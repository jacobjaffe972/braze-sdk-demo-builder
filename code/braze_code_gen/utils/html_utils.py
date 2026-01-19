"""HTML utility functions for cleaning and processing LLM-generated HTML."""


def clean_html_response(html_content: str) -> str:
    """Clean HTML response from LLM by removing markdown code blocks and ensuring proper structure.

    Args:
        html_content: Raw HTML content from LLM response, may contain markdown code blocks

    Returns:
        Cleaned HTML content with DOCTYPE declaration

    Example:
        >>> clean_html_response("```html\\n<html>...</html>\\n```")
        "<!DOCTYPE html>\\n<html>...</html>"
    """
    # Remove markdown code blocks
    if "```html" in html_content:
        html_content = html_content.split("```html")[1]
        if "```" in html_content:
            html_content = html_content.split("```")[0]
    elif "```" in html_content:
        # Generic code block
        parts = html_content.split("```")
        if len(parts) >= 2:
            html_content = parts[1]

    # Strip whitespace
    html_content = html_content.strip()

    # Ensure starts with DOCTYPE
    if not html_content.upper().startswith("<!DOCTYPE"):
        if html_content.upper().startswith("<HTML"):
            html_content = "<!DOCTYPE html>\n" + html_content

    return html_content
