"""
Legacy adapter for CLI.
Provides backward compatibility with old import paths.
"""

from src.shared.ui.cli import (
    main,
    parse_arguments,
    setup_logging,
    print_banner,
    check_configuration,
    update_ytdlp,
)

__all__ = [
    'main',
    'parse_arguments',
    'setup_logging',
    'print_banner',
    'check_configuration',
    'update_ytdlp',
]

# Made with Bob