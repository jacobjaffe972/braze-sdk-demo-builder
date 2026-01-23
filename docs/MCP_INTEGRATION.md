# Braze MCP Integration Documentation

## Overview

The Braze Code Generator uses the **official Braze MCP (Model Context Protocol) server** to provide comprehensive access to Braze SDK documentation during code generation. This enables the research agent to find accurate, up-to-date information about SDK methods, best practices, and implementation patterns.

## Architecture

### Component Stack

```
┌─────────────────────────────────────────────────────┐
│          Research Agent (ReAct LangGraph)           │
│  Uses tools to search docs and get code examples   │
└─────────────────────┬───────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────┐
│     LangChain Tool Wrappers (mcp_integration.py)   │
│  - search_braze_docs(query)                         │
│  - get_braze_code_examples(topic)                   │
│  - get_braze_event_schema(event_key)                │
│  - get_braze_setup_checklist(environment)           │
└─────────────────────┬───────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────┐
│      MCP Client Layer (mcp_client.py)               │
│  - BrazeMCPClient (async MCP protocol client)      │
│  - Threading locks for concurrent access            │
│  - Retry logic with exponential backoff             │
│  - Sync wrappers for LangChain integration          │
└─────────────────────┬───────────────────────────────┘
                      │ stdio transport
┌─────────────────────▼───────────────────────────────┐
│    Official Braze MCP Server (braze-docs-mcp)      │
│  Installed via: brew install braze-docs-mcp         │
│  - Comprehensive Braze SDK documentation            │
│  - Semantic search capabilities                     │
│  - Structured code examples                         │
│  - Event schemas & setup checklists                 │
└─────────────────────────────────────────────────────┘
```

## Installation

### Official Braze MCP Server

The official server is installed separately:

```bash
# Install via Homebrew (macOS)
brew install braze-docs-mcp

# Verify installation
which braze-docs-mcp
# /opt/homebrew/bin/braze-docs-mcp
```

### Python Dependencies

The MCP client requires:

```bash
pip install mcp>=1.0.0
```

This is included in `code/requirements.txt`.

## Configuration

### MCP Client Configuration

The client is configured in [mcp_client.py](../code/braze_code_gen/tools/mcp_client.py):

```python
# Default server configuration
DEFAULT_SERVER_COMMAND = "/opt/homebrew/bin/braze-docs-mcp"

# Initialize with official server
client = BrazeMCPClient(use_official_server=True)
```

### Claude Desktop Integration

For Claude Code integration, the server is configured in `~/.config/claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "braze-docs": {
      "command": "braze-docs-mcp"
    }
  }
}
```

## Available Tools

### 1. search_braze_docs(query)

Searches Braze documentation using semantic search.

**When to use:**
- Finding documentation about specific SDK methods
- Learning about SDK features and capabilities
- Discovering integration patterns

**Example queries:**
```python
search_braze_docs("changeUser method user identification")
search_braze_docs("track custom events Web SDK")
search_braze_docs("push notification permissions")
```

**Returns:**
```json
{
  "results": [
    {
      "uri": "docs://public/braze/latest/en/web-sdk/user-identification",
      "title": "User Identification - Web SDK",
      "snippet": "Use braze.changeUser() to identify users...",
      "score": 0.95,
      "metadata": {
        "doc_type": "overview",
        "platforms": ["Web"],
        "last_modified": "2026-01-23T09:54:25.770Z"
      }
    }
  ]
}
```

### 2. get_braze_code_examples(topic)

Retrieves working code examples for specific SDK features.

**Topics:**
- `"initialization"` - SDK initialization code
- `"user_tracking"` - Event tracking examples
- `"push_notifications"` - Push notification setup
- `"user_attributes"` - Setting user attributes
- `"custom_events"` - Logging custom events
- `"content_cards"` - Content card implementation

**Example:**
```python
get_braze_code_examples("initialization")
```

**Returns:**
```json
{
  "examples": [
    {
      "id": "web-init-basic",
      "title": "Basic SDK Initialization (Web)",
      "description": "Initialize the Braze Web SDK with minimal configuration",
      "language": "javascript",
      "sdk": "web",
      "code": "import * as braze from '@braze/web-sdk';\n\nbraze.initialize('YOUR_API_KEY', {\n  baseUrl: 'sdk.iad-01.braze.com',\n  enableLogging: true\n});\n\nbraze.openSession();"
    }
  ]
}
```

### 3. get_braze_event_schema(event_key)

Gets JSON schema for Braze event types.

**Event keys:**
- `"custom_event"` - Custom event tracking
- `"purchase"` - Purchase events
- `"user_attribute"` - User attributes
- `"push_token"` - Push token registration

### 4. get_braze_setup_checklist(environment)

Gets structured setup checklist for SDK integration.

**Environments:** `"dev"`, `"staging"`, `"prod"`

## Race Condition Handling

The MCP client uses threading locks to prevent race conditions when multiple tools are called concurrently:

```python
# Global lock serializes MCP connections
_connection_lock = threading.Lock()

def _run_with_retry(coro_func, operation_name: str, timeout: int = 30):
    def _run_with_lock():
        with _connection_lock:
            result = asyncio.run(coro_func())
            return result

    # Run in ThreadPoolExecutor for async-to-sync conversion
    with concurrent.futures.ThreadPoolExecutor() as pool:
        future = pool.submit(_run_with_lock)
        return future.result(timeout=timeout)
```

**Why this is needed:**
- Research agent makes 5-6 concurrent tool calls
- Each tool spawns a subprocess to connect to MCP server
- Without locks, asyncio subprocess spawning races occur
- Lock ensures connections are serialized (50-100ms each)

## Testing

Test the MCP integration:

```bash
PYTHONPATH=/Users/Jacob.Jaffe/code-gen-agent/code python3 test_official_mcp.py
```

**Expected output:**
```
[TEST 1] Searching for 'changeUser method'...
✅ Search successful!

[TEST 2] Getting code examples for 'initialization'...
✅ Get examples successful!

[TEST 3] Searching for 'logCustomEvent track events'...
✅ Search successful!
```

## Troubleshooting

### MCP Server Not Found

```
FileNotFoundError: [Errno 2] No such file or directory: '/opt/homebrew/bin/braze-docs-mcp'
```

**Solution:** Install the official server:
```bash
brew install braze-docs-mcp
```

### Connection Timeout

```
TimeoutError: MCP connection timed out after 30s
```

**Solution:** Check if server is responsive:
```bash
echo '{"jsonrpc":"2.0","id":1,"method":"initialize"}' | braze-docs-mcp
```

### Race Condition Errors (Historical)

```
RuntimeError: Racing with another loop to spawn a process
```

**Status:** Fixed with threading locks (see [Race Condition Handling](#race-condition-handling))

## Performance

**Typical latency:**
- Single MCP call: 50-100ms
- 6 concurrent calls (serialized): 250-500ms
- Total research phase: 5-10 seconds

**Comparison to custom server:**
- Custom server: Limited to 50 cached pages
- Official server: Comprehensive coverage, semantic search
- Result quality: Significantly improved with official server

## Migration Notes

**January 2026:** Migrated from custom braze-docs-mcp server to official Braze MCP server.

**Key changes:**
- [mcp_client.py](../code/braze_code_gen/tools/mcp_client.py): Updated to use official server command
- [mcp_integration.py](../code/braze_code_gen/tools/mcp_integration.py): Simplified to 164 lines (was 433)
- [BRAZE_PROMPTS.py](../code/braze_code_gen/prompts/BRAZE_PROMPTS.py): Updated tool descriptions
- Removed cache fallback logic (official server has full coverage)

**Legacy custom server:**
The custom server at `braze-docs-mcp/` is deprecated but kept for reference.

## References

- [MCP Protocol Specification](https://spec.modelcontextprotocol.io/)
- [Official Braze MCP Server](https://github.com/braze/braze-docs-mcp)
- [LangChain Tool Integration](https://python.langchain.com/docs/modules/tools/)
