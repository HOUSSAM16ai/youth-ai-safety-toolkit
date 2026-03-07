def kagent_tool(name: str, mcp_server: str):
    def decorator(func):
        from langchain_core.tools import tool

        # We wrap it in a standard langchain tool for compatibility with the LLM bind_tools
        # But we preserve the mcp_server metadata.
        t = tool(name)(func)
        t.metadata = {"mcp_server": mcp_server}
        return t

    return decorator
