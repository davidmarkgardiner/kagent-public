"""Three bounded, read-only MCP operations over one approved Denodo view."""

from fastmcp import FastMCP

from jdbc import approved_view, query
from result_budget import budget_from_env


mcp = FastMCP("denodo-inventory-readonly")


@mcp.tool()
def get_inventory_data_product_details() -> dict[str, object]:
    """Describe the synthetic inventory data product and response limits."""
    budget = budget_from_env()
    return {
        "data_product": "synthetic-kubernetes-namespace-inventory-v1",
        "functions": ["get_namespace_count", "get_namespace_summary"],
        "writes_supported": False,
        "arbitrary_sql_supported": False,
        "response_budget": {
            "max_rows": budget.max_rows,
            "max_response_bytes": budget.max_response_bytes,
            "max_cell_chars": budget.max_cell_chars,
        },
    }


@mcp.tool()
def get_namespace_count() -> dict[str, object]:
    """Count distinct namespaces in the approved Denodo view."""
    return query(f'SELECT COUNT(DISTINCT namespace_name) AS namespace_count FROM "{approved_view()}"')


@mcp.tool()
def get_namespace_summary(namespace_name: str) -> dict[str, object]:
    """Get one namespace's approved ownership and workload summary."""
    return query(
        f'SELECT namespace_name, owner_team, workload_type, lob, region, '
        f'workload_count, running_pod_count, observed_at FROM "{approved_view()}" '
        "WHERE namespace_name = ?",
        (namespace_name,),
    )


if __name__ == "__main__":
    mcp.run(transport="streamable-http", host="0.0.0.0", port=8000, path="/mcp", show_banner=False)
