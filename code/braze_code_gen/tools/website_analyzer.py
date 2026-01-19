"""Website analyzer tool for extracting branding data.

This module provides functionality to scrape customer websites and extract:
- Color schemes (primary, secondary, accent colors)
- Typography (font families, sizes)
"""

import re
import logging
from typing import Optional, Dict, List, Tuple
from collections import Counter
from urllib.parse import urljoin, urlparse
import urllib3

import requests
from bs4 import BeautifulSoup
import cssutils

from braze_code_gen.core.models import (
    BrandingData,
    ColorScheme,
    TypographyData,
    DEFAULT_BRAZE_COLORS,
    DEFAULT_BRAZE_TYPOGRAPHY,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Suppress cssutils warnings
cssutils.log.setLevel(logging.CRITICAL)

# Suppress SSL warnings when verification is disabled
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class WebsiteAnalyzer:
    """Analyzer for extracting branding data from websites."""

    def __init__(
        self,
        timeout: int = 10,
        max_retries: int = 2,
        user_agents: Optional[List[str]] = None
    ):
        """Initialize the website analyzer.

        Args:
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
            user_agents: List of User-Agent strings to try
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.user_agents = user_agents or [
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        ]

    def analyze_website(self, url: str) -> BrandingData:
        """Analyze website and extract branding data.

        Args:
            url: Website URL to analyze

        Returns:
            BrandingData: Extracted branding information

        Example:
            >>> analyzer = WebsiteAnalyzer()
            >>> branding = analyzer.analyze_website("https://nike.com")
            >>> print(branding.colors.primary)
            '#111111'
        """
        logger.info(f"Analyzing website: {url}")

        # Ensure URL has protocol
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url

        # Try to fetch website
        html_content = self._fetch_website(url)

        if html_content is None:
            logger.warning(f"Failed to fetch {url}, using default branding")
            return self._create_fallback_branding(url, "Failed to fetch website")

        # Parse HTML
        soup = BeautifulSoup(html_content, 'html.parser')

        # Extract colors
        colors = self._extract_colors(soup, html_content, url)

        # Extract typography
        typography = self._extract_typography(soup, html_content, url)

        # Determine if extraction was successful (at least one extraction succeeded)
        extraction_success = colors is not None or typography is not None
        fallback_used = not extraction_success

        # Build extraction notes
        extracted_items = []
        if colors is not None:
            extracted_items.append("colors")
        if typography is not None:
            extracted_items.append("typography")

        if extracted_items:
            extraction_notes = f"Successfully extracted {', '.join(extracted_items)}"
            if colors is None:
                extraction_notes += " (using default colors)"
            elif typography is None:
                extraction_notes += " (using default typography)"
        else:
            extraction_notes = "Used default Braze branding (extraction failed)"

        # Use defaults if extraction failed
        if colors is None:
            colors = DEFAULT_BRAZE_COLORS
        if typography is None:
            typography = DEFAULT_BRAZE_TYPOGRAPHY

        return BrandingData(
            website_url=url,
            colors=colors,
            typography=typography,
            extraction_success=extraction_success,
            fallback_used=fallback_used,
            extraction_notes=extraction_notes
        )

    def _fetch_website(self, url: str) -> Optional[str]:
        """Fetch website HTML with retry logic and SSL fallback.

        Args:
            url: Website URL

        Returns:
            Optional[str]: HTML content or None if failed
        """
        ssl_error_occurred = False

        for attempt in range(self.max_retries):
            user_agent = self.user_agents[attempt % len(self.user_agents)]
            headers = {'User-Agent': user_agent}

            try:
                response = requests.get(
                    url,
                    headers=headers,
                    timeout=self.timeout,
                    allow_redirects=True,
                    verify=True
                )
                response.raise_for_status()
                return response.text

            except requests.exceptions.SSLError as e:
                ssl_error_occurred = True
                logger.warning(f"SSL certificate verification failed for {url}: {str(e)}")

            except requests.Timeout:
                logger.warning(f"Timeout fetching {url} (attempt {attempt + 1}/{self.max_retries})")

            except requests.RequestException as e:
                logger.warning(f"Error fetching {url}: {str(e)} (attempt {attempt + 1}/{self.max_retries})")

        # If SSL error occurred, retry once without verification
        if ssl_error_occurred:
            logger.info(f"Retrying {url} with SSL verification disabled")
            try:
                response = requests.get(
                    url,
                    headers={'User-Agent': self.user_agents[0]},
                    timeout=self.timeout,
                    allow_redirects=True,
                    verify=False  # Disable SSL verification as fallback
                )
                response.raise_for_status()
                logger.info(f"Successfully fetched {url} with SSL verification disabled")
                return response.text

            except requests.RequestException as e:
                logger.warning(f"Failed to fetch {url} even with SSL verification disabled: {str(e)}")

        return None

    def _extract_colors(
        self,
        soup: BeautifulSoup,
        html_content: str,
        base_url: str
    ) -> Optional[ColorScheme]:
        """Extract color scheme from website.

        Strategy:
        1. Parse inline styles and style tags
        2. Fetch and parse linked stylesheets
        3. Extract all color values (hex, rgb, rgba)
        4. Use frequency analysis to identify primary colors
        5. Categorize by usage (background, text, accent)

        Args:
            soup: BeautifulSoup parsed HTML
            html_content: Raw HTML content
            base_url: Base URL for resolving relative links

        Returns:
            Optional[ColorScheme]: Extracted colors or None if failed
        """
        logger.info("Extracting colors...")
        colors_found: List[str] = []

        # 1. Extract from inline styles
        for element in soup.find_all(style=True):
            style = element['style']
            colors_found.extend(self._parse_colors_from_css(style))

        # 2. Extract from style tags
        for style_tag in soup.find_all('style'):
            if style_tag.string:
                colors_found.extend(self._parse_colors_from_css(style_tag.string))

        # 3. Extract from linked stylesheets (limited to first 3)
        for link in soup.find_all('link', rel='stylesheet', href=True)[:3]:
            css_url = urljoin(base_url, link['href'])
            css_content = self._fetch_css(css_url)
            if css_content:
                colors_found.extend(self._parse_colors_from_css(css_content))

        if not colors_found:
            logger.warning("No colors found in website")
            return None

        # Normalize and count colors
        normalized_colors = [self._normalize_color(c) for c in colors_found]
        normalized_colors = [c for c in normalized_colors if c]  # Remove None values
        color_counts = Counter(normalized_colors)

        # Get most common colors
        most_common = color_counts.most_common(10)
        logger.info(f"Found {len(most_common)} unique colors")

        if len(most_common) < 3:
            logger.warning("Not enough colors found")
            return None

        # Categorize colors
        return self._categorize_colors(most_common)

    def _parse_colors_from_css(self, css_text: str) -> List[str]:
        """Parse colors from CSS text.

        Args:
            css_text: CSS content

        Returns:
            List[str]: List of color values found
        """
        colors = []

        # Hex colors
        hex_colors = re.findall(r'#[0-9A-Fa-f]{6}|#[0-9A-Fa-f]{3}', css_text)
        colors.extend(hex_colors)

        # RGB/RGBA colors
        rgb_colors = re.findall(r'rgba?\([^)]+\)', css_text)
        colors.extend(rgb_colors)

        return colors

    def _normalize_color(self, color: str) -> Optional[str]:
        """Normalize color to 6-digit hex format.

        Args:
            color: Color in any format

        Returns:
            Optional[str]: Normalized hex color or None
        """
        color = color.strip().lower()

        # Already 6-digit hex
        if re.match(r'^#[0-9a-f]{6}$', color):
            return color.upper()

        # 3-digit hex - expand
        if re.match(r'^#[0-9a-f]{3}$', color):
            return '#' + ''.join([c*2 for c in color[1:]]).upper()

        # RGB/RGBA - convert to hex
        if color.startswith('rgb'):
            match = re.match(r'rgba?\((\d+),\s*(\d+),\s*(\d+)', color)
            if match:
                r, g, b = match.groups()
                return f"#{int(r):02X}{int(g):02X}{int(b):02X}"

        return None

    def _categorize_colors(self, color_counts: List[Tuple[str, int]]) -> ColorScheme:
        """Categorize colors into primary, secondary, accent, etc.

        Args:
            color_counts: List of (color, count) tuples

        Returns:
            ColorScheme: Categorized colors
        """
        colors = [c[0] for c in color_counts]

        # Filter out pure white and black (often background/text)
        non_bw_colors = [c for c in colors if c not in ['#FFFFFF', '#000000']]

        if len(non_bw_colors) >= 3:
            primary = non_bw_colors[0]
            secondary = non_bw_colors[1]
            accent = non_bw_colors[2]
        elif len(non_bw_colors) >= 1:
            primary = non_bw_colors[0]
            secondary = colors[1] if len(colors) > 1 else "#2196F3"
            accent = colors[2] if len(colors) > 2 else "#FF5722"
        else:
            # Fallback
            return DEFAULT_BRAZE_COLORS

        # Determine background and text
        background = "#FFFFFF"
        text = "#333333"

        # If white is in top colors, use it as background
        if '#FFFFFF' in colors[:5]:
            background = "#FFFFFF"
            text = "#333333"
        # If black is in top colors, maybe dark theme
        elif '#000000' in colors[:5]:
            background = "#FFFFFF"  # Still use light background for safety
            text = "#000000"

        return ColorScheme(
            primary=primary,
            secondary=secondary,
            accent=accent,
            background=background,
            text=text
        )

    def _extract_typography(
        self,
        soup: BeautifulSoup,
        html_content: str,
        base_url: str
    ) -> Optional[TypographyData]:
        """Extract typography from website.

        Strategy:
        1. Find font-family declarations in CSS
        2. Extract from body, h1-h6, p tags
        3. Look for Google Fonts links
        4. Identify most common fonts

        Args:
            soup: BeautifulSoup parsed HTML
            html_content: Raw HTML content
            base_url: Base URL

        Returns:
            Optional[TypographyData]: Extracted typography or None
        """
        logger.info("Extracting typography...")
        fonts_found: List[str] = []

        # 1. Extract from inline styles
        for element in soup.find_all(style=True):
            style = element['style']
            font_families = re.findall(r'font-family:\s*([^;]+)', style)
            fonts_found.extend(font_families)

        # 2. Extract from style tags
        for style_tag in soup.find_all('style'):
            if style_tag.string:
                font_families = re.findall(r'font-family:\s*([^;]+)', style_tag.string)
                fonts_found.extend(font_families)

        # 3. Check for Google Fonts
        google_fonts = []
        for link in soup.find_all('link', href=True):
            if 'fonts.googleapis.com' in link['href']:
                # Extract font name from URL
                match = re.search(r'family=([^&:]+)', link['href'])
                if match:
                    google_fonts.append(match.group(1).replace('+', ' '))

        if not fonts_found and not google_fonts:
            logger.warning("No fonts found in website")
            return None

        # Process found fonts
        all_fonts = fonts_found + google_fonts
        cleaned_fonts = [self._clean_font_family(f) for f in all_fonts]
        cleaned_fonts = [f for f in cleaned_fonts if f]

        if not cleaned_fonts:
            return None

        # Get most common fonts
        font_counts = Counter(cleaned_fonts)
        most_common_fonts = [f[0] for f in font_counts.most_common(5)]

        # Determine primary and heading fonts
        primary_font = most_common_fonts[0] if most_common_fonts else "'Inter', sans-serif"
        heading_font = most_common_fonts[1] if len(most_common_fonts) > 1 else primary_font

        return TypographyData(
            primary_font=primary_font,
            heading_font=heading_font,
            base_size="16px",
            heading_scale=["32px", "28px", "24px", "20px", "18px", "16px"]
        )

    def _clean_font_family(self, font_family: str) -> Optional[str]:
        """Clean and normalize font-family string.

        Args:
            font_family: Raw font-family value

        Returns:
            Optional[str]: Cleaned font-family or None
        """
        font_family = font_family.strip().strip('"').strip("'")

        # Remove !important
        font_family = re.sub(r'!important', '', font_family).strip()

        # Take first font in stack
        if ',' in font_family:
            fonts = [f.strip().strip('"').strip("'") for f in font_family.split(',')]
            # Skip generic families
            fonts = [f for f in fonts if f.lower() not in ['sans-serif', 'serif', 'monospace', 'cursive', 'fantasy']]
            if fonts:
                font_family = fonts[0]
            else:
                return None

        # Ensure quoted if contains spaces
        if ' ' in font_family and not (font_family.startswith("'") or font_family.startswith('"')):
            font_family = f"'{font_family}'"

        # Add fallback
        if 'sans-serif' not in font_family.lower():
            font_family = f"{font_family}, sans-serif"

        return font_family

    def _fetch_css(self, url: str) -> Optional[str]:
        """Fetch CSS file content with SSL fallback.

        Args:
            url: CSS file URL

        Returns:
            Optional[str]: CSS content or None
        """
        try:
            response = requests.get(
                url,
                headers={'User-Agent': self.user_agents[0]},
                timeout=5,
                verify=True
            )
            response.raise_for_status()
            return response.text
        except requests.exceptions.SSLError:
            # Retry with SSL verification disabled
            try:
                response = requests.get(
                    url,
                    headers={'User-Agent': self.user_agents[0]},
                    timeout=5,
                    verify=False
                )
                response.raise_for_status()
                return response.text
            except requests.RequestException:
                return None
        except requests.RequestException:
            return None

    def _create_fallback_branding(self, url: str, reason: str) -> BrandingData:
        """Create fallback branding with default values.

        Args:
            url: Website URL
            reason: Reason for fallback

        Returns:
            BrandingData: Fallback branding
        """
        return BrandingData(
            website_url=url,
            colors=DEFAULT_BRAZE_COLORS,
            typography=DEFAULT_BRAZE_TYPOGRAPHY,
            extraction_success=False,
            fallback_used=True,
            extraction_notes=f"Fallback: {reason}"
        )
