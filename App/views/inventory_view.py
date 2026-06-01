"""Mixin - Ecran inventaire Steam : fetch, prix paralleles, export."""
import json
import re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from tkinter import filedialog, messagebox
import tkinter as tk

from api import fetch_listings, fetch_steam_inventory
from config import (
    ACCENT, ACCENT2, BG, BG2, BG3, BORDER,
    FONT_BODY, FONT_HEAD, FONT_SMALL, GREEN, MUTED, RED, TEXT,
)
from widgets import ScrollFrame


class InventoryViewMixin:
    def _build_inline_inventory(self, parent):
        """Inventaire intégré dans la home, sous les catégories."""
        frame = tk.Frame(parent, bg=BG, padx=24, pady=14)
        frame.pack(fill="both", expand=True)

        tk.Label(frame, text="Inventaire Steam",
                 font=FONT_HEAD, bg=BG, fg=TEXT).pack(anchor="w", pady=(0, 10))

        input_frame = tk.Frame(frame, bg=BG3, padx=16, pady=12)
        input_frame.pack(fill="x")
        tk.Label(input_frame, text="SteamID64 ou URL du profil :",
                 font=FONT_SMALL, bg=BG3, fg=MUTED).pack(anchor="w", pady=(0, 6))
        row = tk.Frame(input_frame, bg=BG3)
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
        tk.Label(input_frame,
                 text="ex: 76561198xxxxxxxxx  ou  https://steamcommunity.com/profiles/76561198xxxxxxxxx",
                 font=FONT_SMALL, bg=BG3, fg=MUTED).pack(anchor="w", pady=(6, 0))

        self._inv_results = tk.Frame(frame, bg=BG)
        self._inv_results.pack(fill="both", expand=True, pady=(10, 0))
        tk.Label(self._inv_results, text="Entrez un SteamID64 et cliquez sur Charger.",
                 font=FONT_BODY, bg=BG, fg=MUTED).pack(pady=20)

    def _parse_steam_id(self, raw):
        raw = raw.strip()
        if raw.isdigit() and len(raw) == 17:
            return raw
        m = re.search(r"/profiles/(\d{17})", raw)
        return m.group(1) if m else None

    def _start_inventory_fetch(self):
        steam_id = self._parse_steam_id(self._inv_steam_var.get())
        if not steam_id:
            messagebox.showerror("SteamID invalide",
                                 "Entrez un SteamID64 (17 chiffres) ou une URL de profil Steam.")
            return
        if not self.api_key.get().strip():
            messagebox.showerror("Cle manquante", "Valide ta cle API CSFloat d'abord.")
            return
        for w in self._inv_results.winfo_children():
            w.destroy()
        self._inv_progress = tk.Label(self._inv_results,
                                      text="Chargement de l'inventaire Steam...",
                                      font=FONT_BODY, bg=BG, fg=MUTED)
        self._inv_progress.pack(pady=30)
        threading.Thread(target=self._inventory_thread,
                         args=(steam_id, self.api_key.get().strip()), daemon=True).start()

    def _inventory_thread(self, steam_id, api_key):
        try:
            items = fetch_steam_inventory(steam_id)
        except (ValueError, Exception) as e:
            self.after(0, self._inv_error, str(e))
            return
        if not items:
            self.after(0, self._inv_error, "Aucun skin marketable trouve.")
            return

        unique_names = list(dict.fromkeys(i["name"] for i in items))
        price_map    = {}
        completed    = [0]

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
                self.after(0, self._inv_update_progress,
                           completed[0], len(unique_names), name)

        self.after(0, self._inv_show_results, items, price_map)

    def _inv_update_progress(self, current, total, name):
        if self._inv_progress.winfo_exists():
            short = name if len(name) <= 55 else name[:53] + "..."
            self._inv_progress.config(
                text=f"Recuperation des prix... {current}/{total}\n{short}")

    def _inv_error(self, msg):
        for w in self._inv_results.winfo_children():
            w.destroy()
        tk.Label(self._inv_results, text=msg,
                 font=FONT_BODY, bg=BG, fg=RED).pack(pady=30)

    def _inv_show_results(self, items, price_map):
        for w in self._inv_results.winfo_children():
            w.destroy()

        total_cents = sum(price_map.get(i["name"]) or 0 for i in items)
        priced      = sum(1 for i in items if price_map.get(i["name"]))

        summary = tk.Frame(self._inv_results, bg=BG2, padx=16, pady=12)
        summary.pack(fill="x", pady=(0, 8))
        tk.Label(summary, text=f"{len(items)} skin(s)  ({priced} avec prix CSFloat)",
                 font=FONT_SMALL, bg=BG2, fg=MUTED).pack(side="left")
        tk.Label(summary, text=self.format_price(total_cents),
                 font=("Segoe UI", 15, "bold"), bg=BG2, fg=ACCENT).pack(side="right")
        tk.Label(summary, text="Valeur estimee : ",
                 font=FONT_SMALL, bg=BG2, fg=MUTED).pack(side="right")

        exp = tk.Label(self._inv_results, text="Exporter JSON", font=FONT_SMALL,
                       bg=BG3, fg=TEXT, padx=10, pady=5, cursor="hand2")
        exp.pack(anchor="w", pady=(0, 6))
        exp.bind("<Button-1>", lambda e: self._inv_export(items, price_map))
        exp.bind("<Enter>", lambda e: exp.config(bg=BORDER))
        exp.bind("<Leave>", lambda e: exp.config(bg=BG3))

        sf = ScrollFrame(self._inv_results)
        sf.pack(fill="both", expand=True)

        hdr = tk.Frame(sf.inner, bg=BG3, padx=8, pady=4)
        hdr.pack(fill="x", pady=(0, 2))
        tk.Label(hdr, text="x", font=FONT_SMALL, bg=BG3, fg=MUTED, width=3).pack(side="left")
        tk.Label(hdr, text="Skin", font=FONT_SMALL, bg=BG3, fg=MUTED,
                 anchor="w").pack(side="left", fill="x", expand=True, padx=8)
        tk.Label(hdr, text="Unitaire", font=FONT_SMALL, bg=BG3, fg=MUTED,
                 width=14, anchor="e").pack(side="left")
        tk.Label(hdr, text="Total", font=FONT_SMALL, bg=BG3, fg=MUTED,
                 width=14, anchor="e").pack(side="left")

        groups = {}
        for item in items:
            n = item["name"]
            groups.setdefault(n, {"name": n, "count": 0})["count"] += 1

        for idx, g in enumerate(
            sorted(groups.values(),
                   key=lambda x: (price_map.get(x["name"]) or 0) * x["count"],
                   reverse=True)
        ):
            name  = g["name"]
            count = g["count"]
            price = price_map.get(name)
            rb    = CARD if idx % 2 == 0 else BG2
            row   = tk.Frame(sf.inner, bg=rb, padx=8, pady=7)
            row.pack(fill="x", pady=1)
            tk.Label(row, text=f"x{count}", font=FONT_SMALL, bg=rb,
                     fg=ACCENT2, width=3, anchor="w").pack(side="left")
            tk.Label(row, text=name, font=FONT_SMALL, bg=rb,
                     fg=TEXT, anchor="w").pack(side="left", fill="x", expand=True, padx=8)
            tk.Label(row, text=self.format_price(price) if price else "-",
                     font=FONT_SMALL, bg=rb, fg=MUTED,
                     width=14, anchor="e").pack(side="left")
            tk.Label(row, text=self.format_price(price * count) if price else "-",
                     font=("Segoe UI", 9, "bold"), bg=rb,
                     fg=GREEN if price else MUTED,
                     width=14, anchor="e").pack(side="left")

    def _inv_export(self, items, price_map):
        path = filedialog.asksaveasfilename(defaultextension=".json",
                                            filetypes=[("JSON", "*.json")])
        if not path:
            return
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
