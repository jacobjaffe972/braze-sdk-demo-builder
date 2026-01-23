"""Real MCP Client for Braze Documentation Server.

This module provides a proper MCP client that communicates with the
braze-docs-mcp server via stdio transport, enabling real-time access
to Braze documentation.
"""

import asyncio
import json
import logging
import random
import threading
import time
from contextlib import asynccontextmanager
from typing import Any, Optional

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logger = logging.getLogger(__name__)

# Retry configuration
MAX_RETRIES = 3
INITIAL_RETRY_DELAY = 0.1  # 100ms
MAX_RETRY_DELAY = 2.0  # 2 seconds

# Default server configuration
# Using official Braze MCP server (installed via homebrew/npm)
DEFAULT_SERVER_COMMAND = "/opt/homebrew/bin/braze-docs-mcp"

# Legacy custom server paths (kept for backwards compatibility)
DEFAULT_SERVER_PATH = "/Users/Jacob.Jaffe/code-gen-agent/braze-docs-mcp"
DEFAULT_PYTHON_PATH = f"{DEFAULT_SERVER_PATH}/venv/bin/python"
DEFAULT_SERVER_SCRIPT = f"{DEFAULT_SERVER_PATH}/server.py"

# Global lock to serialize MCP connections and avoid race conditions
# when multiple tools are called concurrently
_connection_lock = threading.Lock()


class BrazeMCPClient:
    """MCP Client for Braze Documentation Server.

    This client connects to the braze-docs-mcp FastMCP server and
    calls its tools using the MCP protocol.

    Example:
        >>> async with BrazeMCPClient() as client:
        ...     results = await client.search_documentation("Web SDK initialization")
        ...     print(results)
    """

    def __init__(
        self,
        server_command: Optional[str] = None,
        use_official_server: bool = True
    ):
        """Initialize the MCP client.

        Args:
            server_command: Path to MCP server command (default: official braze-docs-mcp)
            use_official_server: If True, use official Braze MCP server; if False, use custom server
        """
        if use_official_server:
            self.server_command = server_command or DEFAULT_SERVER_COMMAND
            self.server_args = []
        else:
            # Use legacy custom server
            self.server_command = DEFAULT_PYTHON_PATH
            self.server_args = [DEFAULT_SERVER_SCRIPT]

        self._session: Optional[ClientSession] = None
        self._read_stream = None
        self._write_stream = None

    @asynccontextmanager
    async def connect(self):
        """Connect to the MCP server.

        Yields:
            BrazeMCPClient: Connected client instance
        """
        server_params = StdioServerParameters(
            command=self.server_command,
            args=self.server_args,
        )

        logger.info(f"Connecting to Braze MCP server: {self.server_command}")

        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                # Initialize the session
                await session.initialize()

                self._session = session
                logger.info("MCP session initialized successfully")

                try:
                    yield self
                finally:
                    self._session = None

    async def search_documentation(self, query: str, limit: int = 5) -> dict:
        """Search Braze documentation using MCP tool.

        Args:
            query: Search query
            limit: Maximum number of results (default: 5)

        Returns:
            dict: Search results from the MCP server
        """
        if not self._session:
            raise RuntimeError("Not connected to MCP server. Use 'async with client.connect():'")

        logger.debug(f"MCP search_docs: {query} (limit={limit})")

        # Official Braze MCP server uses "search_docs" tool
        result = await self._session.call_tool(
            "search_docs",
            arguments={"query": query, "limit": limit}
        )

        # Extract text content from result
        if result.content:
            for content_block in result.content:
                if hasattr(content_block, 'text'):
                    return {"success": True, "content": content_block.text}

        return {"success": False, "content": "No results found"}

    async def get_examples(
        self,
        topic: str,
        language: str = "javascript",
        sdk: str = "web",
        limit: int = 5
    ) -> dict:
        """Get code examples from Braze documentation.

        Args:
            topic: Topic to get examples for (e.g., 'initialization', 'user_tracking')
            language: Programming language filter (default: 'javascript')
            sdk: SDK type filter (default: 'web')
            limit: Maximum number of examples (default: 5)

        Returns:
            dict: Code examples from the MCP server
        """
        if not self._session:
            raise RuntimeError("Not connected to MCP server. Use 'async with client.connect():'")

        logger.debug(f"MCP get_examples: {topic} (lang={language}, sdk={sdk})")

        # Official Braze MCP server uses "get_examples" tool
        result = await self._session.call_tool(
            "get_examples",
            arguments={
                "topic": topic,
                "language": language,
                "sdk": sdk,
                "limit": limit
            }
        )

        if result.content:
            for content_block in result.content:
                if hasattr(content_block, 'text'):
                    return {"success": True, "content": content_block.text}

        return {"success": False, "content": "No examples found"}

    async def get_event_schema(self, event_key: str) -> dict:
        """Get JSON schema for a Braze event type.

        Args:
            event_key: Event identifier (e.g., 'custom_event', 'purchase', 'user_attribute')

        Returns:
            dict: Event schema from the MCP server
        """
        if not self._session:
            raise RuntimeError("Not connected to MCP server. Use 'async with client.connect():'")

        logger.debug(f"MCP get_event_schema: {event_key}")

        result = await self._session.call_tool(
            "get_event_schema",
            arguments={"event_key": event_key}
        )

        if result.content:
            for content_block in result.content:
                if hasattr(content_block, 'text'):
                    return {"success": True, "content": content_block.text}

        return {"success": False, "content": "Schema not found"}

    async def get_setup_checklist(self, environment: str = "dev") -> dict:
        """Get structured setup checklist for Braze SDK integration.

        Args:
            environment: Target environment ('dev', 'staging', 'prod')

        Returns:
            dict: Setup checklist from the MCP server
        """
        if not self._session:
            raise RuntimeError("Not connected to MCP server. Use 'async with client.connect():'")

        logger.debug(f"MCP get_setup_checklist: {environment}")

        result = await self._session.call_tool(
            "get_setup_checklist",
            arguments={"environment": environment}
        )

        if result.content:
            for content_block in result.content:
                if hasattr(content_block, 'text'):
                    return {"success": True, "content": content_block.text}

        return {"success": False, "content": "Checklist not found"}


def _run_with_retry(coro_func, operation_name: str, timeout: int = 30):
    """Run async operation with retry logic for race conditions.

    Uses a global lock to serialize MCP connections and avoid race conditions
    when multiple tools are called concurrently.

    Args:
        coro_func: Async function to execute
        operation_name: Name for logging
        timeout: Timeout in seconds

    Returns:
        Result from the async function
    """
    last_exception = None

    def _run_with_lock():
        """Run the async function with lock protection."""
        with _connection_lock:
            logger.debug(f"MCP {operation_name}: acquired connection lock")
            result = asyncio.run(coro_func())
            logger.debug(f"MCP {operation_name}: success")
            return result

    for attempt in range(MAX_RETRIES):
        try:
            # Add jitter on retries
            if attempt > 0:
                jitter = random.uniform(0, 0.1 * attempt)
                time.sleep(jitter)

            # Check if we're already in an async context
            try:
                loop = asyncio.get_running_loop()
                # We're in an async context, need to run in a new thread
                # The lock must be acquired in the new thread, not here!
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(_run_with_lock)
                    return future.result(timeout=timeout)
            except RuntimeError:
                # No running loop, we can use the lock directly
                return _run_with_lock()

        except Exception as e:
            last_exception = e
            error_msg = str(e)

            # Check if it's a race condition that we should retry
            is_race_condition = "Racing with another loop" in error_msg or "cannot spawn" in error_msg.lower()

            # Log details for debugging
            logger.info(
                f"MCP {operation_name} attempt {attempt + 1}/{MAX_RETRIES}: "
                f"exception={type(e).__name__}, "
                f"is_race_condition={is_race_condition}, "
                f"message='{error_msg}'"
            )

            if is_race_condition:
                if attempt < MAX_RETRIES - 1:
                    delay = min(INITIAL_RETRY_DELAY * (2 ** attempt), MAX_RETRY_DELAY)
                    delay += random.uniform(0, delay * 0.5)  # Add jitter
                    logger.warning(
                        f"MCP {operation_name} attempt {attempt + 1} failed with race condition, "
                        f"retrying in {delay:.2f}s: {error_msg}"
                    )
                    time.sleep(delay)
                    continue
                else:
                    # Last attempt failed with race condition
                    logger.error(f"MCP {operation_name} failed after {MAX_RETRIES} attempts with race condition: {error_msg}")
                    raise

            # Not a retryable error
            logger.error(f"MCP {operation_name} failed with non-retryable error: {e}")
            raise

    # All retries exhausted
    logger.error(f"MCP {operation_name} failed after {MAX_RETRIES} attempts")
    raise last_exception


def run_mcp_search(query: str, limit: int = 5) -> str:
    """Synchronous wrapper for MCP documentation search.

    Uses the official Braze MCP server for comprehensive documentation access.

    Args:
        query: Search query
        limit: Maximum number of results (default: 5)

    Returns:
        str: Search results as formatted text
    """
    async def _search():
        client = BrazeMCPClient(use_official_server=True)
        async with client.connect() as connected_client:
            result = await connected_client.search_documentation(query, limit=limit)
            return result.get("content", "No results found")

    return _run_with_retry(_search, "search", timeout=30)


def run_mcp_get_examples(
    topic: str,
    language: str = "javascript",
    sdk: str = "web",
    limit: int = 5
) -> str:
    """Synchronous wrapper for MCP code examples.

    Args:
        topic: Topic to get examples for
        language: Programming language (default: 'javascript')
        sdk: SDK type (default: 'web')
        limit: Maximum number of examples (default: 5)

    Returns:
        str: Code examples as formatted text
    """
    async def _get_examples():
        client = BrazeMCPClient(use_official_server=True)
        async with client.connect() as connected_client:
            result = await connected_client.get_examples(
                topic=topic,
                language=language,
                sdk=sdk,
                limit=limit
            )
            return result.get("content", "No examples found")

    return _run_with_retry(_get_examples, "get_examples", timeout=30)


def run_mcp_get_event_schema(event_key: str) -> str:
    """Synchronous wrapper for MCP event schema.

    Args:
        event_key: Event identifier (e.g., 'custom_event', 'purchase')

    Returns:
        str: Event schema as formatted text
    """
    async def _get_schema():
        client = BrazeMCPClient(use_official_server=True)
        async with client.connect() as connected_client:
            result = await connected_client.get_event_schema(event_key)
            return result.get("content", "Schema not found")

    return _run_with_retry(_get_schema, "get_event_schema", timeout=30)


def run_mcp_get_setup_checklist(environment: str = "dev") -> str:
    """Synchronous wrapper for MCP setup checklist.

    Args:
        environment: Target environment ('dev', 'staging', 'prod')

    Returns:
        str: Setup checklist as formatted text
    """
    async def _get_checklist():
        client = BrazeMCPClient(use_official_server=True)
        async with client.connect() as connected_client:
            result = await connected_client.get_setup_checklist(environment)
            return result.get("content", "Checklist not found")

    return _run_with_retry(_get_checklist, "get_setup_checklist", timeout=30)
