import json
import os
import sys
import threading
from datetime import datetime, timezone
from typing import Any


APP_NAME = "CSFloat Price Checker"
HISTORY_FILENAME = "price_history.json"
_LOCK = threading.Lock()


def get_user_data_dir() -> str:
    if getattr(sys, "frozen", False):
        base = os.getenv("LOCALAPPDATA") or os.path.expanduser("~")
        return os.path.join(base, APP_NAME)
    return os.path.dirname(__file__)


def get_history_path(path: str | None = None) -> str:
    return path or os.path.join(get_user_data_dir(), HISTORY_FILENAME)


def _empty_history() -> dict[str, Any]:
    return {"version": 1, "searches": []}


def load_price_history(path: str | None = None) -> dict[str, Any]:
    history_path = get_history_path(path)
    if not os.path.exists(history_path):
        return _empty_history()
    with open(history_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        return _empty_history()
    searches = data.get("searches")
    if not isinstance(searches, list):
        data["searches"] = []
    data.setdefault("version", 1)
    return data


def _write_history(history: dict[str, Any], path: str | None = None) -> str:
    history_path = get_history_path(path)
    os.makedirs(os.path.dirname(history_path), exist_ok=True)
    tmp_path = history_path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, history_path)
    return history_path


def init_price_history(path: str | None = None) -> str:
    history_path = get_history_path(path)
    if not os.path.exists(history_path):
        _write_history(_empty_history(), history_path)
    return history_path


def save_price_search(
    market_hash_name: str,
    listings: list[dict[str, Any]],
    stats: dict[str, Any] | None = None,
    *,
    min_float: float | None = None,
    max_float: float | None = None,
    category: int = 0,
    limit_requested: int | None = None,
    source: str = "price_view",
    path: str | None = None,
    db_path: str | None = None,
) -> int:
    history_path = get_history_path(path or db_path)
    with _LOCK:
        history = load_price_history(history_path)
        searches = history.setdefault("searches", [])
        next_id = (max((int(s.get("id", 0)) for s in searches), default=0) + 1)
        searches.append(
            {
                "id": next_id,
                "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "source": source,
                "market_hash_name": market_hash_name,
                "min_float": min_float,
                "max_float": max_float,
                "category": category,
                "limit_requested": limit_requested,
                "listing_count": len(listings),
                "stats": stats or {},
                "listings": listings,
            }
        )
        _write_history(history, history_path)
        return next_id


def get_recent_price_searches(
    limit: int = 50,
    path: str | None = None,
    db_path: str | None = None,
) -> list[dict[str, Any]]:
    history = load_price_history(path or db_path)
    searches = history.get("searches", [])
    if not isinstance(searches, list):
        return []
    return list(reversed(searches))[:limit]
