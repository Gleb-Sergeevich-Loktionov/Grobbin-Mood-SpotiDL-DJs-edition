"""Minimal observer pattern for progress events."""

from __future__ import annotations

import logging
from typing import Any, List, Optional

logger = logging.getLogger(__name__)


class ProgressSubject:
    """Subject that notifies attached observers of progress events."""

    def __init__(self):
        self._observers: List[Any] = []

    def attach(self, observer: Any) -> None:
        if observer not in self._observers:
            self._observers.append(observer)

    def detach(self, observer: Any) -> None:
        if observer in self._observers:
            self._observers.remove(observer)

    def notify(self, event: str, data: Optional[Any] = None) -> None:
        for observer in self._observers:
            observer.update(event, data)


class ConsoleObserver:
    """Prints progress events to the console."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose

    def update(self, event: str, data: Optional[Any] = None) -> None:
        if self.verbose:
            print(f"[{event}] {data}" if data is not None else f"[{event}]")


class FileObserver:
    """Logs progress events to a file via the logging module."""

    def __init__(self, log_file):
        self.log_file = log_file
        self._logger = logging.getLogger("spotify_downloader.progress")

    def update(self, event: str, data: Optional[Any] = None) -> None:
        self._logger.info("%s %s", event, data if data is not None else "")
