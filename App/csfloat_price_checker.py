"""
CSFloat Price Checker - CLI
"""
import json
import os
import sys

import requests
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api import analyze_prices, fetch_listings
from config import FLOAT_RANGES, WEAR_OPTIONS

load_dotenv()
API_KEY = os.getenv("CSFLOAT_API_KEY", "")


def cents_to_usd(cents):
    return f"${cents / 100:.2f}"


def print_results(name, stats, listings, show_top=5):
    sep = "-" * 55
    print(f"\n{sep}\n  {name}\n{sep}")
    if not stats:
        print("  Aucun listing trouve.")
        return
    print(f"  Listings analyses : {stats['count']}")
    print(f"  Prix minimum      : {cents_to_usd(stats['min'])}")
    print(f"  Prix moyen        : {cents_to_usd(int(stats['mean']))}")
    print(f"  Prix median       : {cents_to_usd(int(stats['median']))}")
    print(f"  Prix maximum      : {cents_to_usd(stats['max'])}")
    if stats['stdev']:
        print(f"  Ecart-type        : {cents_to_usd(int(stats['stdev']))}")
    print(f"\n  Top {show_top} moins chers :")
    for i, listing in enumerate(listings[:show_top], 1):
        price  = cents_to_usd(listing["price"])
        fval   = listing.get("item", {}).get("float_value", "N/A")
        fval_s = f"{fval:.4f}" if isinstance(fval, float) else str(fval)
        print(f"  {i}. {price}  (float: {fval_s})")
    print(sep)


def select_wear():
    print("\nQualites disponibles :")
    for i, w in enumerate(WEAR_OPTIONS, 1):
        print(f"  {i}. {w}")
    while True:
        try:
            choice = int(input("Choix (1-5) : ").strip())
            if 1 <= choice <= 5:
                return WEAR_OPTIONS[choice - 1]
        except ValueError:
            pass
        print("  Entrez un chiffre entre 1 et 5.")


def select_category():
    cats = {1: "Normal", 2: "StatTrak", 3: "Souvenir", 0: "Tous"}
    print("\nType d'item :")
    for k, v in cats.items():
        print(f"  {k}. {v}")
    while True:
        try:
            choice = int(input("Choix : ").strip())
            if choice in cats:
                return choice
        except ValueError:
            pass
        print("  Choix invalide.")


def main():
    print("=" * 46)
    print("  CSFloat Price Checker  v1.0  (CLI)")
    print("=" * 46)

    if not API_KEY:
        print("\nAucune cle API configuree.")
        print("Copiez .env.example en .env et renseignez CSFLOAT_API_KEY.\n")
        return

    while True:
        print("\n" + "=" * 46)
        weapon_name = input("Nom de l'arme (ex: AK-47 | Redline) : ").strip()
        if not weapon_name:
            print("  Nom invalide.")
            continue

        wear     = select_wear()
        category = select_category()
        name     = f"{weapon_name} ({wear})"
        min_f, max_f = FLOAT_RANGES[wear]

        print(f"\nRecherche : {name} ...")
        try:
            listings = fetch_listings(API_KEY, name, min_f, max_f, category)
            stats    = analyze_prices(listings)
            print_results(name, stats, listings)

            if input("\n  Exporter en JSON ? (o/N) : ").strip().lower() == "o":
                filename = name.replace(" ", "_").replace("|", "").replace("/", "") + ".json"
                with open(filename, "w", encoding="utf-8") as f:
                    json.dump({"query": name, "stats": stats, "listings": listings},
                              f, indent=2, ensure_ascii=False)
                print(f"  Exporte -> {filename}")

        except requests.HTTPError as e:
            code = e.response.status_code
            if code == 401:
                print("  Cle API invalide ou expiree.")
            elif code == 429:
                print("  Rate limit atteint. Attendez quelques minutes.")
            else:
                print(f"  Erreur HTTP {code}")
        except requests.RequestException as e:
            print(f"  Erreur reseau : {e}")

        if input("\n  Nouvelle recherche ? (O/n) : ").strip().lower() == "n":
            print("\n  A bientot !")
            break


if __name__ == "__main__":
    main()
