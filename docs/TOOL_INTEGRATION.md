# Tool Integration Patterns

## Overview

This document describes proven patterns for integrating tools into LangChain agents, extracted from the reference implementation in [/code/reference_agents/](../code/reference_agents/) and the Braze Docs MCP server.

**Key Concepts**:
- LangChain `@tool` decorator for function wrapping
- MCP (Model Context Protocol) server integration
- Safe expression evaluation
- Error handling and validation
- Timeout management

---

## 1. LangChain @tool Decorator Pattern

### Pattern Description

**Intent**: Convert Python functions into tools that LLMs can call with proper type annotations and documentation.

**Source**: [/code/reference_agents/agents/react_multi_agent.py:95-136](../code/reference_agents/agents/react_multi_agent.py)

### Basic Tool Implementation

```python
from langchain_core.tools import tool
from typing import Annotated

@tool
def calculator(expression: Annotated[str, "The mathematical expression to evaluate"]) -> str:
    """Evaluate a mathematical expression using basic arithmetic operations (+, -, *, /, %, //).
    Examples: '5 + 3', '10 * (2 + 3)', '15 / 3'
    """
    result = Calculator.evaluate_expression(expression)
    if isinstance(result, str) and result.startswith("Error"):
        raise ValueError(result)
    return str(result)
```

### Key Components

1. **@tool Decorator**: Marks function as LangChain tool
2. **Type Annotations**: Uses `Annotated[type, "description"]` for parameters
3. **Docstring**: First line becomes tool description, rest provides context
4. **Error Handling**: Raise `ValueError` for invalid inputs
5. **Return Type**: Always return strings for consistency

---

## 2. Tool Design Best Practices

### ✅ Do:

#### 1. Use Annotated Type Hints

```python
@tool
def get_weather(
    location: Annotated[str, "The location to get weather for (city, country)"]
) -> str:
    """Get the current weather for a given location using Tavily search.
    Examples: 'New York, USA', 'London, UK', 'Tokyo, Japan'
    """
    pass
```

**Why**: LLM uses annotations to understand parameter purpose.

#### 2. Write Clear Docstrings

```python
@tool
def execute_datetime_code(
    code: Annotated[str, "Python code to execute for datetime operations"]
) -> str:
    """Execute Python code for datetime operations. The code should use datetime or time modules.

    Examples:
    - 'print(datetime.datetime.now().strftime("%Y-%m-%d"))'
    - 'print(datetime.datetime.now().year)'
    """
    pass
```

**Why**: Docstring helps LLM decide when to call tool.

#### 3. Include Examples in Docstrings

```python
"""Calculate the square root of a number.

Examples:
- calculate_sqrt(16) -> 4.0
- calculate_sqrt(2) -> 1.414...
"""
```

**Why**: Examples clarify expected inputs.

#### 4. Return Error Messages as Strings

```python
@tool
def fetch_url(url: Annotated[str, "URL to fetch"]) -> str:
    try:
        response = requests.get(url, timeout=10)
        return response.text
    except requests.Timeout:
        return "Error: Request timed out after 10 seconds"
    except requests.RequestException as e:
        return f"Error: Failed to fetch URL: {str(e)}"
```

**Why**: Agent can read error and retry with different approach.

### ❌ Don't:

#### 1. Don't Use Magic Values

```python
# ❌ Bad
@tool
def calculate(x, y):  # No type hints, unclear purpose
    return x + y

# ✅ Good
@tool
def add_numbers(
    x: Annotated[float, "First number"],
    y: Annotated[float, "Second number"]
) -> str:
    """Add two numbers together."""
    return str(x + y)
```

#### 2. Don't Let Exceptions Crash Agent

```python
# ❌ Bad
@tool
def risky_operation(data: str) -> str:
    result = json.loads(data)  # May crash on invalid JSON
    return result['key']

# ✅ Good
@tool
def safe_operation(data: Annotated[str, "JSON string to parse"]) -> str:
    """Parse JSON and extract 'key' field."""
    try:
        result = json.loads(data)
        return result.get('key', 'Key not found')
    except json.JSONDecodeError:
        return "Error: Invalid JSON format"
```

#### 3. Don't Combine Unrelated Functionality

```python
# ❌ Bad - one tool does too much
@tool
def do_everything(action: str, data: str) -> str:
    if action == "calculate":
        # calculation logic
    elif action == "search":
        # search logic
    elif action == "format":
        # formatting logic

# ✅ Good - separate focused tools
@tool
def calculate(expression: str) -> str:
    """Evaluate mathematical expression."""
    pass

@tool
def search_web(query: str) -> str:
    """Search the web for information."""
    pass
```

---

## 3. Safe Expression Evaluation Pattern

### Pattern Description

**Intent**: Safely evaluate user-provided mathematical expressions without executing arbitrary code.

**Source**: [/code/reference_agents/tools/calculator.py](../code/reference_agents/tools/calculator.py)

### Implementation

```python
import re
from typing import Union

class Calculator:
    """A simple calculator tool for evaluating basic arithmetic expressions."""

    @staticmethod
    def evaluate_expression(expression: str) -> Union[float, str]:
        """Evaluate a basic arithmetic expression.

        Supports only basic arithmetic operations (+, -, *, /) and parentheses.
        Returns an error message if the expression is invalid or cannot be
        evaluated safely.

        Args:
            expression: A string containing a mathematical expression
                       e.g. "5 + 3" or "10 * (2 + 3)"

        Returns:
            Union[float, str]: The result of the evaluation, or an error message
                              if the expression is invalid

        Examples:
            >>> Calculator.evaluate_expression("5 + 3")
            8.0
            >>> Calculator.evaluate_expression("10 * (2 + 3)")
            50.0
            >>> Calculator.evaluate_expression("15 / 3")
            5.0
        """
        try:
            # Clean up the expression
            expression = expression.strip()

            # Only allow safe characters (digits, basic operators, parentheses, spaces)
            if not re.match(r'^[\d\s\+\-\*\/\(\)\.]*$', expression):
                return "Error: Invalid characters in expression"

            # Evaluate the expression with restricted builtins
            result = eval(expression, {"__builtins__": {}})

            # Convert to float and handle division by zero
            return float(result)

        except ZeroDivisionError:
            return "Error: Division by zero"
        except (SyntaxError, TypeError, NameError):
            return "Error: Invalid expression"
        except Exception as e:
            return f"Error: {str(e)}"
```

### Security Measures

1. **Regex Validation**: Only allow digits, operators, parentheses, spaces
2. **Restricted eval**: `{"__builtins__": {}}` prevents access to dangerous functions
3. **Explicit Error Handling**: Catch division by zero, syntax errors
4. **Return Errors as Strings**: Don't raise exceptions

### LangChain Tool Wrapper

```python
from langchain_core.tools import tool

@tool
def calculator(
    expression: Annotated[str, "The mathematical expression to evaluate"]
) -> str:
    """Evaluate a mathematical expression using basic arithmetic operations (+, -, *, /, %, //).
    Examples: '5 + 3', '10 * (2 + 3)', '15 / 3'
    """
    result = Calculator.evaluate_expression(expression)
    if isinstance(result, str) and result.startswith("Error"):
        raise ValueError(result)
    return str(result)
```

---

## 4. Code Execution with Sandboxing Pattern

### Pattern Description

**Intent**: Execute user code in a controlled environment with limited imports and output capture.

**Source**: [/code/reference_agents/agents/react_multi_agent.py:250-263](../code/reference_agents/agents/react_multi_agent.py)

### Implementation

```python
import io
import contextlib

@tool
def execute_datetime_code(
    code: Annotated[str, "Python code to execute for datetime operations"]
) -> str:
    """Execute Python code for datetime operations. The code should use datetime or time modules.

    Examples:
    - 'print(datetime.datetime.now().strftime("%Y-%m-%d"))'
    - 'print(datetime.datetime.now().year)'
    """
    output_buffer = io.StringIO()

    # Prepend safe imports
    code = f"import datetime\\nimport time\\n{code}"

    try:
        # Redirect stdout to capture print statements
        with contextlib.redirect_stdout(output_buffer):
            exec(code)

        return output_buffer.getvalue().strip()

    except Exception as e:
        raise ValueError(f"Error executing datetime code: {str(e)}")
```

### Key Features

1. **Output Capture**: Use `io.StringIO()` and `contextlib.redirect_stdout()`
2. **Limited Imports**: Only allow specific safe modules
3. **Error Handling**: Raise `ValueError` with descriptive message
4. **Return Captured Output**: Return printed content

### Usage Example

```python
# Agent calls:
result = execute_datetime_code('print(datetime.datetime.now().year)')
# Returns: "2026"

result = execute_datetime_code('print(datetime.datetime.now().strftime("%B %d, %Y"))')
# Returns: "January 06, 2026"
```

---

## 5. External API Tool Pattern

### Pattern Description

**Intent**: Wrap external API calls with timeout, error handling, and fallback logic.

**Source**: [/code/reference_agents/agents/react_multi_agent.py:266-279](../code/reference_agents/agents/react_multi_agent.py)

### Implementation

```python
from langchain_community.tools.tavily_search import TavilySearch

@tool
def get_weather(
    location: Annotated[str, "The location to get weather for (city, country)"]
) -> str:
    """Get the current weather for a given location using Tavily search.
    Examples: 'New York, USA', 'London, UK', 'Tokyo, Japan'
    """
    search = TavilySearch(max_results=3)
    query = f"what is the current weather temperature in {location} right now"

    try:
        results = search.invoke({"query": query})

        search_results = results.get('results', [])
        if not search_results:
            return f"Could not find weather information for {location}"

        return search_results[0].get("content", f"Could not find weather information for {location}")

    except Exception as e:
        return f"Error fetching weather: {str(e)}"
```

### Best Practices for External APIs

1. **Set Timeouts**: Prevent hanging on slow APIs
2. **Limit Results**: Don't overwhelm context with data
3. **Check for Empty Results**: Handle missing data gracefully
4. **Provide Fallback Messages**: Return useful error messages
5. **Catch All Exceptions**: Don't let API errors crash agent

### Enhanced Version with Retry Logic

```python
import time
from typing import Optional

@tool
def get_weather_with_retry(
    location: Annotated[str, "The location to get weather for (city, country)"]
) -> str:
    """Get the current weather for a given location using Tavily search.
    Retries once on failure.
    Examples: 'New York, USA', 'London, UK', 'Tokyo, Japan'
    """
    search = TavilySearch(max_results=3)
    query = f"what is the current weather temperature in {location} right now"

    max_retries = 2
    for attempt in range(max_retries):
        try:
            results = search.invoke({"query": query})

            search_results = results.get('results', [])
            if not search_results:
                return f"Could not find weather information for {location}"

            return search_results[0].get("content", f"Could not find weather information for {location}")

        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(1)  # Wait before retry
                continue
            return f"Error fetching weather after {max_retries} attempts: {str(e)}"
```

---

## 6. MCP Server Integration Pattern

### Pattern Description

**Intent**: Create MCP server that scrapes and caches documentation for agent access via resources and tools.

**Source**: [/braze-docs-mcp/server.py](../braze-docs-mcp/server.py)

### MCP Server Structure

```python
from mcp.server.fastmcp import FastMCP
import requests
from bs4 import BeautifulSoup
import json
from pathlib import Path

# Create MCP server
mcp = FastMCP("Braze Documentation")

# Storage for scraped documentation
DOCS_CACHE_FILE = Path("braze_docs_cache.json")
docs_data = {}
```

### Resource Pattern (MCP)

Resources provide read-only data access with URI scheme:

```python
@mcp.resource("doc://{page_path}")
def get_documentation_page(page_path: str) -> str:
    """
    Get a specific documentation page by path.

    Example: doc://user_guide/introduction or doc://api/endpoints/users
    """
    if page_path not in docs_data:
        available_pages = list(docs_data.keys())[:10]
        return f"Page '{page_path}' not found. Available pages include:\\n" + "\\n".join(available_pages)

    page = docs_data[page_path]

    # Format the response
    response = f"""# {page['title']}

**URL:** {page['url']}

## Content

{page['content']}
"""

    # Add code examples if available
    if page['code_examples']:
        response += "## Code Examples\\n\\n"
        for i, example in enumerate(page['code_examples'][:5], 1):
            response += f"### Example {i}\\n```\\n{example}\\n```\\n\\n"

    return response
```

### Tool Pattern (MCP)

Tools provide active operations that agents can invoke:

```python
@mcp.tool()
def search_documentation(query: str) -> str:
    """
    Search all documentation for pages matching your query.
    Returns matching page titles, URLs, and relevant snippets.
    """
    if not docs_data:
        return "No documentation loaded. Please restart the server."

    query_lower = query.lower()
    results = []

    for page_path, page in docs_data.items():
        title = page['title'].lower()
        content = page['content'].lower()

        # Check if query appears in title or content
        if query_lower in title or query_lower in content:
            # Extract relevant snippet
            content_index = content.find(query_lower)
            start = max(0, content_index - 100)
            end = min(len(content), content_index + 200)
            snippet = content[start:end].strip()

            # Calculate relevance score
            relevance = 0
            if query_lower in title:
                relevance += 3
            if content.count(query_lower) > 3:
                relevance += 2

            results.append({
                'page_path': page_path,
                'title': page['title'],
                'url': page['url'],
                'snippet': snippet,
                'relevance': relevance
            })

    # Sort by relevance
    results.sort(key=lambda x: x['relevance'], reverse=True)

    if not results:
        return f"No pages found matching '{query}'. Try searching for broader terms."

    response = f"Found {len(results)} matching pages:\\n\\n"

    for i, result in enumerate(results[:10], 1):
        response += f"{i}. **{result['title']}**\\n"
        response += f"   Path: `doc://{result['page_path']}`\\n"
        response += f"   URL: {result['url']}\\n"
        response += f"   Snippet: ...{result['snippet']}...\\n\\n"

    return response


@mcp.tool()
def extract_code_from_page(page_path: str) -> str:
    """
    Extract all code examples from a specific documentation page.
    """
    if page_path not in docs_data:
        return f"Page '{page_path}' not found."

    page = docs_data[page_path]

    if not page['code_examples']:
        return f"No code examples found on page '{page_path}'."

    response = f"Code examples from **{page['title']}**:\\n\\n"

    for i, example in enumerate(page['code_examples'], 1):
        response += f"### Example {i}\\n```\\n{example}\\n```\\n\\n"

    return response
```

### Web Scraping Pattern

```python
def scrape_documentation() -> None:
    """Scrape Braze documentation and cache it"""
    global docs_data

    # Load cache if it exists
    if DOCS_CACHE_FILE.exists():
        with open(DOCS_CACHE_FILE, 'r') as f:
            docs_data = json.load(f)
        print(f"✅ Loaded {len(docs_data)} cached documentation pages")
        return

    # Start with common entry points
    base_urls = [
        "https://www.braze.com/docs/",
        "https://www.braze.com/docs/user_guide/",
        "https://www.braze.com/docs/api/",
    ]

    visited_urls = set()
    to_visit = base_urls.copy()
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }

    page_count = 0
    max_pages = 50  # Limit for initial scrape

    while to_visit and page_count < max_pages:
        url = to_visit.pop(0)

        if url in visited_urls:
            continue

        visited_urls.add(url)

        try:
            response = requests.get(url, timeout=10, headers=headers)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "lxml")

            # Extract title
            title_tag = soup.find("h1") or soup.find("title")
            title = title_tag.get_text(strip=True) if title_tag else url.split("/")[-1]

            # Extract main content
            content_div = soup.find(["main", "article", "div.content"])
            if not content_div:
                content_div = soup

            content = content_div.get_text(separator="\\n", strip=True)[:5000]  # Limit length

            # Extract code examples
            code_blocks = soup.find_all(["code", "pre"])
            code_examples = [block.get_text(strip=True) for block in code_blocks if len(block.get_text(strip=True)) > 10][:10]

            # Store the page
            page_key = url.replace("https://www.braze.com/docs/", "").rstrip("/")
            docs_data[page_key] = {
                "title": title,
                "url": url,
                "content": content,
                "code_examples": code_examples
            }

            page_count += 1

            # Extract links to other documentation pages
            for link in soup.find_all("a", href=True):
                href = link["href"]
                if href.startswith("/docs/"):
                    full_url = "https://www.braze.com" + href
                    if full_url not in visited_urls:
                        to_visit.append(full_url)

        except requests.exceptions.RequestException as e:
            continue

    # Save cache
    with open(DOCS_CACHE_FILE, 'w') as f:
        json.dump(docs_data, f, indent=2)
```

### Web Scraping Best Practices

1. **Cache Results**: Don't scrape on every server start
2. **Set User-Agent**: Some sites block default Python requests
3. **Timeout Requests**: 10-second timeout prevents hanging
4. **Limit Scope**: Don't scrape entire internet (max_pages limit)
5. **Extract Structured Data**: Separate title, content, code examples
6. **Follow Links**: Build comprehensive coverage by following internal links
7. **Handle Errors Gracefully**: Continue on failed requests

---

## 7. Tool Organization Pattern

### Creating Tool Collections

```python
def _create_tools(self) -> List[Any]:
    """Create and return the list of tools for the agent."""

    @tool
    def calculator(expression: Annotated[str, "The mathematical expression to evaluate"]) -> str:
        """Evaluate a mathematical expression using basic arithmetic operations (+, -, *, /, %, //)."""
        result = Calculator.evaluate_expression(expression)
        if isinstance(result, str) and result.startswith("Error"):
            raise ValueError(result)
        return str(result)

    @tool
    def execute_datetime_code(code: Annotated[str, "Python code to execute for datetime operations"]) -> str:
        """Execute Python code for datetime operations."""
        # Implementation...
        pass

    @tool
    def get_weather(location: Annotated[str, "The location to get weather for"]) -> str:
        """Get the current weather for a given location."""
        # Implementation...
        pass

    return [calculator, execute_datetime_code, get_weather]
```

### Binding Tools to LLM

```python
from langchain_openai import ChatOpenAI

# Create LLM
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# Create tools
tools = self._create_tools()

# Bind tools to LLM
llm_with_tools = llm.bind_tools(tools)

# Use in agent
from langgraph.prebuilt import create_react_agent

agent = create_react_agent(
    model=llm_with_tools,
    tools=tools,
)
```

---

## 8. Error Handling Strategies

### Strategy 1: Return Error Messages

```python
@tool
def safe_operation(data: str) -> str:
    """Process data safely."""
    try:
        result = process(data)
        return f"Success: {result}"
    except ValueError as e:
        return f"Error: Invalid input - {str(e)}"
    except Exception as e:
        return f"Error: Unexpected error - {str(e)}"
```

**Pros**: Agent can read error and adapt
**Cons**: Error doesn't stop agent execution

### Strategy 2: Raise ValueError

```python
@tool
def strict_operation(data: str) -> str:
    """Process data with strict validation."""
    try:
        result = process(data)
        return f"Success: {result}"
    except ValueError as e:
        raise ValueError(f"Invalid input: {str(e)}")
```

**Pros**: Stops execution on critical errors
**Cons**: Agent must retry from scratch

### Strategy 3: Hybrid Approach

```python
@tool
def smart_operation(data: str) -> str:
    """Process data with smart error handling."""
    try:
        result = process(data)
        return f"Success: {result}"
    except ValueError as e:
        # Recoverable error - return message
        return f"Error: {str(e)}. Please provide valid input."
    except CriticalError as e:
        # Critical error - raise exception
        raise ValueError(f"Critical failure: {str(e)}")
```

**Pros**: Balance between flexibility and safety
**Cons**: Requires careful classification of errors

---

## 9. Testing Tools

### Unit Test Pattern

```python
import pytest
from your_module import calculator

def test_calculator_addition():
    """Test calculator with addition."""
    result = calculator.invoke({"expression": "5 + 3"})
    assert result == "8.0"

def test_calculator_complex():
    """Test calculator with complex expression."""
    result = calculator.invoke({"expression": "10 * (2 + 3)"})
    assert result == "50.0"

def test_calculator_invalid():
    """Test calculator error handling."""
    with pytest.raises(ValueError):
        calculator.invoke({"expression": "import os"})

def test_calculator_division_by_zero():
    """Test calculator division by zero."""
    with pytest.raises(ValueError):
        calculator.invoke({"expression": "10 / 0"})
```

### Integration Test Pattern

```python
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI

def test_agent_with_calculator():
    """Test agent can use calculator tool."""
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    tools = [calculator, get_weather]

    agent = create_react_agent(llm, tools)

    result = agent.invoke({
        "messages": [("user", "What is 156 * 42?")]
    })

    final_message = result["messages"][-1].content
    assert "6552" in final_message
```

---

## Summary: Tool Integration Checklist

When creating a new tool, ensure:

- [ ] Uses `@tool` decorator
- [ ] Has type annotations with `Annotated[type, "description"]`
- [ ] Has clear docstring with examples
- [ ] Returns strings for consistency
- [ ] Handles errors gracefully (return messages or raise ValueError)
- [ ] Includes timeout for external API calls
- [ ] Validates inputs (regex, type checks)
- [ ] Limits output size (don't return huge results)
- [ ] Focused on single responsibility
- [ ] Unit tests cover happy path and error cases

---

## References

- **LangChain Tools**: [/code/reference_agents/agents/react_multi_agent.py](../code/reference_agents/agents/react_multi_agent.py)
- **Calculator Pattern**: [/code/reference_agents/tools/calculator.py](../code/reference_agents/tools/calculator.py)
- **MCP Server**: [/braze-docs-mcp/server.py](../braze-docs-mcp/server.py)
- **LangChain Documentation**: https://python.langchain.com/docs/modules/tools/
- **MCP Protocol**: https://modelcontextprotocol.io/
