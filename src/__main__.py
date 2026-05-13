"""
Entry point for running the application as a module.
Allows execution via: python -m src
"""

import sys
from pathlib import Path

# Добавить корневую директорию в путь
sys.path.insert(0, str(Path(__file__).parent.parent))

from main import main

if __name__ == '__main__':
    sys.exit(main())

# Made with Bob
