"""Setup script for braze_code_gen package."""

from setuptools import setup, find_packages
from pathlib import Path

# Read requirements.txt and filter out comments and empty lines
requirements_file = Path(__file__).parent / "requirements.txt"
install_requires = []

if requirements_file.exists():
    with open(requirements_file) as f:
        for line in f:
            line = line.strip()
            # Skip empty lines, comments, and section headers
            if line and not line.startswith("#") and not line.startswith("="):
                install_requires.append(line)

setup(
    name="braze_code_gen",
    version="0.1.0",
    description="Braze SDK Landing Page Generator",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=install_requires,
)
