"""Mixin - Ecran inventaire Steam : fetch, prix paralleles, export."""
import json
import re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from tkinter import filedialog, messagebox
import tkinter as tk

from api import analyze_prices, fetch_listings, fetch_steam_inventory
from config import (
    ACCENT, ACCENT2, BG, BG2, BG3, BORDER, CARD,
    FONT_BODY, FONT_HEAD, FONT_SMALL, GREEN, MUTED, RED, TEXT,
)
from price_history import save_price_search
from widgets import ScrollFrame, SkinCard, grid_card_size


class InventoryViewMixin:
    def _attach_paste_menu(self, entry: tk.Entry):
        """Ajoute un menu contextuel couper/copier/coller sur un widget Entry."""
        menu = tk.Menu(entry, tearoff=0, bg=BG2, fg=TEXT,
                       activebackground=ACCENT, activeforeground=BG,
                       bd=0, relief="flat")
        menu.add_command(label="Couper",   command=lambda: entry.event_generate("<<Cut>>"))
        menu.add_command(label="Copier",   command=lambda: entry.event_generate("<<Copy>>"))
        menu.add_command(label="Coller",   command=lambda: entry.event_generate("<<Paste>>"))
        menu.add_separator()
        menu.add_command(label="Tout sélectionner",
                         command=lambda: entry.select_range(0, "end"))

        def show_menu(e):
            try:
                menu.tk_popup(e.x_root, e.y_root)
            finally:
                menu.grab_release()

        entry.bind("<Button-3>", show_menu)

    def _show_inventory_page(self):
        """Ouvre l'inventaire en page complète (comme les autres vues)."""
        self._update_breadcrumb(section="Inventaire Steam")
        outer = tk.Frame(self.main_area, bg=BG)
        self._swap(outer)

        tk.Label(outer, text="🎒  Inventaire Steam",
                 font=FONT_HEAD, bg=BG, fg=TEXT, padx=24).pack(anchor="w", pady=(16, 8))

        input_frame = tk.Frame(outer, bg=BG2, padx=20, pady=14)
        input_frame.pack(fill="x", padx=16)

        tk.Label(input_frame, text="SteamID64 ou URL du profil :",
                 font=FONT_SMALL, bg=BG2, fg=MUTED).pack(anchor="w", pady=(0, 6))
        row = tk.Frame(input_frame, bg=BG2)
        row.pack(fill="x")

        if not hasattr(self, "_inv_steam_var"):
            self._inv_steam_var = tk.StringVar()

        entry = tk.Entry(row, textvariable=self._inv_steam_var, bg=BG3, fg=TEXT,
                         insertbackground=ACCENT, font=FONT_BODY, bd=0, width=56,
                         highlightthickness=1, highlightbackground=BORDER)
        entry.pack(side="left", ipady=6, padx=(0, 10))
        self._attach_paste_menu(entry)
        entry.bind("<Return>", lambda e: self._start_inventory_fetch())

        btn = tk.Label(row, text="  Charger  ", bg=ACCENT, fg=BG,
                       font=FONT_SMALL, cursor="hand2", padx=8, pady=6)
        btn.pack(side="left")
        btn.bind("<Button-1>", lambda e: self._start_inventory_fetch())

        tk.Label(input_frame,
                 text="ex: 76561198xxxxxxxxx  ou  https://steamcommunity.com/profiles/76561198xxxxxxxxx",
                 font=FONT_SMALL, bg=BG2, fg=MUTED).pack(anchor="w", pady=(8, 0))

        # Zone de résultats (prend tout l'espace restant)
        self._inv_results = tk.Frame(outer, bg=BG)
        self._inv_results.pack(fill="both", expand=True, padx=16, pady=(12, 0))
        tk.Label(self._inv_results,
                 text="Entrez un SteamID64 et cliquez sur Charger.",
                 font=FONT_BODY, bg=BG, fg=MUTED).pack(pady=30)

    # Ancienne méthode inline conservée pour compatibilité éventuelle
    def _build_inline_inventory(self, parent):
        self._show_inventory_page()

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
                try:
                    save_price_search(
                        name,
                        listings,
                        analyze_prices(listings),
                        limit_requested=1,
                        source="inventory_view",
                    )
                except Exception:
                    pass
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

        # ── Barre récap ──────────────────────────────────────────────────────
        summary = tk.Frame(self._inv_results, bg=BG2, padx=16, pady=12)
        summary.pack(fill="x", pady=(0, 8))
        tk.Label(summary, text=f"{len(items)} skin(s)  ({priced} avec prix CSFloat)",
                 font=FONT_SMALL, bg=BG2, fg=MUTED).pack(side="left")
        tk.Label(summary, text=self.format_price(total_cents),
                 font=("Segoe UI", 15, "bold"), bg=BG2, fg=ACCENT).pack(side="right")
        tk.Label(summary, text="Valeur estimée : ",
                 font=FONT_SMALL, bg=BG2, fg=MUTED).pack(side="right")

        exp = tk.Label(self._inv_results, text="  Exporter JSON  ", font=FONT_SMALL,
                       bg=BG3, fg=TEXT, padx=10, pady=5, cursor="hand2")
        exp.pack(anchor="w", pady=(0, 8))
        exp.bind("<Button-1>", lambda e: self._inv_export(items, price_map))
        exp.bind("<Enter>", lambda e: exp.config(bg=BORDER))
        exp.bind("<Leave>", lambda e: exp.config(bg=BG3))

        # ── Grouper par nom ──────────────────────────────────────────────────
        groups: dict = {}
        for item in items:
            n = item["name"]
            if n not in groups:
                groups[n] = {"name": n, "count": 0,
                              "icon_url": item.get("icon_url", "")}
            groups[n]["count"] += 1

        self._inv_groups    = sorted(groups.values(),
                                     key=lambda x: (price_map.get(x["name"]) or 0) * x["count"],
                                     reverse=True)
        self._inv_price_map = price_map
        self._inv_last_w    = 0

        # ── ScrollFrame + grille responsive ─────────────────────────────────
        sf = ScrollFrame(self._inv_results)
        sf.pack(fill="both", expand=True)
        self._inv_sf = sf

        sf.canvas.bind("<Configure>", lambda e: self._inv_on_resize(e.width))
        sf.canvas.after_idle(lambda: self._inv_render_cards(sf.canvas.winfo_width()))

    def _inv_on_resize(self, width: int):
        if abs(width - self._inv_last_w) >= 20:
            self._inv_render_cards(width)

    def _inv_render_cards(self, avail_w: int = 0):
        if avail_w == 0:
            avail_w = self._inv_sf.canvas.winfo_width()
        self._inv_last_w = avail_w

        for child in self._inv_sf.inner.winfo_children():
            if getattr(child, "_is_inv_grid", False):
                child.destroy()

        groups = self._inv_groups
        if not groups:
            return

        cols, card_w, card_h = grid_card_size(
            len(groups), avail_w, pad=10, min_w=120, max_w=240)
        # hauteur légèrement augmentée pour le subtitle prix
        card_h = int(card_h * 1.10)
        img_w  = int(card_w * 0.78)
        img_h  = int(card_h * 0.52)

        grid = tk.Frame(self._inv_sf.inner, bg=BG)
        grid._is_inv_grid = True
        grid.pack(fill="x", padx=5, pady=5)

        for i, g in enumerate(groups):
            name     = g["name"]
            count    = g["count"]
            icon_url = g["icon_url"]
            price    = self._inv_price_map.get(name)

            parts        = name.split(" | ")
            display_name = parts[1] if len(parts) > 1 else name
            if count > 1:
                display_name = f"x{count} {display_name}"

            subtitle = self.format_price(price) if price else "—"
            img_url  = (f"https://community.akamai.steamstatic.com/economy/image/{icon_url}"
                        if icon_url else "")

            row, col = divmod(i, cols)
            SkinCard(grid, name=display_name,
                     img_url=img_url,
                     subtitle=subtitle,
                     card_w=card_w, card_h=card_h, img_size=(img_w, img_h),
                     ).grid(row=row, column=col, padx=5, pady=5, sticky="nsew")

        for c in range(cols):
            grid.columnconfigure(c, weight=1)

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
