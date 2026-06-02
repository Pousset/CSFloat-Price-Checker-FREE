"""
Script utilitaire : télécharge et met en cache toutes les images de skins en JPEG.
Usage : python prefetch_images.py [--workers N]
"""
import argparse
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "App"))

from api import IMG_CACHE_DIR, fetch_skins_db, get_img_cache_path, prefetch_all_skin_images


def main():
    parser = argparse.ArgumentParser(description="Pré-cache toutes les images de skins.")
    parser.add_argument("--workers", type=int, default=8,
                        help="Nombre de téléchargements parallèles (défaut : 8)")
    args = parser.parse_args()

    print("Chargement de la base de skins...")
    skins = fetch_skins_db()

    total_skins = len([s for s in skins if s.get("image")])
    already     = sum(1 for s in skins
                      if s.get("image") and os.path.exists(get_img_cache_path(s["image"])))
    to_download = total_skins - already

    print(f"{total_skins} skins trouvés · {already} déjà en cache · {to_download} à télécharger")
    print(f"Dossier de cache : {IMG_CACHE_DIR}")

    if to_download == 0:
        print("Tout est déjà en cache, reconstruction de l'index...")

    def progress(done, total):
        pct  = done / total * 100
        bar  = "#" * int(pct / 2) + "-" * (50 - int(pct / 2))
        print(f"\r[{bar}] {done}/{total} ({pct:.1f}%)", end="", flush=True)

    prefetch_all_skin_images(skins, max_workers=args.workers, progress_cb=progress)
    print(f"\nTerminé ! {to_download} images téléchargées dans {IMG_CACHE_DIR}")

    from api import IMG_CACHE_INDEX
    import json as _json
    with open(IMG_CACHE_INDEX, encoding="utf-8") as f:
        index = _json.load(f)
    print(f"index.json mis à jour : {len(index)} entrées -> {IMG_CACHE_INDEX}")


if __name__ == "__main__":
    main()
