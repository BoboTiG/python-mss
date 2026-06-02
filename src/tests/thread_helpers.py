"""Helpers for tests that need to run work on background threads."""

from __future__ import annotations

import threading
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable


def run_threads(*targets: Callable[[], None], start_delay: float = 0.0) -> None:
    errors: list[Exception] = []

    def record(target: Callable[[], None]) -> None:
        try:
            target()
        except Exception as exc:  # noqa: BLE001 - transport worker failures to the main test thread.
            errors.append(exc)

    threads = [threading.Thread(target=record, args=(target,)) for target in targets]
    for index, thread in enumerate(threads):
        thread.start()
        if start_delay and index < len(threads) - 1:
            time.sleep(start_delay)
    for thread in threads:
        thread.join()

    if errors:
        raise errors[0]
