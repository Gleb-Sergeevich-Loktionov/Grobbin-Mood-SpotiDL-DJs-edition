"""
Setup script for Spotify Playlist Downloader.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

# Read requirements
requirements_file = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_file.exists():
    with open(requirements_file, 'r', encoding='utf-8') as f:
        requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]

setup(
    name="spotify-playlist-downloader",
    version="1.0.0",
    author="Spotify Playlist Downloader Team",
    description="A production-ready CLI application for downloading Spotify playlists as audio files",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/spotify-playlist-downloader",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Multimedia :: Sound/Audio",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "spotify-dl=src.cli:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": ["config/*.yaml"],
    },
    keywords="spotify playlist downloader music audio mp3 youtube",
    project_urls={
        "Bug Reports": "https://github.com/yourusername/spotify-playlist-downloader/issues",
        "Source": "https://github.com/yourusername/spotify-playlist-downloader",
    },
)

# Made with Bob
