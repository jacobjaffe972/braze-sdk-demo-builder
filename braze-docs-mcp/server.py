#!/usr/bin/env python3
"""
Braze Documentation MCP Server

This server scrapes Braze's public documentation and makes it available
as MCP resources and tools for goose to access.

Features:
- Resource access: doc://docs/page-title -> Returns page content
- Search tool: Search all documentation for specific queries
- Code extraction: Extract code examples from documentation
"""

import json
import logging
import re
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
from mcp.server.fastmcp import FastMCP
import requests
from bs4 import BeautifulSoup

# Configure logging
logging.basicConfig(
    filename='mcp_extension.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create MCP server
mcp = FastMCP("Braze Documentation")

# Storage for scraped documentation
DOCS_CACHE_FILE = Path("braze_docs_cache.json")
docs_data = {}


@dataclass
class DocPage:
    """Represents a documentation page"""
    title: str
    url: str
    content: str
    code_examples: list[str]
    sections: dict[str, str]


def is_valid_doc_url(url: str) -> bool:
    """Check if URL is a valid Braze documentation page"""
    return url.startswith("https://www.braze.com/docs/") and not url.endswith("#")


def extract_code_examples(html: str) -> list[str]:
    """Extract code examples from HTML content"""
    soup = BeautifulSoup(html, "lxml")
    code_blocks = soup.find_all(["code", "pre"])
    examples = []
    
    for block in code_blocks:
        code_text = block.get_text(strip=True)
        if code_text and len(code_text) > 10:  # Filter out very short snippets
            examples.append(code_text)
    
    return examples[:10]  # Limit to 10 examples per page


def extract_sections(html: str) -> dict[str, str]:
    """Extract main sections from documentation page"""
    soup = BeautifulSoup(html, "lxml")
    sections = {}
    
    # Extract headings and their following content
    current_section = "Introduction"
    section_content = []
    
    for element in soup.find_all(["h1", "h2", "h3", "p"]):
        if element.name in ["h1", "h2"]:
            if section_content:
                sections[current_section] = "\n".join(section_content)
            current_section = element.get_text(strip=True)
            section_content = []
        elif element.name == "p":
            text = element.get_text(strip=True)
            if text:
                section_content.append(text)
    
    if section_content:
        sections[current_section] = "\n".join(section_content)
    
    return sections


def scrape_documentation() -> None:
    """Scrape Braze documentation and cache it"""
    global docs_data
    
    logger.info("Starting Braze documentation scrape...")
    print("🔄 Scraping Braze documentation (this may take a moment)...")
    
    try:
        # Load cache if it exists
        if DOCS_CACHE_FILE.exists():
            logger.info("Loading documentation from cache...")
            with open(DOCS_CACHE_FILE, 'r') as f:
                docs_data = json.load(f)
            print(f"✅ Loaded {len(docs_data)} cached documentation pages")
            return
        
        # Start with common entry points
        base_urls = [
            "https://www.braze.com/docs/",
            "https://www.braze.com/docs/user_guide/",
            "https://www.braze.com/docs/api/",
            "https://www.braze.com/docs/developer_guide/",
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
            
            if url in visited_urls or not is_valid_doc_url(url):
                continue
            
            visited_urls.add(url)
            
            try:
                logger.debug(f"Fetching {url}")
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
                
                content = content_div.get_text(separator="\n", strip=True)[:5000]  # Limit length
                
                # Extract code examples
                code_examples = extract_code_examples(response.content.decode('utf-8', errors='ignore'))
                
                # Extract sections
                sections = extract_sections(response.content.decode('utf-8', errors='ignore'))
                
                # Store the page
                page_key = url.replace("https://www.braze.com/docs/", "").rstrip("/")
                docs_data[page_key] = {
                    "title": title,
                    "url": url,
                    "content": content,
                    "code_examples": code_examples,
                    "sections": sections
                }
                
                page_count += 1
                print(f"  ✓ {page_count}. {title[:60]}")
                
                # Extract links to other documentation pages
                for link in soup.find_all("a", href=True):
                    href = link["href"]
                    if href.startswith("/docs/"):
                        full_url = "https://www.braze.com" + href
                    elif href.startswith("https://www.braze.com/docs/"):
                        full_url = href
                    else:
                        continue
                    
                    if full_url not in visited_urls:
                        to_visit.append(full_url)
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Failed to fetch {url}: {str(e)}")
                continue
        
        # Save cache
        with open(DOCS_CACHE_FILE, 'w') as f:
            json.dump(docs_data, f, indent=2)
        
        logger.info(f"Successfully scraped {page_count} documentation pages")
        print(f"✅ Successfully scraped {page_count} documentation pages!")
        
    except Exception as e:
        logger.error(f"Scraping failed: {str(e)}", exc_info=True)
        print(f"❌ Scraping failed: {str(e)}")


@mcp.resource("doc://{page_path}")
def get_documentation_page(page_path: str) -> str:
    """
    Get a specific documentation page by path.
    
    Example: doc://user_guide/introduction or doc://api/endpoints/users
    """
    logger.debug(f"Retrieving documentation page: {page_path}")
    
    if page_path not in docs_data:
        # Try with or without trailing slashes
        alternatives = [
            page_path,
            page_path.rstrip("/"),
            page_path + "/",
        ]
        
        for alt in alternatives:
            if alt in docs_data:
                page_path = alt
                break
        else:
            logger.warning(f"Documentation page not found: {page_path}")
            available_pages = list(docs_data.keys())[:10]
            return f"Page '{page_path}' not found. Available pages include:\n" + "\n".join(available_pages)
    
    page = docs_data[page_path]
    
    # Format the response
    response = f"""# {page['title']}

**URL:** {page['url']}

## Content

{page['content']}

"""
    
    # Add sections if available
    if page['sections']:
        response += "## Sections\n\n"
        for section_title, section_content in page['sections'].items():
            response += f"### {section_title}\n{section_content[:500]}\n\n"
    
    # Add code examples if available
    if page['code_examples']:
        response += "## Code Examples\n\n"
        for i, example in enumerate(page['code_examples'][:5], 1):
            response += f"### Example {i}\n```\n{example}\n```\n\n"
    
    return response


@mcp.tool()
def search_documentation(query: str) -> str:
    """
    Search all documentation for pages matching your query.
    Returns matching page titles, URLs, and relevant snippets.
    """
    logger.info(f"Searching documentation for: {query}")
    
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
    
    response = f"Found {len(results)} matching pages:\n\n"
    
    for i, result in enumerate(results[:10], 1):
        response += f"{i}. **{result['title']}**\n"
        response += f"   Path: `doc://{result['page_path']}`\n"
        response += f"   URL: {result['url']}\n"
        response += f"   Snippet: ...{result['snippet']}...\n\n"
    
    return response


@mcp.tool()
def list_documentation() -> str:
    """
    List all available documentation pages.
    Returns titles and paths for all scraped pages.
    """
    logger.info("Listing all documentation")
    
    if not docs_data:
        return "No documentation loaded."
    
    response = f"Available documentation pages ({len(docs_data)} total):\n\n"
    
    for i, (page_path, page) in enumerate(list(docs_data.items())[:50], 1):
        response += f"{i}. **{page['title']}**\n   `doc://{page_path}`\n"
    
    if len(docs_data) > 50:
        response += f"\n... and {len(docs_data) - 50} more pages"
    
    return response


@mcp.tool()
def extract_code_from_page(page_path: str) -> str:
    """
    Extract all code examples from a specific documentation page.
    """
    logger.debug(f"Extracting code examples from: {page_path}")
    
    if page_path not in docs_data:
        return f"Page '{page_path}' not found."
    
    page = docs_data[page_path]
    
    if not page['code_examples']:
        return f"No code examples found on page '{page_path}'."
    
    response = f"Code examples from **{page['title']}**:\n\n"
    
    for i, example in enumerate(page['code_examples'], 1):
        response += f"### Example {i}\n```\n{example}\n```\n\n"
    
    return response


def main():
    """Initialize and run the MCP server"""
    logger.info("Starting Braze Documentation MCP Server")
    print("🚀 Starting Braze Documentation MCP Server...")
    
    # Scrape documentation on startup
    scrape_documentation()
    
    # Run the server
    print("\n✅ Server initialized. Connecting to goose...")
    logger.info(f"Loaded {len(docs_data)} documentation pages")
    mcp.run()


if __name__ == "__main__":
    main()
