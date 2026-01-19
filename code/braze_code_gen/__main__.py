"""Entry point for running braze_code_gen as a module.

This allows running the package with:
    python -m braze_code_gen

Launches the Streamlit UI.
"""

import sys
import os
from pathlib import Path
from streamlit.web import cli as stcli


def main():
    """Launch Streamlit UI."""
    # Get the path to streamlit_app.py
    app_path = Path(__file__).parent / "ui" / "streamlit_app.py"

    # Set up streamlit arguments
    sys.argv = [
        "streamlit",
        "run",
        str(app_path),
        "--server.port=7860",
        "--server.headless=true",
    ]

    # Launch streamlit
    sys.exit(stcli.main())


if __name__ == "__main__":
    main()
