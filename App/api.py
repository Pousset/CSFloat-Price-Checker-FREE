import json
import os
import statistics
import time

import requests

from config import API_BASE, SKINS_API

SKINS_CACHE_PATH = os.path.join(os.path.dirname(__file__), ".skins_cache.json")
SKINS_CACHE_TTL  = 7 * 24 * 3600  # 7 jours


def fetch_skins_db() -> list[dict]:
    if os.path.exists(SKINS_CACHE_PATH):
        if time.time() - os.path.getmtime(SKINS_CACHE_PATH) < SKINS_CACHE_TTL:
            with open(SKINS_CACHE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
    r = requests.get(SKINS_API, timeout=20)
    r.raise_for_status()
    data = r.json()
    with open(SKINS_CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f)
    return data


def fetch_listings(api_key: str, market_hash_name: str,
                   min_float: float | None = None,
                   max_float: float | None = None,
                   category: int = 0,
                   limit: int = 50) -> list[dict]:
    params = {
        "market_hash_name": market_hash_name,
        "limit": limit,
        "sort_by": "lowest_price",
        "type": "buy_now",
        "category": category,
    }
    if min_float is not None:
        params["min_float"] = min_float
    if max_float is not None:
        params["max_float"] = max_float
    resp = requests.get(
        f"{API_BASE}/listings",
        headers={"Authorization": api_key},
        params=params,
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    return data if isinstance(data, list) else data.get("data", [])


def analyze_prices(listings: list[dict]) -> dict:
    prices = [l["price"] for l in listings if "price" in l]
    if not prices:
        return {}
    return {
        "count":  len(prices),
        "min":    min(prices),
        "max":    max(prices),
        "mean":   statistics.mean(prices),
        "median": statistics.median(prices),
        "stdev":  statistics.stdev(prices) if len(prices) > 1 else 0,
    }


def fetch_eur_rate() -> float:
    try:
        r = requests.get("https://open.er-api.com/v6/latest/USD", timeout=8)
        return r.json()["rates"]["EUR"]
    except Exception:
        return 0.92


def fetch_steam_inventory(steam_id: str) -> list[dict]:
    """
    Retourne la liste des skins marketables de l'inventaire CS2.
    Lève ValueError si l'inventaire est privé/introuvable.
    """
    HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    assets: list = []
    descriptions_raw: list = []
    last_assetid = None

    while True:
        params = {"l": "english", "count": 2000}
        if last_assetid:
            params["start_assetid"] = last_assetid

        r = requests.get(
            f"https://steamcommunity.com/inventory/{steam_id}/730/2",
            headers=HEADERS,
            params=params,
            timeout=15,
        )
        if r.status_code == 403:
            raise ValueError("Inventaire privé ou profil introuvable.")
        if r.status_code == 429:
            raise ValueError("Rate limit Steam — réessaie dans quelques secondes.")
        r.raise_for_status()

        data = r.json()
        if not data or data.get("success") == 0:
            raise ValueError("Inventaire inaccessible (privé ou inexistant).")

        assets += data.get("assets", [])
        descriptions_raw += data.get("descriptions", [])

        if data.get("more_items") and data.get("last_assetid"):
            last_assetid = data["last_assetid"]
            time.sleep(1)
        else:
            break

    descriptions = {
        (d["classid"], d.get("instanceid", "0")): d
        for d in descriptions_raw
    }

    items = []
    for asset in assets:
        key  = (asset["classid"], asset.get("instanceid", "0"))
        desc = descriptions.get(key, {})
        if not desc.get("marketable", 0):
            continue
        name = desc.get("market_hash_name", "")
        if " | " not in name:
            continue
        items.append({"name": name, "icon_url": desc.get("icon_url", "")})

    return items
