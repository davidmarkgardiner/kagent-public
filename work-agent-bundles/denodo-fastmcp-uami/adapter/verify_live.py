"""Marker-only direct DVP verifier. No tokens, URLs, identities, or rows printed."""

import base64
import binascii
import json
import os

from identity import access_token
from jdbc import approved_view, query


def check_token_audience(token: str) -> None:
    """Check the returned audience without treating decoded claims as trust proof.

    This does not verify a JWT signature. DVP must authenticate the token at
    connection time; the check only catches a wrong resource request early.
    """
    try:
        payload = token.split(".")[1]
        claims = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    except (IndexError, ValueError, TypeError, binascii.Error):
        raise RuntimeError("DVP_TOKEN_CLAIMS_UNREADABLE") from None
    if not isinstance(claims, dict) or claims.get("aud") != os.environ["DENODO_RESOURCE_APP_ID"]:
        raise RuntimeError("DVP_TOKEN_AUDIENCE_MISMATCH")


def main():
    token = access_token()
    if not token:
        raise RuntimeError("DVP token acquisition returned no token")
    check_token_audience(token)
    print("DVP_AUDIENCE_TOKEN_MATCH_OK")
    probe = query("SELECT 1")
    if probe["returned_rows"] != 1:
        raise RuntimeError("DVP SELECT 1 failed")
    print("DVP_TLS_JDBC_SELECT_ONE_OK")
    view = approved_view()
    query(f'SELECT COUNT(DISTINCT namespace_name) AS namespace_count FROM "{view}"')
    print("DVP_APPROVED_VIEW_QUERY_OK")
    query("SELECT 1")
    print("DVP_FRESH_TOKEN_CONNECTION_OK")
    print("DVP_DIRECT_GATES_PASS")


if __name__ == "__main__":
    main()
