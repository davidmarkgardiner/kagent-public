"""Call the live Streamable HTTP MCP transport without printing data rows."""

import asyncio

from fastmcp import Client


async def main():
    async with Client("http://127.0.0.1:8000/mcp") as client:
        tools = await client.list_tools()
        assert {tool.name for tool in tools} == {
            "get_inventory_data_product_details", "get_namespace_count", "get_namespace_summary"
        }
        result = await client.call_tool("get_namespace_count")
        assert not result.is_error
        assert result.structured_content["rows"] == [{"namespace_count": 3}]
        print("DENODO_STREAMABLE_HTTP_MCP_PASS")


asyncio.run(main())
