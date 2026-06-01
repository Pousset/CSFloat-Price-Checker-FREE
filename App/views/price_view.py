"""Mixin - Ecran 3 : selection qualite et affichage des prix."""
import json
import threading
import webbrowser
from tkinter import filedialog, messagebox, ttk
import tkinter as tk

import requests

from api import analyze_prices, fetch_listings
from config import (
    ACCENT, ACCENT2, BG, BG2, BG3, BORDER, CARD, CARD_H,
    CATEGORY_MAP, FLOAT_RANGES, FONT_BODY, FONT_SMALL, FONT_STAT,
    GREEN, MUTED, RED, TEXT,
)
from widgets import ScrollFrame, load_image


class PriceViewMixin:
    def _show_quality_picker(self):
        skin      = self.sel_skin
        full_name = skin.get("name", "")
        parts     = full_name.split(" | ")
        skin_name = parts[1] if len(parts) > 1 else full_name
        self._update_breadcrumb(section=self.sel_section, weapon=self.sel_weapon, skin_name=skin_name)

        min_f = skin.get("min_float", 0.0)
        max_f = skin.get("max_float", 1.0)
        available_wears = [w for w, (lo, hi) in FLOAT_RANGES.items()
                           if lo < max_f and hi > min_f]

        frame = tk.Frame(self.main_area, bg=BG)
        self._swap(frame)

        left = tk.Frame(frame, bg=BG2, width=280)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)
        tk.Frame(frame, bg=BORDER, width=1).pack(side="left", fill="y")
        info = tk.Frame(left, bg=BG2, padx=20, pady=20)
        info.pack(fill="both", expand=True)

        self._skin_big_lbl = tk.Label(info, bg=BG2, text="...", fg=MUTED,
                                      font=("Consolas", 24))
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
        self._show_results_placeholder()

    def _style_combobox(self):
        s = ttk.Style()
        s.theme_use("default")
        s.configure("TCombobox", fieldbackground=BG3, background=BG3,
                    foreground=TEXT, arrowcolor=ACCENT, bordercolor=BORDER,
                    selectbackground=CARD, selectforeground=TEXT)
        s.map("TCombobox",
              fieldbackground=[("readonly", BG3)],
              foreground=[("readonly", TEXT)],
              background=[("readonly", BG3)])

    def _show_results_placeholder(self):
        for w in self.results_right.winfo_children():
            w.destroy()
        f = tk.Frame(self.results_right, bg=BG)
        f.place(relx=.5, rely=.5, anchor="center")
        tk.Label(f, text="o", font=("Consolas", 40), bg=BG, fg=BORDER).pack()
        tk.Label(f, text="Choisis une qualite\npour voir les prix",
                 font=FONT_BODY, bg=BG, fg=MUTED, justify="center").pack(pady=8)

    def _start_price_search(self, wear):
        key = self.api_key.get().strip()
        if not key:
            messagebox.showerror("Cle manquante", "Valide ta cle API d'abord.")
            return
        base_name = self.sel_skin.get("name", "")
        cat_label = self.cat_var.get()
        cat = CATEGORY_MAP[cat_label]
        # Construire le market_hash_name exact attendu par CSFloat.
        # Couteaux/gants commencent par "★ " — StatTrak s'insère après le ★.
        # Exemples corrects :
        #   Normal  : "★ Karambit | Fade (Factory New)"
        #   StatTrak: "★ StatTrak™ Karambit | Fade (Factory New)"
        #   Normal  : "AK-47 | Redline (Factory New)"
        #   StatTrak: "StatTrak™ AK-47 | Redline (Factory New)"
        if cat == 2 and "StatTrak\u2122" not in base_name:
            if base_name.startswith("\u2605 "):
                prefixed = f"\u2605 StatTrak\u2122 {base_name[2:]}"
            else:
                prefixed = f"StatTrak\u2122 {base_name}"
        elif cat == 3 and not base_name.startswith("Souvenir"):
            prefixed = f"Souvenir {base_name}"
        else:
            prefixed = base_name
        market_name = f"{prefixed} ({wear})"
        min_f, max_f = FLOAT_RANGES[wear]
        self._show_loading_results(market_name)
        threading.Thread(target=self._fetch_price_thread,
                         args=(key, market_name, min_f, max_f, cat), daemon=True).start()

    def _fetch_price_thread(self, key, name, min_f, max_f, cat):
        try:
            listings = fetch_listings(key, name, min_f, max_f, cat)
            stats    = analyze_prices(listings)
            self.listings_cache = listings
            self.stats_cache    = stats
            self.after(0, self._show_price_results, name, listings, stats)
        except requests.HTTPError as e:
            code = e.response.status_code if e.response is not None else 0
            if code == 401:
                msg = "Cl\u00e9 API invalide — v\u00e9rifie ta cl\u00e9."
            elif code == 429:
                msg = "Rate limit atteint — attends quelques secondes."
            elif code == 403:
                msg = "403 — Cl\u00e9 invalide ou expir\u00e9e.\nReg\u00e9n\u00e8re ta cl\u00e9 sur\ncsfloat.com/profile > Developer"
            else:
                msg = str(e) if str(e) else f"HTTP {code}"
            self.after(0, self._show_error_results, msg)
        except Exception as e:
            self.after(0, self._show_error_results, str(e))

    def _show_loading_results(self, name):
        for w in self.results_right.winfo_children():
            w.destroy()
        f = tk.Frame(self.results_right, bg=BG)
        f.place(relx=.5, rely=.5, anchor="center")
        tk.Label(f, text="chargement...", font=("Consolas", 32), bg=BG, fg=ACCENT).pack()
        tk.Label(f, text=f"Chargement...\n{name}",
                 font=FONT_BODY, bg=BG, fg=MUTED, justify="center").pack(pady=8)

    def _show_error_results(self, msg):
        for w in self.results_right.winfo_children():
            w.destroy()
        f = tk.Frame(self.results_right, bg=BG)
        f.place(relx=.5, rely=.5, anchor="center")
        tk.Label(f, text="X", font=("Consolas", 32), bg=BG, fg=RED).pack()
        tk.Label(f, text=msg, font=FONT_BODY, bg=BG,
                 fg=RED, wraplength=300, justify="center").pack(pady=8)

    def _show_price_results(self, name, listings, stats):
        self._last_price_name = name
        for w in self.results_right.winfo_children():
            w.destroy()
        sf  = ScrollFrame(self.results_right)
        sf.pack(fill="both", expand=True)
        pad = tk.Frame(sf.inner, bg=BG, padx=20, pady=16)
        pad.pack(fill="both", expand=True)

        tk.Label(pad, text=name, font=("Consolas", 12, "bold"),
                 bg=BG, fg=ACCENT, wraplength=500, justify="left").pack(anchor="w")
        tk.Frame(pad, bg=BORDER, height=1).pack(fill="x", pady=(8, 14))

        if not stats:
            tk.Label(pad, text="Aucun listing trouve.",
                     font=FONT_BODY, bg=BG, fg=MUTED).pack(anchor="w")
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
            tk.Label(c, text=label, font=FONT_SMALL, bg=CARD, fg=MUTED
                     ).pack(anchor="w", padx=10, pady=(8, 0))
            tk.Label(c, text=value, font=FONT_STAT, bg=CARD, fg=color
                     ).pack(anchor="w", padx=10)
            tk.Label(c, text=" ", bg=CARD).pack(pady=(0, 6))

        tk.Label(pad,
                 text=f"* {stats['count']} listings  -  "
                      f"Ecart-type : {self.format_price(int(stats.get('stdev', 0)))}",
                 font=FONT_SMALL, bg=BG, fg=MUTED).pack(anchor="w", pady=(0, 12))
        tk.Frame(pad, bg=BORDER, height=1).pack(fill="x", pady=(0, 12))

        exp = tk.Label(pad, text="Exporter JSON", font=FONT_SMALL,
                       bg=BG3, fg=TEXT, padx=10, pady=5, cursor="hand2")
        exp.pack(anchor="w", pady=(0, 12))
        exp.bind("<Button-1>", lambda e: self._export_json())
        exp.bind("<Enter>",    lambda e: exp.config(bg=BORDER))
        exp.bind("<Leave>",    lambda e: exp.config(bg=BG3))

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
            rb     = CARD if i % 2 == 0 else BG2
            item   = listing.get("item", {})
            fval   = item.get("float_value", "N/A")
            fval_s = f"{fval:.6f}" if isinstance(fval, float) else str(fval)
            price  = self.format_price(listing.get("price", 0))
            pfg    = GREEN if listing.get("price") == stats["min"] else TEXT
            st     = "ST" if item.get("is_stattrak") else "-"
            lid    = listing.get("id", "")
            url    = f"https://csfloat.com/item/{lid}" if lid else ""
            for col, (val, fg) in enumerate(zip(
                [str(i), price, fval_s, item.get("wear_name", "-"), st],
                [MUTED,  pfg,   MUTED,  TEXT,                       ACCENT2 if st == "ST" else MUTED]
            )):
                tk.Label(table, text=val, font=FONT_SMALL, bg=rb, fg=fg,
                         width=widths[col], anchor="w", padx=8, pady=5
                         ).grid(row=i, column=col, sticky="ew", padx=(0, 1), pady=1)
            lnk = tk.Label(table, text="->", font=FONT_SMALL,
                           bg=rb, fg=ACCENT2 if url else MUTED,
                           width=widths[5], anchor="w", padx=8, pady=5,
                           cursor="hand2" if url else "arrow")
            lnk.grid(row=i, column=5, sticky="ew", padx=(0, 1), pady=1)
            if url:
                lnk.bind("<Button-1>", lambda e, u=url: webbrowser.open(u))
                lnk.bind("<Enter>", lambda e, l=lnk, r=rb: l.config(fg=TEXT, bg=CARD_H))
                lnk.bind("<Leave>", lambda e, l=lnk, r=rb: l.config(fg=ACCENT2, bg=r))

    def _export_json(self):
        if not self.listings_cache:
            messagebox.showinfo("Aucune donnee", "Lance une recherche d'abord.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".json",
                                            filetypes=[("JSON", "*.json")])
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"stats": self.stats_cache, "listings": self.listings_cache},
                      f, indent=2, ensure_ascii=False)
        messagebox.showinfo("Exporte", f"Sauvegarde :\n{path}")
