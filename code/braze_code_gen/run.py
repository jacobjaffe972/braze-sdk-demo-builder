#!/usr/bin/env python3
"""Launch script for Braze SDK Landing Page Generator UI.

This script launches the Gradio web interface for generating Braze SDK landing pages.

Usage:
    python -m braze_code_gen.run
    python -m braze_code_gen.run --port 8080
    python -m braze_code_gen.run --share  # Create public share link
    python -m braze_code_gen.run --no-browser-testing  # Disable Playwright tests
"""

import argparse
import logging
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file in repository root
env_path = Path(__file__).parent.parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """Main entry point for launching the UI."""
    parser = argparse.ArgumentParser(
        description="Braze SDK Landing Page Generator - Web UI"
    )

    parser.add_argument(
        "--port",
        type=int,
        default=7860,
        help="Port to run the server on (default: 7860)"
    )

    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host to run the server on (default: 0.0.0.0)"
    )

    parser.add_argument(
        "--share",
        action="store_true",
        help="Create a public Gradio share link"
    )

    parser.add_argument(
        "--export-dir",
        type=str,
        default="/tmp/braze_exports",
        help="Directory for exported HTML files (default: /tmp/braze_exports)"
    )

    parser.add_argument(
        "--no-browser-testing",
        action="store_true",
        help="Disable Playwright browser testing (faster, but no validation)"
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )

    args = parser.parse_args()

    # Set log level
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Debug logging enabled")

    # Check for required environment variables
    braze_api_key = os.getenv("BRAZE_API_KEY")
    braze_sdk_endpoint = os.getenv("BRAZE_SDK_ENDPOINT")

    if not braze_api_key:
        logger.warning(
            "BRAZE_API_KEY not set in environment. "
            "Users will need to enter API key manually in the UI."
        )

    if not braze_sdk_endpoint:
        logger.warning(
            "BRAZE_SDK_ENDPOINT not set in environment. "
            "Defaulting to sondheim.braze.com"
        )

    # Check Playwright installation if browser testing enabled
    if not args.no_browser_testing:
        try:
            import playwright
            logger.info("Playwright available - browser testing enabled")
        except ImportError:
            logger.warning(
                "Playwright not installed. Browser testing will be disabled. "
                "Install with: pip install playwright && playwright install chromium"
            )
            args.no_browser_testing = True

    # Create export directory
    os.makedirs(args.export_dir, exist_ok=True)
    logger.info(f"Export directory: {args.export_dir}")

    # Import and launch UI
    try:
        from braze_code_gen.ui.gradio_app import launch_ui

        logger.info("Starting Braze SDK Landing Page Generator...")
        logger.info(f"Server: http://{args.host}:{args.port}")

        if args.share:
            logger.info("Public share link will be generated...")

        launch_ui(
            export_dir=args.export_dir,
            enable_browser_testing=not args.no_browser_testing,
            share=args.share,
            server_name=args.host,
            server_port=args.port
        )

    except ImportError as e:
        logger.error(f"Failed to import UI module: {e}")
        logger.error("Make sure all dependencies are installed: pip install -r requirements.txt")
        sys.exit(1)

    except KeyboardInterrupt:
        logger.info("\nShutting down gracefully...")
        sys.exit(0)

    except Exception as e:
        logger.error(f"Error starting UI: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
