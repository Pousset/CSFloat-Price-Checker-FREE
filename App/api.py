import hashlib
import io
import json
import os
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from PIL import Image

from config import API_BASE, SKINS_API

SKINS_CACHE_PATH = os.path.join(os.path.dirname(__file__), ".skins_cache.json")
SKINS_CACHE_TTL  = 7 * 24 * 3600  # 7 jours

IMG_CACHE_DIR   = os.path.join(os.path.dirname(__file__), ".img_cache")
IMG_CACHE_INDEX = os.path.join(IMG_CACHE_DIR, "index.json")
_IMG_BG         = (30, 34, 48)  # correspond à CARD "#1e2230"


def get_img_cache_path(url: str) -> str:
    """Retourne le chemin JPEG local pour une URL d'image."""
    h = hashlib.md5(url.encode()).hexdigest()
    return os.path.join(IMG_CACHE_DIR, f"{h}.jpg")


def cache_img(url: str) -> str | None:
    """
    Retourne le chemin JPEG local de l'image.
    Si absent du cache, la télécharge, la composite sur fond sombre et la sauvegarde.
    """
    path = get_img_cache_path(url)
    if os.path.exists(path):
        return path
    try:
        os.makedirs(IMG_CACHE_DIR, exist_ok=True)
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        src = Image.open(io.BytesIO(r.content)).convert("RGBA")
        bg  = Image.new("RGB", src.size, _IMG_BG)
        bg.paste(src, mask=src.split()[3])          # composite alpha sur fond sombre
        bg.save(path, "JPEG", quality=85, optimize=True)
        return path
    except Exception:
        return None


def _write_img_index(skins: list[dict]) -> None:
    """Écrit (ou recrée) index.json : name → filename.jpg pour tous les skins en cache."""
    index = {}
    for s in skins:
        name = s.get("name") or s.get("market_hash_name", "")
        url  = s.get("image", "")
        if not name or not url:
            continue
        fname = os.path.basename(get_img_cache_path(url))
        if os.path.exists(os.path.join(IMG_CACHE_DIR, fname)):
            index[name] = fname
    tmp = IMG_CACHE_INDEX + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)
    os.replace(tmp, IMG_CACHE_INDEX)  # écriture atomique


def get_img_path_by_name(name: str) -> str | None:
    """Retourne le chemin JPEG local d'un skin à partir de son nom (via index.json)."""
    if not os.path.exists(IMG_CACHE_INDEX):
        return None
    with open(IMG_CACHE_INDEX, "r", encoding="utf-8") as f:
        index = json.load(f)
    fname = index.get(name)
    if not fname:
        return None
    path = os.path.join(IMG_CACHE_DIR, fname)
    return path if os.path.exists(path) else None


def prefetch_all_skin_images(
    skins: list[dict],
    max_workers: int = 8,
    progress_cb=None,
) -> None:
    """
    Pré-télécharge en parallèle toutes les images de skins manquantes dans le cache JPEG,
    puis met à jour index.json (name → filename.jpg).
    progress_cb(done: int, total: int) est appelé après chaque image si fourni.
    """
    urls = [
        s["image"] for s in skins
        if s.get("image") and not os.path.exists(get_img_cache_path(s["image"]))
    ]
    total = len(urls)
    done  = 0
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(cache_img, u): u for u in urls}
        for f in as_completed(futures):
            done += 1
            if progress_cb:
                progress_cb(done, total)
    _write_img_index(skins)


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
        headers={
            "Authorization": api_key,
            "Accept": "application/json",
        },
        params=params,
        timeout=15,
    )
    if resp.status_code == 403:
        body = resp.text[:300].strip()
        raise requests.HTTPError(
            f"403 Forbidden — CSFloat a refusé la requête.\nRéponse : {body}",
            response=resp,
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
