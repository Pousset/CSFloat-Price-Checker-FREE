"""
CSFloat Price Checker - Interface Graphique v2
"""
import os
import sys
import time
import threading
import tkinter as tk

import requests
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
        tk.Frame(self, bg=BORDER, height=1).pack(fill="x")
        self.breadcrumb_bar = tk.Frame(self, bg=BG2, padx=16, pady=6)
        self.breadcrumb_bar.pack(fill="x")
        tk.Frame(self, bg=BORDER, height=1).pack(fill="x")
        self.main_area = tk.Frame(self, bg=BG)
        self.main_area.pack(fill="both", expand=True)
        self._splash_start = time.monotonic()
        self._show_splash()

    def _build_header(self):
        hdr = tk.Frame(self, bg=BG2)
        hdr.pack(fill="x")
        tk.Frame(hdr, bg=ACCENT, width=4).pack(side="left", fill="y")
        inner = tk.Frame(hdr, bg=BG2, padx=16, pady=12)
        inner.pack(side="left", fill="both", expand=True)

        # Logo + titre (cliquable → retour accueil)
        dot = tk.Label(inner, text="●", font=("Segoe UI", 14, "bold"),
                 bg=BG2, fg=ACCENT, cursor="hand2")
        dot.pack(side="left")
        lbl_cs = tk.Label(inner, text="  CSFloat", font=("Segoe UI", 15, "bold"),
                 bg=BG2, fg=ACCENT, cursor="hand2")
        lbl_cs.pack(side="left")
        lbl_pc = tk.Label(inner, text=" Price Checker", font=("Segoe UI", 15),
                 bg=BG2, fg=TEXT, cursor="hand2")
        lbl_pc.pack(side="left")
        for w in (dot, lbl_cs, lbl_pc):
            w.bind("<Button-1>", lambda e: self._show_weapons())
            w.bind("<Enter>",    lambda e: (lbl_cs.config(fg=TEXT), lbl_pc.config(fg=MUTED)))
            w.bind("<Leave>",    lambda e: (lbl_cs.config(fg=ACCENT), lbl_pc.config(fg=TEXT)))

        # Droite : settings ⚙
        settings_lbl = tk.Label(inner, text="⚙", font=("Segoe UI", 15),
                                 bg=BG2, fg=MUTED, cursor="hand2")
        settings_lbl.pack(side="right", padx=(8, 0))
        settings_lbl.bind("<Button-1>", lambda e: self._open_settings())
        settings_lbl.bind("<Enter>",    lambda e: settings_lbl.config(fg=TEXT))
        settings_lbl.bind("<Leave>",    lambda e: settings_lbl.config(fg=MUTED))

        # Devise toggle
        self._curr_btn = tk.Label(inner, text="EUR", bg=BG3, fg=ACCENT,
                                   font=("Segoe UI", 9, "bold"), cursor="hand2",
                                   padx=10, pady=3,
                                   highlightbackground=ACCENT, highlightthickness=1)
        self._curr_btn.pack(side="right", padx=8)
        self._curr_btn.bind("<Button-1>", lambda e: self._toggle_currency())

        # Status
        self.status_dot = tk.Label(inner, text="●", font=("Segoe UI", 10),
                                    bg=BG2, fg=MUTED)
        self.status_dot.pack(side="right", padx=(0, 4))
        self.status_lbl = tk.Label(inner, text="Clé non configurée",
                                    font=FONT_SMALL, bg=BG2, fg=MUTED)
        self.status_lbl.pack(side="right")

    # ── Splash screen animé ───────────────────────────────────────────────────

    def _show_splash(self):
        self._splash_frame = tk.Frame(self.main_area, bg=BG)
        self._splash_frame.pack(fill="both", expand=True)

        center = tk.Frame(self._splash_frame, bg=BG)
        center.place(relx=0.5, rely=0.45, anchor="center")

        # Ligne de lettres — chacune dans son propre Label
        letters_frame = tk.Frame(center, bg=BG)
        letters_frame.pack()

        full_text  = "CSFloat"
        self._splash_letter_lbls = []
        for ch in full_text:
            lbl = tk.Label(
                letters_frame, text=ch,
                font=("Segoe UI", 72, "bold"),
                bg=BG, fg=BG,           # invisible au départ
            )
            lbl.pack(side="left")
            self._splash_letter_lbls.append(lbl)

        tk.Label(center, text="Price Checker",
                 font=("Segoe UI", 14), bg=BG, fg=BG).pack(pady=(4, 0))
        self._splash_sub = center.winfo_children()[-1]

        tk.Label(center, text="v2.0", font=("Segoe UI", 9),
                 bg=BG, fg=BG).pack(pady=(2, 0))
        self._splash_ver = center.winfo_children()[-1]

        tk.Label(center, text="by Mathis PIETTE",
                 font=("Segoe UI", 9, "italic"), bg=BG, fg=BG).pack(pady=(6, 0))
        self._splash_author = center.winfo_children()[-1]

        tk.Label(center, text="Chargement...",
                 font=("Segoe UI", 9), bg=BG, fg=BG).pack(pady=(20, 0))
        self._splash_status_lbl = center.winfo_children()[-1]

        self._splash_letter_idx = 0
        self._splash_phase      = "letters"   # letters → subtitle → done
        self._animate_splash()

    def _animate_splash(self):
        try:
            if not self._splash_frame.winfo_exists():
                return
        except Exception:
            return

        if self._splash_phase == "letters":
            idx = self._splash_letter_idx
            if idx < len(self._splash_letter_lbls):
                # Couleur : les 2 premières (CS) en ACCENT, reste en TEXT
                color = ACCENT if idx < 2 else TEXT
                self._splash_letter_lbls[idx].config(fg=color)
                self._splash_letter_idx += 1
                self.after(80, self._animate_splash)
            else:
                self._splash_phase = "subtitle"
                self.after(120, self._animate_splash)

        elif self._splash_phase == "subtitle":
            self._splash_sub.config(fg=MUTED)
            self._splash_ver.config(fg=MUTED)
            self._splash_author.config(fg=MUTED)
            self._splash_phase = "status"
            self.after(200, self._animate_splash)

        elif self._splash_phase == "status":
            self._splash_status_lbl.config(fg=MUTED)
            # Blink du status pour indiquer le chargement
            self._splash_blink = True
            self._blink_status()

    def _blink_status(self):
        try:
            if not self._splash_frame.winfo_exists():
                return
        except Exception:
            return
        fg = MUTED if self._splash_blink else BG3
        self._splash_status_lbl.config(fg=fg)
        self._splash_blink = not self._splash_blink
        self.after(600, self._blink_status)

    # ── Dialog paramètres (clé API) ───────────────────────────────────────────

    def _open_settings(self):
        dlg = tk.Toplevel(self)
        dlg.title("Paramètres")
        dlg.geometry("440x230")
        dlg.configure(bg=BG)
        dlg.resizable(False, False)
        dlg.transient(self)
        dlg.grab_set()

        tk.Label(dlg, text="Paramètres", font=("Segoe UI", 14, "bold"),
                 bg=BG, fg=TEXT).pack(pady=(20, 14), padx=24, anchor="w")

        key_frame = tk.Frame(dlg, bg=BG3, padx=16, pady=12)
        key_frame.pack(fill="x", padx=24, pady=(0, 14))
        tk.Label(key_frame, text="CLÉ API CSFLOAT", font=("Segoe UI", 8, "bold"),
                 bg=BG3, fg=MUTED).pack(anchor="w", pady=(0, 6))

        row = tk.Frame(key_frame, bg=BG3)
        row.pack(fill="x")

        self._key_visible = getattr(self, "_key_visible", False)
        entry = tk.Entry(row, textvariable=self.api_key, bg=BG, fg=TEXT,
                         insertbackground=ACCENT, font=("Segoe UI", 9),
                         bd=0, show="*", width=38,
                         highlightthickness=1, highlightbackground=BORDER)
        entry.pack(side="left", ipady=5)
        if self._key_visible:
            entry.config(show="")

        eye = tk.Label(row, text=" 👁 ", bg=BG3, fg=MUTED, cursor="hand2",
                       font=("Segoe UI", 11))
        eye.pack(side="left", padx=4)

        def _toggle_vis():
            self._key_visible = not self._key_visible
            entry.config(show="" if self._key_visible else "*")
        eye.bind("<Button-1>", lambda e: _toggle_vis())

        btn_row = tk.Frame(dlg, bg=BG)
        btn_row.pack(fill="x", padx=24)

        val = tk.Label(btn_row, text="  Valider la clé  ", bg=ACCENT, fg=BG,
                       font=("Segoe UI", 10, "bold"), cursor="hand2",
                       padx=8, pady=6)
        val.pack(side="left")
        val.bind("<Button-1>", lambda e: (self._validate_key(), dlg.destroy()))

        close = tk.Label(btn_row, text="  Fermer  ", bg=BG3, fg=TEXT,
                         font=("Segoe UI", 10), cursor="hand2", padx=8, pady=6)
        close.pack(side="right")
        close.bind("<Button-1>", lambda e: dlg.destroy())

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

    def _update_breadcrumb(self, section: str = "", weapon: str = "", skin_name: str = ""):
        """Navigation retour contextuelle dans la barre de breadcrumb."""
        for w in self.breadcrumb_bar.winfo_children():
            w.destroy()

        if not section and not weapon and not skin_name:
            return  # home – barre vide

        # Destination du bouton retour
        if skin_name:
            back_text = f"←  {weapon}"
            back_cmd  = self._show_skins
            current   = skin_name
        elif weapon:
            back_text = f"←  {section}"
            back_cmd  = lambda: self._select_section(section)  # noqa: E731
            current   = weapon
        else:
            back_text = "←  Catégories"
            back_cmd  = self._show_weapons
            current   = section

        back = tk.Label(self.breadcrumb_bar, text=back_text,
                        font=FONT_SMALL, bg=BG2, fg=MUTED, cursor="hand2")
        back.pack(side="left")
        back.bind("<Button-1>", lambda e: back_cmd())
        back.bind("<Enter>",    lambda e: back.config(fg=TEXT))
        back.bind("<Leave>",    lambda e: back.config(fg=MUTED))

        tk.Label(self.breadcrumb_bar, text=f"  ›  {current}",
                 font=FONT_SMALL, bg=BG2, fg=ACCENT).pack(side="left")

    # ── Clé API ───────────────────────────────────────────────────────────────

    def _validate_key(self):
        key = self.api_key.get().strip()
        if not key:
            self._set_status("Clé vide", RED)
            return
        self._set_status("Vérification...", ACCENT)
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
                os.environ["CSFLOAT_API_KEY"] = key
                self._save_env_key(key)
                self.after(0, self._set_status, "Cle valide ✓  (.env mis à jour)", GREEN)
            elif r.status_code in (200, 400):
                os.environ["CSFLOAT_API_KEY"] = key
                self._save_env_key(key)
                self.after(0, self._set_status, "Cle valide ✓  (.env mis à jour)", GREEN)
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

    def _save_env_key(self, key: str):
        """Crée ou met à jour CSFLOAT_API_KEY dans le fichier .env à côté de csfloat_gui.py."""
        env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
        lines: list[str] = []
        found = False
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            for i, line in enumerate(lines):
                if line.startswith("CSFLOAT_API_KEY"):
                    lines[i] = f"CSFLOAT_API_KEY={key}\n"
                    found = True
                    break
        if not found:
            lines.append(f"CSFLOAT_API_KEY={key}\n")
        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(lines)

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
        # Durée minimum du splash : 2.5 s
        elapsed  = time.monotonic() - self._splash_start
        delay_ms = max(0, int((2.5 - elapsed) * 1000))
        self.after(delay_ms, self._show_weapons)

    def _on_db_error(self, msg):
        for w in self.main_area.winfo_children():
            w.destroy()
        tk.Label(self.main_area, text=f"Erreur chargement skins :\n{msg}",
                 font=FONT_HEAD, bg=BG, fg=RED).place(relx=.5, rely=.5, anchor="center")


if __name__ == "__main__":
    CSFloatApp().mainloop()
