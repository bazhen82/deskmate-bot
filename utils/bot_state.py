"""Runtime state for polling: dedupe updates and skip stale queue messages."""

import time
from typing import Set

from telebot import types

_polling_ready_at: float | None = None
_processed_ids: Set[int] = set()
_MAX_IDS = 2000


def mark_polling_ready() -> None:
    """Call right before the polling loop starts (after queue clear)."""
    global _polling_ready_at
    _polling_ready_at = time.time()


def should_process_update(update: types.Update) -> bool:
    """Skip duplicate update_ids and messages from before bot was ready."""
    global _processed_ids

    if update.update_id in _processed_ids:
        return False

    _processed_ids.add(update.update_id)
    if len(_processed_ids) > _MAX_IDS:
        _processed_ids = set(list(_processed_ids)[-_MAX_IDS // 2 :])

    if _polling_ready_at is None:
        return True

    msg = update.message or update.edited_message
    if msg and msg.date < _polling_ready_at - 10:
        return False

    return True
