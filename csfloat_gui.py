"""
CSFloat Price Checker - Interface Graphique v2
"""
import json
import os
import re
import sys
import threading
import webbrowser
from concurrent.futures import ThreadPoolExecutor, as_completed
from tkinter import filedialog, messagebox, ttk
import tkinter as tk

from dotenv import load_dotenv
import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api import (
    analyze_prices, fetch_eur_rate, fetch_listings,
    fetch_skins_db, fetch_steam_inventory,
)
from config import (
    ACCENT, ACCENT2, BG, BG2, BG3, BORDER, CARD, CARD_H,
    CATEGORY_MAP, EUR_RATE_DEFAULT, EXCLUDED_CATEGORIES,
    EXCLUDED_WEAPONS, FLOAT_RANGES, FONT_BODY, FONT_HEAD,
    FONT_SMALL, FONT_STAT, FONT_TITLE, GREEN, MUTED,
    RED, TEXT, WEAPON_ORDER,
)
from widgets import ScrollFrame, SkinCard, load_image

load_dotenv()


class CSFloatApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("CSFloat Price Checker")
        self.geometry("1100x720")
        self.minsize(900, 600)
        self.configure(bg=BG)
        self.api_key      = tk.StringVar(value=os.getenv("CSFLOAT_API_KEY", ""))
        self.currency_var = tk.StringVar(value="EUR")
        self.eur_rate     = EUR_RATE_DEFAULT
        self.skins_db: list[dict]         = []
        self.weapons_map: dict[str, list] = {}
        self.sel_weapon   = ""
        self.sel_skin: dict = {}
        self.listings_cache: list[dict] = []
        self.stats_cache: dict          = {}
        self._last_price_name           = ""
        self._build_ui()
        self._load_skins_db()
        threading.Thread(target=self._bg_eur_rate, daemon=True).start()

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _clear(widget):
        for w in widget.winfo_children(): w.destroy()

    def _centered_msg(self, parent, icon, msg, color=None):
        self._clear(parent)
        f = tk.Frame(parent, bg=BG)
        f.place(relx=.5, rely=.5, anchor="center")
        tk.Label(f, text=icon, font=("Consolas", 32), bg=BG, fg=color or BORDER).pack()
        tk.Label(f, text=msg, font=FONT_BODY, bg=BG, fg=color or MUTED,
                 justify="center", wraplength=300).pack(pady=8)

    def _export_btn(self, parent, cmd, **pack_kw):
        btn = tk.Label(parent, text="Exporter JSON", font=FONT_SMALL,
                       bg=BG3, fg=TEXT, padx=10, pady=5, cursor="hand2")
        btn.pack(**pack_kw)
        btn.bind("<Button-1>", lambda e: cmd())
        btn.bind("<Enter>", lambda e: btn.config(bg=BORDER))
        btn.bind("<Leave>", lambda e: btn.config(bg=BG3))

    def _show_grid_screen(self, title, search_attr, grid_attr, refresh):
        sf = ScrollFrame(self.main_area)
        self._swap(sf)
        tk.Label(sf.inner, text=title, font=FONT_HEAD, bg=BG, fg=MUTED,
                 padx=20, pady=14).pack(anchor="w")
        bar = tk.Frame(sf.inner, bg=BG, padx=20)
        bar.pack(fill="x", pady=(0, 10))
        sv = tk.StringVar()
        setattr(self, search_attr, sv)
        tk.Entry(bar, textvariable=sv, bg=BG3, fg=TEXT, insertbackground=ACCENT,
                 font=FONT_BODY, bd=0, width=30,
                 highlightthickness=1, highlightbackground=BORDER
                 ).pack(side="left", ipady=5, padx=(0, 8))
        grid = tk.Frame(sf.inner, bg=BG, padx=20)
        grid.pack(fill="both")
        setattr(self, grid_attr, grid)
        sv.trace_add("write", lambda *_: refresh())
        refresh()

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
        tk.Label(inner, text="CSFloat PRICE CHECKER", font=FONT_TITLE,
                 bg=BG2, fg=ACCENT).pack(side="left")
        tk.Label(inner, text="v2.0", font=FONT_SMALL,
                 bg=BG2, fg=MUTED).pack(side="left", padx=8, pady=(6, 0))
        self.status_dot = tk.Label(inner, text="o", font=("Consolas", 13), bg=BG2, fg=MUTED)
        self.status_dot.pack(side="right", padx=(0, 4))
        self.status_lbl = tk.Label(inner, text="Cle non validee", font=FONT_SMALL, bg=BG2, fg=MUTED)
        self.status_lbl.pack(side="right")

    def _build_api_bar(self):
        bar = tk.Frame(self, bg=BG3, padx=16, pady=8)
        bar.pack(fill="x")
        tk.Label(bar, text="CLE API :", font=FONT_SMALL, bg=BG3, fg=MUTED).pack(side="left")
        self._key_visible = False
        self.api_entry = tk.Entry(bar, textvariable=self.api_key, bg=BG, fg=TEXT,
                                  insertbackground=ACCENT, font=FONT_SMALL, bd=0,
                                  show="*", width=45,
                                  highlightthickness=1, highlightbackground=BORDER)
        self.api_entry.pack(side="left", padx=8, ipady=4)
        eye = tk.Label(bar, text="oeil", bg=BG3, fg=MUTED, cursor="hand2", font=("Consolas", 11))
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

    def _swap(self, widget):
        for w in self.main_area.winfo_children():
            if w is not widget: w.destroy()
        widget.pack(fill="both", expand=True)

    def _set_status(self, text, color):
        self.status_lbl.config(text=text, fg=color)
        self.status_dot.config(fg=color)

    def format_price(self, cents):
        if self.currency_var.get() == "EUR":
            return f"{cents / 100 * self.eur_rate:.2f} EUR"
        return f"${cents / 100:.2f}"

    def _update_breadcrumb(self, weapon="", skin_name=""):
        self._clear(self.breadcrumb_bar)
        def crumb(text, cmd=None, active=False):
            fg = ACCENT if active else (ACCENT2 if cmd else MUTED)
            lbl = tk.Label(self.breadcrumb_bar, text=text, font=FONT_SMALL,
                           bg=BG2, fg=fg, cursor="hand2" if cmd else "arrow")
            lbl.pack(side="left")
            if cmd: lbl.bind("<Button-1>", lambda e: cmd())
        crumb("Armes", self._show_weapons if weapon else None, active=not weapon)
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
            self._set_status("Cle vide", RED); return
        self._set_status("Verification...", ACCENT)
        threading.Thread(target=self._validate_key_thread, args=(key,), daemon=True).start()

    def _validate_key_thread(self, key):
        try:
            r = requests.get("https://csfloat.com/api/v1/listings",
                             headers={"Authorization": key}, params={"limit": 1}, timeout=10)
            if r.status_code == 401:
                self.after(0, self._set_status, "Cle invalide", RED)
            elif r.status_code in (200, 400):
                os.environ["CSFLOAT_API_KEY"] = key
                self.after(0, self._set_status, "Cle valide", GREEN)
            else:
                self.after(0, self._set_status, f"Erreur {r.status_code}", RED)
        except Exception:
            self.after(0, self._set_status, "Reseau KO", RED)

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
            self._show_price_results(self._last_price_name, self.listings_cache, self.stats_cache)

    # ── DB skins ──────────────────────────────────────────────────────────────

    def _load_skins_db(self):
        frame = tk.Frame(self.main_area, bg=BG)
        frame.pack(fill="both", expand=True)
        tk.Label(frame, text="Chargement des skins...", font=("Consolas", 14),
                 bg=BG, fg=MUTED).place(relx=.5, rely=.5, anchor="center")
        threading.Thread(target=self._fetch_db_thread, daemon=True).start()

    def _fetch_db_thread(self):
        try:
            self.after(0, self._on_db_loaded, fetch_skins_db())
        except Exception as e:
            self.after(0, self._centered_msg, self.main_area,
                       "X", f"Erreur chargement skins:\n{e}", RED)

    def _on_db_loaded(self, data):
        grouped = {}
        for skin in data:
            name  = skin.get("name", "")
            parts = name.split(" | ")
            if len(parts) < 2: continue
            weapon = parts[0].strip()
            cat = skin.get("category", {})
            if isinstance(cat, dict) and cat.get("name", "") in EXCLUDED_CATEGORIES: continue
            if any(x in weapon for x in EXCLUDED_WEAPONS): continue
            grouped.setdefault(weapon, []).append(skin)
        self.skins_db = data
        self.weapons_map = grouped
        self._show_weapons()

    # ── Ecran 1 : Grille armes ────────────────────────────────────────────────

    def _show_weapons(self):
        self.sel_weapon = ""
        self._update_breadcrumb()
        self._show_grid_screen("Choisis une arme", "_weapon_search", "_weapons_grid",
                               self._refresh_weapons_grid)

    def _refresh_weapons_grid(self):
        self._clear(self._weapons_grid)
        q = self._weapon_search.get().lower()
        known  = [w for w in WEAPON_ORDER if w in self.weapons_map]
        others = sorted(k for k in self.weapons_map if k not in WEAPON_ORDER)
        weapons = [w for w in known + others if q in w.lower()] if q else known + others
        for i, weapon in enumerate(weapons):
            skins = self.weapons_map[weapon]
            row, col = divmod(i, 7)
            SkinCard(self._weapons_grid, name=weapon,
                     img_url=skins[0].get("image", "") if skins else "",
                     callback=lambda w=weapon: self._select_weapon(w),
                     card_w=130, card_h=115, img_size=(100, 75)
                     ).grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
        if not weapons:
            tk.Label(self._weapons_grid, text="Aucune arme trouvee",
                     font=FONT_BODY, bg=BG, fg=MUTED).pack(pady=20)

    def _select_weapon(self, weapon):
        self.sel_weapon = weapon
        self._show_skins()

    # ── Ecran 2 : Grille skins ────────────────────────────────────────────────

    def _show_skins(self):
        self._update_breadcrumb(weapon=self.sel_weapon)
        self._all_skins = self.weapons_map.get(self.sel_weapon, [])
        self._show_grid_screen(f"Skins - {self.sel_weapon}", "_skin_search", "_skins_grid",
                               self._refresh_skins_grid)

    def _refresh_skins_grid(self):
        self._clear(self._skins_grid)
        q = self._skin_search.get().lower()
        skins = [s for s in self._all_skins
                 if q in s.get("name", "").lower()] if q else self._all_skins
        for i, skin in enumerate(skins):
            parts = skin.get("name", "").split(" | ")
            skin_name = parts[1] if len(parts) > 1 else skin.get("name", "")
            row, col = divmod(i, 6)
            SkinCard(self._skins_grid, name=skin_name, img_url=skin.get("image", ""),
                     callback=lambda s=skin: self._select_skin(s),
                     card_w=148, card_h=120, img_size=(115, 80)
                     ).grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
        if not skins:
            tk.Label(self._skins_grid, text="Aucun skin trouve",
                     font=FONT_BODY, bg=BG, fg=MUTED).pack(pady=20)

    def _select_skin(self, skin):
        self.sel_skin = skin
        self._show_quality_picker()

    # ── Ecran 3 : Qualite + Prix ──────────────────────────────────────────────

    def _show_quality_picker(self):
        skin = self.sel_skin
        full_name = skin.get("name", "")
        parts = full_name.split(" | ")
        skin_name = parts[1] if len(parts) > 1 else full_name
        self._update_breadcrumb(weapon=self.sel_weapon, skin_name=skin_name)
        min_f, max_f = skin.get("min_float", 0.0), skin.get("max_float", 1.0)
        available_wears = [w for w, (lo, hi) in FLOAT_RANGES.items() if lo < max_f and hi > min_f]

        frame = tk.Frame(self.main_area, bg=BG)
        self._swap(frame)
        left = tk.Frame(frame, bg=BG2, width=280)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)
        tk.Frame(frame, bg=BORDER, width=1).pack(side="left", fill="y")
        info = tk.Frame(left, bg=BG2, padx=20, pady=20)
        info.pack(fill="both", expand=True)

        self._skin_big_lbl = tk.Label(info, bg=BG2, text="...", fg=MUTED, font=("Consolas", 24))
        self._skin_big_lbl.pack(pady=(10, 8))
        def _load_big():
            img = load_image(skin.get("image", ""), (220, 160))
            if img:
                self._skin_big_lbl.after(0, lambda i=img: [
                    self._skin_big_lbl.config(image=i, text=""),
                    setattr(self._skin_big_lbl, "image", i),
                ])
        threading.Thread(target=_load_big, daemon=True).start()

        tk.Label(info, text=self.sel_weapon, font=FONT_SMALL, bg=BG2, fg=MUTED).pack()
        tk.Label(info, text=skin_name, font=("Consolas", 13, "bold"),
                 bg=BG2, fg=ACCENT, wraplength=240).pack(pady=(2, 12))
        rarity = skin.get("rarity", {})
        if isinstance(rarity, dict) and rarity.get("name"):
            tk.Label(info, text=f"* {rarity['name']}", font=FONT_SMALL,
                     bg=BG2, fg=rarity.get("color", MUTED)).pack()

        tk.Frame(info, bg=BORDER, height=1).pack(fill="x", pady=12)
        tk.Label(info, text="TYPE", font=FONT_SMALL, bg=BG2, fg=MUTED).pack(anchor="w")
        self.cat_var = tk.StringVar(value="Normal")
        ttk.Combobox(info, textvariable=self.cat_var, values=list(CATEGORY_MAP.keys()),
                     state="readonly", font=FONT_SMALL, width=14).pack(fill="x", pady=(4, 16))
        self._style_combobox()
        tk.Frame(info, bg=BORDER, height=1).pack(fill="x", pady=(0, 12))

        tk.Label(info, text="QUALITE - clique pour voir les prix",
                 font=FONT_SMALL, bg=BG2, fg=MUTED).pack(anchor="w", pady=(0, 6))
        for wear in available_wears:
            btn = tk.Label(info, text=wear, font=FONT_SMALL, bg=BG3, fg=TEXT,
                           pady=7, padx=10, cursor="hand2", anchor="w",
                           highlightbackground=BORDER, highlightthickness=1)
            btn.pack(fill="x", pady=2)
            btn.bind("<Button-1>", lambda e, w=wear: self._start_price_search(w))
            btn.bind("<Enter>", lambda e, b=btn: b.config(bg=CARD_H))
            btn.bind("<Leave>", lambda e, b=btn: b.config(bg=BG3))

        self.results_right = tk.Frame(frame, bg=BG)
        self.results_right.pack(side="left", fill="both", expand=True)
        self._centered_msg(self.results_right, "o", "Choisis une qualite\npour voir les prix")

    def _style_combobox(self):
        s = ttk.Style()
        s.theme_use("default")
        s.configure("TCombobox", fieldbackground=BG3, background=BG3, foreground=TEXT,
                    arrowcolor=ACCENT, bordercolor=BORDER, selectbackground=CARD, selectforeground=TEXT)
        s.map("TCombobox", fieldbackground=[("readonly", BG3)],
              foreground=[("readonly", TEXT)], background=[("readonly", BG3)])

    def _start_price_search(self, wear):
        key = self.api_key.get().strip()
        if not key:
            messagebox.showerror("Cle manquante", "Valide ta cle API d'abord."); return
        name = f"{self.sel_skin.get('name', '')} ({wear})"
        min_f, max_f = FLOAT_RANGES[wear]
        self._centered_msg(self.results_right, "...", f"Chargement...\n{name}", ACCENT)
        threading.Thread(target=self._fetch_price_thread,
                         args=(key, name, min_f, max_f, CATEGORY_MAP[self.cat_var.get()]),
                         daemon=True).start()

    def _fetch_price_thread(self, key, name, min_f, max_f, cat):
        try:
            listings = fetch_listings(key, name, min_f, max_f, cat)
            stats    = analyze_prices(listings)
            self.listings_cache = listings
            self.stats_cache    = stats
            self.after(0, self._show_price_results, name, listings, stats)
        except requests.HTTPError as e:
            code = e.response.status_code
            msg  = "Cle API invalide." if code == 401 else \
                   "Rate limit atteint." if code == 429 else f"HTTP {code}"
            self.after(0, self._centered_msg, self.results_right, "X", msg, RED)
        except Exception as e:
            self.after(0, self._centered_msg, self.results_right, "X", str(e), RED)

    def _show_price_results(self, name, listings, stats):
        self._last_price_name = name
        self._clear(self.results_right)
        sf  = ScrollFrame(self.results_right)
        sf.pack(fill="both", expand=True)
        pad = tk.Frame(sf.inner, bg=BG, padx=20, pady=16)
        pad.pack(fill="both", expand=True)

        tk.Label(pad, text=name, font=("Consolas", 12, "bold"),
                 bg=BG, fg=ACCENT, wraplength=500, justify="left").pack(anchor="w")
        tk.Frame(pad, bg=BORDER, height=1).pack(fill="x", pady=(8, 14))
        if not stats:
            tk.Label(pad, text="Aucun listing trouve.", font=FONT_BODY, bg=BG, fg=MUTED).pack(anchor="w")
            return

        cards_row = tk.Frame(pad, bg=BG)
        cards_row.pack(fill="x", pady=(0, 14))
        for i, (label, value, color) in enumerate([
            ("MINIMUM", self.format_price(stats["min"]),          GREEN),
            ("MOYENNE", self.format_price(int(stats["mean"])),    ACCENT),
            ("MEDIANE", self.format_price(int(stats["median"])), ACCENT2),
            ("MAXIMUM", self.format_price(stats["max"]),          RED),
        ]):
            c = tk.Frame(cards_row, bg=CARD, highlightbackground=BORDER, highlightthickness=1)
            c.grid(row=0, column=i, padx=(0, 8) if i < 3 else 0, sticky="nsew")
            cards_row.columnconfigure(i, weight=1)
            tk.Label(c, text=label, font=FONT_SMALL, bg=CARD, fg=MUTED).pack(anchor="w", padx=10, pady=(8, 0))
            tk.Label(c, text=value, font=FONT_STAT, bg=CARD, fg=color).pack(anchor="w", padx=10)
            tk.Label(c, text=" ", bg=CARD).pack(pady=(0, 6))

        tk.Label(pad,
                 text=f"* {stats['count']} listings  -  Ecart-type : {self.format_price(int(stats.get('stdev', 0)))}",
                 font=FONT_SMALL, bg=BG, fg=MUTED).pack(anchor="w", pady=(0, 12))
        tk.Frame(pad, bg=BORDER, height=1).pack(fill="x", pady=(0, 12))
        self._export_btn(pad, self._export_json, anchor="w", pady=(0, 12))

        tk.Label(pad, text="LISTINGS (tries par prix)",
                 font=FONT_SMALL, bg=BG, fg=MUTED).pack(anchor="w", pady=(0, 6))
        table   = tk.Frame(pad, bg=BG)
        table.pack(fill="x")
        headers = ["#", "Prix", "Float", "Wear", "ST", "Lien"]
        widths  = [3,    10,    12,      14,     4,    6]
        for col, (h, w_) in enumerate(zip(headers, widths)):
            tk.Label(table, text=h, font=FONT_SMALL, bg=BG3, fg=MUTED,
                     width=w_, anchor="w", padx=8, pady=4
                     ).grid(row=0, column=col, sticky="ew", padx=(0, 1))
        for i, listing in enumerate(listings[:30], 1):
            rb   = CARD if i % 2 == 0 else BG2
            item = listing.get("item", {})
            fval = item.get("float_value", "N/A")
            fval_s = f"{fval:.6f}" if isinstance(fval, float) else str(fval)
            price  = self.format_price(listing.get("price", 0))
            pfg    = GREEN if listing.get("price") == stats["min"] else TEXT
            st     = "ST" if item.get("is_stattrak") else "-"
            lid    = listing.get("id", "")
            url    = f"https://csfloat.com/item/{lid}" if lid else ""
            for col, (val, fg) in enumerate(zip(
                [str(i), price, fval_s, item.get("wear_name", "-"), st],
                [MUTED,  pfg,   MUTED,  TEXT,  ACCENT2 if st == "ST" else MUTED]
            )):
                tk.Label(table, text=val, font=FONT_SMALL, bg=rb, fg=fg,
                         width=widths[col], anchor="w", padx=8, pady=5
                         ).grid(row=i, column=col, sticky="ew", padx=(0, 1), pady=1)
            lnk = tk.Label(table, text="->", font=FONT_SMALL, bg=rb,
                           fg=ACCENT2 if url else MUTED, width=widths[5],
                           anchor="w", padx=8, pady=5, cursor="hand2" if url else "arrow")
            lnk.grid(row=i, column=5, sticky="ew", padx=(0, 1), pady=1)
            if url:
                lnk.bind("<Button-1>", lambda e, u=url: webbrowser.open(u))
                lnk.bind("<Enter>", lambda e, l=lnk, r=rb: l.config(fg=TEXT, bg=CARD_H))
                lnk.bind("<Leave>", lambda e, l=lnk, r=rb: l.config(fg=ACCENT2, bg=r))

    def _export_json(self):
        if not self.listings_cache:
            messagebox.showinfo("Aucune donnee", "Lance une recherche d'abord."); return
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")])
        if not path: return
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"stats": self.stats_cache, "listings": self.listings_cache},
                      f, indent=2, ensure_ascii=False)
        messagebox.showinfo("Exporte", f"Sauvegarde :\n{path}")

    # ── Inventaire Steam ──────────────────────────────────────────────────────

    def _show_inventory_screen(self):
        self._update_breadcrumb()
        frame = tk.Frame(self.main_area, bg=BG)
        self._swap(frame)
        tk.Label(frame, text="Inventaire Steam - Valeur estimee",
                 font=FONT_HEAD, bg=BG, fg=MUTED, padx=20, pady=14).pack(anchor="w")
        inp = tk.Frame(frame, bg=BG3, padx=16, pady=12)
        inp.pack(fill="x", padx=20, pady=(0, 10))
        tk.Label(inp, text="SteamID64 ou URL du profil :",
                 font=FONT_SMALL, bg=BG3, fg=MUTED).pack(anchor="w", pady=(0, 6))
        row = tk.Frame(inp, bg=BG3)
        row.pack(fill="x")
        self._inv_steam_var = tk.StringVar()
        tk.Entry(row, textvariable=self._inv_steam_var, bg=BG, fg=TEXT,
                 insertbackground=ACCENT, font=FONT_BODY, bd=0, width=52,
                 highlightthickness=1, highlightbackground=BORDER
                 ).pack(side="left", ipady=4, padx=(0, 8))
        btn = tk.Label(row, text="  Charger  ", bg=ACCENT, fg=BG,
                       font=FONT_SMALL, cursor="hand2", padx=6, pady=4)
        btn.pack(side="left")
        btn.bind("<Button-1>", lambda e: self._start_inventory_fetch())
        tk.Label(inp,
                 text="ex: 76561198xxxxxxxxx  ou  https://steamcommunity.com/profiles/76561198xxxxxxxxx",
                 font=FONT_SMALL, bg=BG3, fg=MUTED).pack(anchor="w", pady=(6, 0))
        self._inv_results = tk.Frame(frame, bg=BG)
        self._inv_results.pack(fill="both", expand=True, padx=20, pady=10)
        tk.Label(self._inv_results, text="Entrez un SteamID64 et cliquez sur Charger.",
                 font=FONT_BODY, bg=BG, fg=MUTED).pack(pady=30)

    def _parse_steam_id(self, raw):
        raw = raw.strip()
        if raw.isdigit() and len(raw) == 17: return raw
        m = re.search(r"/profiles/(\d{17})", raw)
        return m.group(1) if m else None

    def _start_inventory_fetch(self):
        steam_id = self._parse_steam_id(self._inv_steam_var.get())
        if not steam_id:
            messagebox.showerror("SteamID invalide",
                                 "Entrez un SteamID64 (17 chiffres) ou une URL de profil Steam."); return
        if not self.api_key.get().strip():
            messagebox.showerror("Cle manquante", "Valide ta cle API CSFloat d'abord."); return
        self._clear(self._inv_results)
        self._inv_progress = tk.Label(self._inv_results,
                                      text="Chargement de l'inventaire Steam...",
                                      font=FONT_BODY, bg=BG, fg=MUTED)
        self._inv_progress.pack(pady=30)
        threading.Thread(target=self._inventory_thread,
                         args=(steam_id, self.api_key.get().strip()), daemon=True).start()

    def _inventory_thread(self, steam_id, api_key):
        try:
            items = fetch_steam_inventory(steam_id)
        except Exception as e:
            self.after(0, self._inv_error, str(e)); return
        if not items:
            self.after(0, self._inv_error, "Aucun skin marketable trouve."); return
        unique_names = list(dict.fromkeys(i["name"] for i in items))
        price_map = {}
        completed = [0]
        def fetch_price(name):
            try:
                listings = fetch_listings(api_key, name, limit=1)
                return name, listings[0]["price"] if listings else None
            except Exception:
                return name, None
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(fetch_price, n): n for n in unique_names}
            for future in as_completed(futures):
                name, price = future.result()
                price_map[name] = price
                completed[0] += 1
                self.after(0, self._inv_update_progress, completed[0], len(unique_names), name)
        self.after(0, self._inv_show_results, items, price_map)

    def _inv_update_progress(self, current, total, name):
        if self._inv_progress.winfo_exists():
            short = name if len(name) <= 55 else name[:53] + "..."
            self._inv_progress.config(text=f"Recuperation des prix... {current}/{total}\n{short}")

    def _inv_error(self, msg):
        self._clear(self._inv_results)
        tk.Label(self._inv_results, text=msg, font=FONT_BODY, bg=BG, fg=RED).pack(pady=30)

    def _inv_show_results(self, items, price_map):
        self._clear(self._inv_results)
        total_cents = sum(price_map.get(i["name"]) or 0 for i in items)
        priced      = sum(1 for i in items if price_map.get(i["name"]))

        summary = tk.Frame(self._inv_results, bg=BG2, padx=16, pady=12)
        summary.pack(fill="x", pady=(0, 8))
        tk.Label(summary, text=f"{len(items)} skin(s)  ({priced} avec prix CSFloat)",
                 font=FONT_SMALL, bg=BG2, fg=MUTED).pack(side="left")
        tk.Label(summary, text=self.format_price(total_cents),
                 font=("Consolas", 16, "bold"), bg=BG2, fg=ACCENT).pack(side="right")
        tk.Label(summary, text="Valeur estimee : ",
                 font=FONT_SMALL, bg=BG2, fg=MUTED).pack(side="right")
        self._export_btn(self._inv_results, lambda: self._inv_export(items, price_map),
                         anchor="w", pady=(0, 6))

        sf = ScrollFrame(self._inv_results)
        sf.pack(fill="both", expand=True)
        hdr = tk.Frame(sf.inner, bg=BG3, padx=8, pady=4)
        hdr.pack(fill="x", pady=(0, 2))
        tk.Label(hdr, text="x",        font=FONT_SMALL, bg=BG3, fg=MUTED, width=3).pack(side="left")
        tk.Label(hdr, text="Skin",     font=FONT_SMALL, bg=BG3, fg=MUTED,
                 anchor="w").pack(side="left", fill="x", expand=True, padx=8)
        tk.Label(hdr, text="Unitaire", font=FONT_SMALL, bg=BG3, fg=MUTED, width=14, anchor="e").pack(side="left")
        tk.Label(hdr, text="Total",    font=FONT_SMALL, bg=BG3, fg=MUTED, width=14, anchor="e").pack(side="left")

        groups = {}
        for item in items:
            n = item["name"]
            groups.setdefault(n, {"name": n, "count": 0})["count"] += 1
        for idx, g in enumerate(
            sorted(groups.values(),
                   key=lambda x: (price_map.get(x["name"]) or 0) * x["count"], reverse=True)
        ):
            name  = g["name"]
            count = g["count"]
            price = price_map.get(name)
            rb    = CARD if idx % 2 == 0 else BG2
            row   = tk.Frame(sf.inner, bg=rb, padx=8, pady=7)
            row.pack(fill="x", pady=1)
            tk.Label(row, text=f"x{count}", font=FONT_SMALL, bg=rb,
                     fg=ACCENT2, width=3, anchor="w").pack(side="left")
            tk.Label(row, text=name, font=FONT_SMALL, bg=rb, fg=TEXT, anchor="w"
                     ).pack(side="left", fill="x", expand=True, padx=8)
            tk.Label(row, text=self.format_price(price) if price else "-",
                     font=FONT_SMALL, bg=rb, fg=MUTED, width=14, anchor="e").pack(side="left")
            tk.Label(row, text=self.format_price(price * count) if price else "-",
                     font=("Consolas", 9, "bold"), bg=rb,
                     fg=GREEN if price else MUTED, width=14, anchor="e").pack(side="left")

    def _inv_export(self, items, price_map):
        path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON", "*.json")])
        if not path: return
        groups = {}
        for item in items:
            n = item["name"]
            groups.setdefault(n, {"name": n, "count": 0,
                                  "unit_price_cents": price_map.get(n)})["count"] += 1
        export = []
        for g in groups.values():
            p = g["unit_price_cents"]
            g["total_price_cents"] = (p * g["count"]) if p else None
            export.append(g)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(export, f, indent=2, ensure_ascii=False)
        messagebox.showinfo("Exporte", f"Sauvegarde :\n{path}")


if __name__ == "__main__":
    CSFloatApp().mainloop()
