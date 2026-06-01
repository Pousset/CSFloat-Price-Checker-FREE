"""
CSFloat Price Checker - Interface Graphique v2
"""
import os
import sys
import threading
import tkinter as tk

from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api import fetch_eur_rate, fetch_skins_db
from config import (
    ACCENT, ACCENT2, BG, BG2, BG3, BORDER, CARD,
    EUR_RATE_DEFAULT, EXCLUDED_CATEGORIES,
    FONT_HEAD, FONT_SMALL, FONT_TITLE, GREEN, MUTED, RED, TEXT,
    GLOVES_KEYWORDS, KNIFE_KEYWORDS, SECTION_ORDER, WEAPON_CATEGORIES,
)
from views.weapons_view   import WeaponsViewMixin
from views.skins_view     import SkinsViewMixin
from views.price_view     import PriceViewMixin
from views.inventory_view import InventoryViewMixin

load_dotenv()


class CSFloatApp(WeaponsViewMixin, SkinsViewMixin, PriceViewMixin,
                 InventoryViewMixin, tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("CSFloat Price Checker")
        self.geometry("1100x720")
        self.minsize(900, 600)
        self.configure(bg=BG)

        self.api_key      = tk.StringVar(value=os.getenv("CSFLOAT_API_KEY", ""))
        self.currency_var = tk.StringVar(value="EUR")
        self.eur_rate     = EUR_RATE_DEFAULT
        self.skins_db: list[dict]              = []
        self.weapons_map: dict[str, list]      = {}
        self.category_weapons_map: dict        = {s: [] for s in SECTION_ORDER}
        self.sel_section  = ""
        self.sel_weapon   = ""
        self.sel_skin: dict               = {}
        self.listings_cache: list[dict]   = []
        self.stats_cache: dict            = {}
        self._last_price_name             = ""

        self._build_ui()
        self._load_skins_db()
        threading.Thread(target=self._bg_eur_rate, daemon=True).start()

    # ── Construction UI ───────────────────────────────────────────────────────

    def _build_ui(self):
        self._build_header()
        self._build_api_bar()
        tk.Frame(self, bg=BORDER, height=1).pack(fill="x")
        self.breadcrumb_bar = tk.Frame(self, bg=BG2, padx=16, pady=6)
        self.breadcrumb_bar.pack(fill="x")
        tk.Frame(self, bg=BORDER, height=1).pack(fill="x")
        self._update_breadcrumb()
        self.main_area = tk.Frame(self, bg=BG)
        self.main_area.pack(fill="both", expand=True)

    def _build_header(self):
        hdr = tk.Frame(self, bg=BG2)
        hdr.pack(fill="x")
        tk.Frame(hdr, bg=ACCENT, width=4).pack(side="left", fill="y")
        inner = tk.Frame(hdr, bg=BG2, padx=16, pady=12)
        inner.pack(side="left", fill="both", expand=True)
        tk.Label(inner, text="CSFloat PRICE CHECKER",
                 font=FONT_TITLE, bg=BG2, fg=ACCENT).pack(side="left")
        tk.Label(inner, text="v2.0", font=FONT_SMALL,
                 bg=BG2, fg=MUTED).pack(side="left", padx=8, pady=(6, 0))
        self.status_dot = tk.Label(inner, text="o", font=("Consolas", 13),
                                   bg=BG2, fg=MUTED)
        self.status_dot.pack(side="right", padx=(0, 4))
        self.status_lbl = tk.Label(inner, text="Cle non validee",
                                   font=FONT_SMALL, bg=BG2, fg=MUTED)
        self.status_lbl.pack(side="right")

    def _build_api_bar(self):
        bar = tk.Frame(self, bg=BG3, padx=16, pady=8)
        bar.pack(fill="x")
        tk.Label(bar, text="CLE API :", font=FONT_SMALL, bg=BG3, fg=MUTED).pack(side="left")
        self._key_visible = False
        self.api_entry = tk.Entry(bar, textvariable=self.api_key,
                                  bg=BG, fg=TEXT, insertbackground=ACCENT,
                                  font=FONT_SMALL, bd=0, show="*", width=45,
                                  highlightthickness=1, highlightbackground=BORDER)
        self.api_entry.pack(side="left", padx=8, ipady=4)
        eye = tk.Label(bar, text="oeil", bg=BG3, fg=MUTED, cursor="hand2",
                       font=("Consolas", 11))
        eye.pack(side="left")
        eye.bind("<Button-1>", self._toggle_key)
        val = tk.Label(bar, text="  Valider  ", bg=ACCENT, fg=BG,
                       font=FONT_SMALL, cursor="hand2", padx=6, pady=4)
        val.pack(side="left", padx=8)
        val.bind("<Button-1>", lambda e: self._validate_key())
        tk.Frame(bar, bg=BORDER, width=1).pack(side="left", fill="y", padx=8)
        tk.Label(bar, text="DEVISE :", font=FONT_SMALL, bg=BG3, fg=MUTED).pack(side="left")
        self._curr_btn = tk.Label(bar, text="EUR", bg=CARD, fg=ACCENT,
                                   font=("Consolas", 9, "bold"), cursor="hand2",
                                   padx=10, pady=4,
                                   highlightbackground=ACCENT, highlightthickness=1)
        self._curr_btn.pack(side="left", padx=6)
        self._curr_btn.bind("<Button-1>", lambda e: self._toggle_currency())
        tk.Frame(bar, bg=BORDER, width=1).pack(side="left", fill="y", padx=8)
        inv = tk.Label(bar, text="  Inventaire  ", bg=ACCENT2, fg=BG,
                       font=FONT_SMALL, cursor="hand2", padx=6, pady=4)
        inv.pack(side="left", padx=4)
        inv.bind("<Button-1>", lambda e: self._show_inventory_screen())

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _swap(self, widget):
        for w in self.main_area.winfo_children():
            if w is not widget:
                w.destroy()
        widget.pack(fill="both", expand=True)

    def _set_status(self, text, color):
        self.status_lbl.config(text=text, fg=color)
        self.status_dot.config(fg=color)

    def format_price(self, cents):
        if self.currency_var.get() == "EUR":
            return f"{cents / 100 * self.eur_rate:.2f} EUR"
        return f"${cents / 100:.2f}"

    def _update_breadcrumb(self, section="", weapon="", skin_name=""):
        for w in self.breadcrumb_bar.winfo_children():
            w.destroy()

        def crumb(text, cmd=None, active=False):
            fg = ACCENT if active else (ACCENT2 if cmd else MUTED)
            lbl = tk.Label(self.breadcrumb_bar, text=text, font=FONT_SMALL,
                           bg=BG2, fg=fg, cursor="hand2" if cmd else "arrow")
            lbl.pack(side="left")
            if cmd:
                lbl.bind("<Button-1>", lambda e: cmd())

        crumb("Skins", self._show_weapons if (section or weapon) else None,
              active=not section and not weapon)
        if section:
            crumb(" > ")
            crumb(section, self._show_weapons if weapon else None, active=not weapon)
        if weapon:
            crumb(" > ")
            crumb(weapon, self._show_skins if skin_name else None, active=not skin_name)
        if skin_name:
            crumb(" > ")
            crumb(skin_name, active=True)

    # ── Cle API ───────────────────────────────────────────────────────────────

    def _toggle_key(self, _=None):
        self._key_visible = not self._key_visible
        self.api_entry.config(show="" if self._key_visible else "*")

    def _validate_key(self):
        key = self.api_key.get().strip()
        if not key:
            self._set_status("Cle vide", RED)
            return
        self._set_status("Verification...", ACCENT)
        threading.Thread(target=self._validate_key_thread, args=(key,), daemon=True).start()

    def _validate_key_thread(self, key):
        try:
            r = requests.get("https://csfloat.com/api/v1/listings",
                             headers={"Authorization": key},
                             params={"limit": 1}, timeout=15,
                             verify=True)
            if r.status_code == 401:
                self.after(0, self._set_status, "Cle invalide (401)", RED)
            elif r.status_code == 403:
                # 403 sans market_hash_name = cle acceptee mais droits limites
                os.environ["CSFLOAT_API_KEY"] = key
                self.after(0, self._set_status, "Cle valide", GREEN)
            elif r.status_code in (200, 400):
                os.environ["CSFLOAT_API_KEY"] = key
                self.after(0, self._set_status, "Cle valide", GREEN)
            else:
                self.after(0, self._set_status, f"Erreur {r.status_code}", RED)
        except requests.exceptions.SSLError:
            self.after(0, self._set_status, "Erreur SSL", RED)
        except requests.exceptions.ConnectionError:
            self.after(0, self._set_status, "Connexion impossible", RED)
        except requests.exceptions.Timeout:
            self.after(0, self._set_status, "Timeout (15s)", RED)
        except Exception as exc:
            self.after(0, self._set_status, f"Erreur: {exc}", RED)

    # ── Devise ────────────────────────────────────────────────────────────────

    def _bg_eur_rate(self):
        self.eur_rate = fetch_eur_rate()

    def _toggle_currency(self):
        if self.currency_var.get() == "EUR":
            self.currency_var.set("USD")
            self._curr_btn.config(text="USD", fg=ACCENT2, highlightbackground=ACCENT2)
        else:
            self.currency_var.set("EUR")
            self._curr_btn.config(text="EUR", fg=ACCENT, highlightbackground=ACCENT)
        if self.listings_cache and self._last_price_name:
            self._show_price_results(self._last_price_name,
                                     self.listings_cache, self.stats_cache)

    # ── Chargement DB skins ───────────────────────────────────────────────────

    def _load_skins_db(self):
        frame = tk.Frame(self.main_area, bg=BG)
        frame.pack(fill="both", expand=True)
        tk.Label(frame, text="Chargement des skins...",
                 font=("Consolas", 14), bg=BG, fg=MUTED).place(relx=.5, rely=.5, anchor="center")
        threading.Thread(target=self._fetch_db_thread, daemon=True).start()

    def _fetch_db_thread(self):
        try:
            self.after(0, self._on_db_loaded, fetch_skins_db())
        except Exception as e:
            self.after(0, self._on_db_error, str(e))

    def _on_db_loaded(self, data):
        grouped: dict[str, list] = {}

        for skin in data:
            name  = skin.get("name", "")
            parts = name.split(" | ")
            if len(parts) < 2:
                continue
            weapon = parts[0].strip()
            # Filtrer stickers, graffiti, etc.
            cat = skin.get("category", {})
            cat_name = cat.get("name", "") if isinstance(cat, dict) else ""
            if cat_name in EXCLUDED_CATEGORIES:
                continue
            grouped.setdefault(weapon, []).append(skin)

        # Construire category_weapons_map
        cat_map: dict[str, list[str]] = {s: [] for s in SECTION_ORDER}
        seen: set[str] = set()

        # Armes fixes dans l'ordre défini
        for section, weapon_list in WEAPON_CATEGORIES.items():
            for w in weapon_list:
                if w in grouped:
                    cat_map[section].append(w)
                    seen.add(w)

        # Couteaux et Gants détectés dynamiquement
        # Les gants ont aussi ★ — on teste GLOVES_KEYWORDS en priorité
        for weapon in sorted(grouped.keys()):
            if weapon in seen:
                continue
            if any(kw in weapon for kw in GLOVES_KEYWORDS):
                cat_map["Gants"].append(weapon)
                seen.add(weapon)
            elif "★" in weapon or any(kw in weapon for kw in KNIFE_KEYWORDS):
                cat_map["Couteaux"].append(weapon)
                seen.add(weapon)

        self.skins_db             = data
        self.weapons_map          = grouped
        self.category_weapons_map = cat_map
        self._show_weapons()

    def _on_db_error(self, msg):
        for w in self.main_area.winfo_children():
            w.destroy()
        tk.Label(self.main_area, text=f"Erreur chargement skins :\n{msg}",
                 font=FONT_HEAD, bg=BG, fg=RED).place(relx=.5, rely=.5, anchor="center")


if __name__ == "__main__":
    CSFloatApp().mainloop()
