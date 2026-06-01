# ── URLs ──────────────────────────────────────────────────────────────────────
API_BASE  = "https://csfloat.com/api/v1"
SKINS_API = "https://raw.githubusercontent.com/ByMykel/CSGO-API/main/public/api/en/skins.json"

# ── Skins / Wear ──────────────────────────────────────────────────────────────
WEAR_OPTIONS = ["Factory New", "Minimal Wear", "Field-Tested", "Well-Worn", "Battle-Scarred"]

FLOAT_RANGES = {
    "Factory New":    (0.00, 0.07),
    "Minimal Wear":   (0.07, 0.15),
    "Field-Tested":   (0.15, 0.38),
    "Well-Worn":      (0.38, 0.45),
    "Battle-Scarred": (0.45, 1.00),
}

CATEGORY_MAP = {"Tous": 0, "Normal": 1, "StatTrak™": 2, "Souvenir": 3}

WEAPON_ORDER = [
    "AK-47", "M4A4", "M4A1-S", "AWP", "Desert Eagle", "USP-S", "Glock-18",
    "P250", "Five-SeveN", "CZ75-Auto", "Tec-9", "MP9", "MP5-SD", "MAC-10",
    "UMP-45", "P90", "PP-Bizon", "Nova", "XM1014", "Sawed-Off", "MAG-7",
    "M249", "Negev", "SG 553", "AUG", "FAMAS", "Galil AR", "SSG 08",
    "G3SG1", "SCAR-20", "MP7", "P2000", "Dual Berettas", "R8 Revolver",
]

WEAPON_CATEGORIES = {
    "Fusils": [
        "AK-47", "AUG", "FAMAS", "Galil AR", "M4A1-S", "M4A4", "SG 553",
        "AWP", "G3SG1", "SCAR-20", "SSG 08",
    ],
    "Pistolets": [
        "Desert Eagle", "Dual Berettas", "Five-SeveN", "Glock-18",
        "P2000", "P250", "R8 Revolver", "Tec-9", "USP-S", "CZ75-Auto",
    ],
    "Pistolets-Mitrailleurs": [
        "MAC-10", "MP5-SD", "MP7", "MP9", "P90", "PP-Bizon", "UMP-45",
    ],
    "Lourd": [
        "MAG-7", "Nova", "Sawed-Off", "XM1014", "M249", "Negev",
    ],
    # Couteaux et Gants sont détectés dynamiquement via KNIFE_KEYWORDS / GLOVES_KEYWORDS
}

SECTION_ORDER = [
    "Fusils", "Pistolets", "Pistolets-Mitrailleurs",
    "Lourd", "Couteaux", "Gants",
]

KNIFE_KEYWORDS = {
    "Bayonet", "Karambit", "Butterfly", "Bowie", "Falchion",
    "Flip", "Gut", "Huntsman", "M9", "Navaja", "Shadow", "Stiletto",
    "Talon", "Ursus", "Classic", "Nomad", "Paracord", "Skeleton",
    "Survival",
}
GLOVES_KEYWORDS = {"Gloves", "Wraps"}

EXCLUDED_CATEGORIES = {
    "Charm", "Sticker", "Graffiti", "Music Kit",
    "Patch", "Container", "Key", "Pass",
}

EXCLUDED_WEAPONS = ()

EUR_RATE_DEFAULT = 0.92

# ── Palette ───────────────────────────────────────────────────────────────────
BG      = "#0d0f14"
BG2     = "#13161e"
BG3     = "#1a1e29"
CARD    = "#1e2230"
CARD_H  = "#252a3a"
ACCENT  = "#e8a92a"
ACCENT2 = "#3d8ef0"
GREEN   = "#2ecc71"
RED     = "#e74c3c"
TEXT    = "#e8eaf0"
MUTED   = "#6b7280"
BORDER  = "#2a2f3d"

# ── Typographie ───────────────────────────────────────────────────────────────
FONT_TITLE = ("Segoe UI", 18, "bold")
FONT_HEAD  = ("Segoe UI", 11, "bold")
FONT_BODY  = ("Segoe UI", 10)
FONT_SMALL = ("Segoe UI", 9)
FONT_STAT  = ("Segoe UI", 20, "bold")

# ── Icônes catégories ─────────────────────────────────────────────────────────
SECTION_ICONS: dict[str, str] = {
    "Fusils":                  "🎯",
    "Pistolets":               "🔫",
    "Pistolets-Mitrailleurs":  "💨",
    "Lourd":                   "💥",
    "Couteaux":                "🗡",
    "Gants":                   "🧤",
}
