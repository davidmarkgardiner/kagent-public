"""Acquire a valid DVP audience token when opening each JDBC connection."""

from functools import lru_cache
import os

from azure.identity import ManagedIdentityCredential, WorkloadIdentityCredential


@lru_cache(maxsize=2)
def _credential(mode: str, client_id: str, tenant_id: str, token_file: str):
    if mode == "workload_identity":
        return WorkloadIdentityCredential(
            tenant_id=tenant_id,
            client_id=client_id,
            token_file_path=token_file,
        )
    if mode == "managed_identity":
        return ManagedIdentityCredential(client_id=client_id)
    raise ValueError("DENODO_IDENTITY_MODE must be workload_identity or managed_identity")


def credential():
    mode = os.environ.get("DENODO_IDENTITY_MODE", "workload_identity")
    client_id = os.environ["AZURE_CLIENT_ID"]
    tenant_id = os.environ["AZURE_TENANT_ID"] if mode == "workload_identity" else ""
    token_file = os.environ["AZURE_FEDERATED_TOKEN_FILE"] if mode == "workload_identity" else ""
    return _credential(mode, client_id, tenant_id, token_file)


def access_token() -> str:
    resource = os.environ["DENODO_RESOURCE_APP_ID"].strip()
    if not resource or any(char.isspace() for char in resource):
        raise ValueError("DENODO_RESOURCE_APP_ID must be a nonempty resource identifier")
    # WorkloadIdentityCredential uses the Entra v2 scope form. Azure Identity
    # converts this to the resource form for managed identity / IMDS.
    return credential().get_token(f"{resource}/.default").token
