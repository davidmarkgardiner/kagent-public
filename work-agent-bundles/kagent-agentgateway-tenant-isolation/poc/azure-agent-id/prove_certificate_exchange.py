#!/usr/bin/env python3
"""Temporarily add a certificate and prove the two-stage Agent ID exchange.

The private key exists only in process memory. The public certificate is
removed from the blueprint in a finally block, even if token exchange fails.
This does not test UAMI or AKS workload identity.
"""

import argparse
import base64
import datetime as dt
import hashlib
import json
import re
import subprocess
import time
import uuid
import urllib.error
import urllib.parse
import urllib.request

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.x509.oid import NameOID

from pathlib import Path

from provision_graph import GRAPH, ProvisionError, azure, graph_get, load_state, private_state_dir


ASSERTION_TYPE = "urn:ietf:params:oauth:client-assertion-type:jwt-bearer"


def b64url(data):
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def certificate():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    now = dt.datetime.now(dt.timezone.utc)
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "kagent-public-agentid-poc")])
    cert = (x509.CertificateBuilder()
            .subject_name(subject).issuer_name(subject)
            .public_key(key.public_key()).serial_number(x509.random_serial_number())
            .not_valid_before(now - dt.timedelta(minutes=5))
            .not_valid_after(now + dt.timedelta(days=1))
            .sign(key, hashes.SHA256()))
    return key, cert


def jwt_assertion(key, cert, client_id, endpoint):
    header = {"alg": "RS256", "typ": "JWT", "x5t": b64url(hashlib.sha1(cert.public_bytes(serialization.Encoding.DER)).digest())}
    now = int(time.time())
    payload = {"aud": endpoint, "iss": client_id, "sub": client_id,
               "jti": str(uuid.uuid4()), "nbf": now - 30, "exp": now + 300}
    signing_input = ".".join(b64url(json.dumps(item, separators=(",", ":")).encode())
                             for item in (header, payload)).encode()
    signature = key.sign(signing_input, padding.PKCS1v15(), hashes.SHA256())
    return signing_input.decode() + "." + b64url(signature)


def token(endpoint, parameters):
    request = urllib.request.Request(endpoint, data=urllib.parse.urlencode(parameters).encode(),
                                     headers={"Content-Type": "application/x-www-form-urlencoded"})
    for attempt in range(6):
        try:
            with urllib.request.urlopen(request, timeout=25) as response:
                return json.load(response)["access_token"]
        except urllib.error.HTTPError as exc:
            data = exc.read(4096).decode(errors="replace")
            code = re.search(r"AADSTS\d+", data)
            if code and code.group() == "AADSTS700027" and attempt < 5:
                time.sleep(4)
                continue
            raise ProvisionError(f"token endpoint denied exchange: {code.group() if code else exc.code}; response withheld") from None


def claims(jwt):
    parts = jwt.split(".")
    if len(parts) != 3:
        raise ProvisionError("token endpoint returned a non-JWT access token")
    return json.loads(base64.urlsafe_b64decode(parts[1] + "=" * (-len(parts[1]) % 4)))


def credential_ids(object_id):
    app = graph_get(f"/applications/{object_id}?$select=keyCredentials")
    return {item["keyId"] for item in app.get("keyCredentials", [])}


def patch_keys(object_id, credentials):
    result = subprocess.run(["az", "rest", "--method", "PATCH",
                             "--url", f"{GRAPH}/applications/{object_id}",
                             "--headers", "Content-Type=application/json",
                             "--body", json.dumps({"keyCredentials": credentials}),
                             "--output", "none", "--only-show-errors"],
                            capture_output=True, text=True)
    if result.returncode:
        code = re.search(r"(?:AADSTS\d+|Authorization_RequestDenied|BadRequest)", result.stderr)
        raise ProvisionError(f"Graph certificate update failed: {code.group() if code else 'unknown'}; raw response withheld")


def prove(state_dir):
    state = load_state(state_dir / "state.json")
    required = ("tenantId", "blueprintAppId", "blueprintObjectId", "agentAppId", "agentObjectId", "apiAppId", "apiRoleId")
    if any(not state.get(key) for key in required):
        raise ProvisionError("provision_graph.py and provision_access.py must succeed first")
    account = azure("account", "show")
    if account.get("tenantId") != state["tenantId"]:
        raise ProvisionError("signed-in tenant differs from private receipt")
    endpoint = f"https://login.microsoftonline.com/{state['tenantId']}/oauth2/v2.0/token"
    object_id = state["blueprintObjectId"]
    before = credential_ids(object_id)
    if before:
        raise ProvisionError("blueprint already has certificates; refusing to replace any existing credential")
    key, cert = certificate()
    cert_id = str(uuid.uuid4())
    try:
        patch_keys(object_id, [{
            "keyId": cert_id,
            "displayName": "Temporary Agent ID PoC proof certificate",
            "type": "AsymmetricX509Cert",
            "usage": "Verify",
            "key": base64.b64encode(cert.public_bytes(serialization.Encoding.DER)).decode(),
            "startDateTime": cert.not_valid_before_utc.isoformat(),
            "endDateTime": cert.not_valid_after_utc.isoformat(),
        }])
        if credential_ids(object_id) != {cert_id}:
            raise ProvisionError("temporary blueprint certificate read-back failed")
        print("temporary_blueprint_certificate=added")
        assertion = jwt_assertion(key, cert, state["blueprintAppId"], endpoint)
        first = token(endpoint, {
            "client_id": state["blueprintAppId"],
            "scope": "api://AzureADTokenExchange/.default",
            "fmi_path": state["agentAppId"],
            "client_assertion_type": ASSERTION_TYPE,
            "client_assertion": assertion,
            "grant_type": "client_credentials",
        })
        print("blueprint_exchange_status=issued")
        second = token(endpoint, {
            "client_id": state["agentAppId"],
            "scope": f"api://{state['apiAppId']}/.default",
            "client_assertion_type": ASSERTION_TYPE,
            "client_assertion": first,
            "grant_type": "client_credentials",
        })
        result = claims(second)
        if result.get("oid") != state["agentObjectId"] or "team-event.mcp.use" not in result.get("roles", []):
            raise ProvisionError("resource token lacks the child Agent ID or expected app role")
        if result.get("aud") not in (state["apiAppId"], f"api://{state['apiAppId']}"):
            raise ProvisionError("resource token has an unexpected audience")
        print("AGENT_TOKEN_POC_OK: child Agent ID, API audience, and app role verified")
    finally:
        current = credential_ids(object_id)
        if cert_id in current:
            if current != {cert_id}:
                raise ProvisionError("certificate set changed during test; refusing unsafe cleanup")
            patch_keys(object_id, [])
            if credential_ids(object_id):
                raise ProvisionError("temporary blueprint certificate cleanup failed")
            print("temporary_blueprint_certificate=removed")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-dir", required=True, type=Path)
    args = parser.parse_args()
    try:
        prove(private_state_dir(args.state_dir))
    except (OSError, KeyError, ValueError, ProvisionError) as exc:
        parser.exit(2, f"error: {exc}\n")


if __name__ == "__main__":
    main()
