"""Mixin - Ecran 1 : home avec catégories en cards, puis armes."""
import tkinter as tk

from api import get_img_path_by_name
from config import (
    ACCENT, BG, BG2, BG3, BORDER, CARD, CARD_H,
    FONT_BODY, FONT_HEAD, FONT_SMALL, MUTED, SECTION_ICONS, SECTION_ORDER, TEXT,
)
from widgets import CategoryCard, ScrollFrame, SkinCard, grid_card_size


class WeaponsViewMixin:
    # ── Écran home : grille de catégories ─────────────────────────────────────

    def _show_weapons(self):
        self.sel_weapon  = ""
        self.sel_section = ""
        self._update_breadcrumb()

        outer = tk.Frame(self.main_area, bg=BG)
        self._swap(outer)

        # Titre
        tk.Label(outer, text="Catégories", font=FONT_HEAD,
                 bg=BG, fg=MUTED, padx=24).pack(anchor="w", pady=(16, 4))

        # Grille de cards catégories
        grid_frame = tk.Frame(outer, bg=BG, padx=16)
        grid_frame.pack(fill="x")

        COLS = 3
        available = [
            (s, self.category_weapons_map.get(s, []))
            for s in SECTION_ORDER if self.category_weapons_map.get(s)
        ]
        for i, (section, weapons) in enumerate(available):
            icon = SECTION_ICONS.get(section, "🎮")
            r, c = divmod(i, COLS)
            CategoryCard(
                grid_frame, title=section, icon=icon, count=len(weapons),
                callback=lambda s=section: self._select_section(s),
                w=220, h=150,
            ).grid(row=r, column=c, padx=8, pady=8, sticky="nsew")

        for col in range(COLS):
            grid_frame.columnconfigure(col, weight=1)

        # ── Bloc inventaire inline ────────────────────────────────────────────
        tk.Frame(outer, bg=BORDER, height=1).pack(fill="x", padx=16, pady=(12, 0))

        inv_frame = tk.Frame(outer, bg=BG2, padx=20, pady=14)
        inv_frame.pack(fill="x", padx=16, pady=(0, 12))

        tk.Label(inv_frame, text="🎒  Inventaire Steam",
                 font=FONT_HEAD, bg=BG2, fg=TEXT).pack(anchor="w", pady=(0, 8))

        row = tk.Frame(inv_frame, bg=BG2)
        row.pack(fill="x")

        if not hasattr(self, "_inv_steam_var"):
            self._inv_steam_var = tk.StringVar()

        entry = tk.Entry(row, textvariable=self._inv_steam_var,
                         bg=BG3, fg=TEXT, insertbackground=ACCENT,
                         font=FONT_BODY, bd=0, width=54,
                         highlightthickness=1, highlightbackground=BORDER)
        entry.pack(side="left", ipady=6, padx=(0, 10))
        self._attach_paste_menu(entry)

        btn = tk.Label(row, text="  Charger  ", bg=ACCENT, fg=BG,
                       font=FONT_SMALL, cursor="hand2", padx=8, pady=6)
        btn.pack(side="left")
        btn.bind("<Button-1>", lambda e: self._goto_inventory_and_fetch())
        entry.bind("<Return>",  lambda e: self._goto_inventory_and_fetch())

        tk.Label(inv_frame,
                 text="ex: 76561198xxxxxxxxx  ou  https://steamcommunity.com/profiles/76561198xxxxxxxxx",
                 font=FONT_SMALL, bg=BG2, fg=MUTED).pack(anchor="w", pady=(6, 0))

    def _goto_inventory_and_fetch(self):
        """Navigue vers la page inventaire puis lance le fetch."""
        self._show_inventory_page()
        self._start_inventory_fetch()

    # ── Sélection d'une section → liste d'armes ───────────────────────────────

    def _select_section(self, section: str):
        self.sel_section = section
        self._update_breadcrumb(section=section)

        outer = tk.Frame(self.main_area, bg=BG)
        self._swap(outer)

        weapons = self.category_weapons_map.get(section, [])
        if not weapons:
            tk.Label(outer, text="Aucune arme disponible",
                     font=FONT_BODY, bg=BG, fg=MUTED).pack(pady=40)
            return

        # Barre de recherche
        search_bar = tk.Frame(outer, bg=BG, padx=20, pady=10)
        search_bar.pack(fill="x")
        self._weapon_search = tk.StringVar()
        tk.Entry(
            search_bar, textvariable=self._weapon_search,
            bg=BG3, fg=TEXT, insertbackground=ACCENT, font=FONT_BODY,
            bd=0, width=28, highlightthickness=1, highlightbackground=BORDER,
        ).pack(side="left", ipady=5)
        tk.Label(search_bar, text=f"{len(weapons)} armes",
                 font=FONT_SMALL, bg=BG, fg=MUTED).pack(side="left", padx=12)

        # Grille scrollable
        sf = ScrollFrame(outer)
        sf.pack(fill="both", expand=True)
        self._weapons_inner  = sf.inner
        self._weapons_canvas = sf.canvas
        self._last_section_w = 0

        self._current_weapons = weapons
        self._weapon_search.trace_add("write",
                                      lambda *_: self._refresh_section_grid())
        sf.canvas.bind("<Configure>",
                       lambda e: self._on_weapons_canvas_resize(e.width))
        sf.canvas.after_idle(
            lambda: self._refresh_section_grid(self._weapons_canvas.winfo_width()))

    # ── Grille d'armes ────────────────────────────────────────────────────────

    def _on_weapons_canvas_resize(self, width: int):
        """Re-layout seulement si la largeur change de plus de 20 px."""
        if abs(width - self._last_section_w) >= 20:
            self._refresh_section_grid(width)

    def _refresh_section_grid(self, avail_w: int = 0):
        if avail_w == 0:
            avail_w = self._weapons_canvas.winfo_width()
        self._last_section_w = avail_w

        for child in self._weapons_inner.winfo_children():
            child.destroy()

        q = self._weapon_search.get().lower()
        weapons = ([w for w in self._current_weapons if q in w.lower()]
                   if q else self._current_weapons)

        if not weapons:
            tk.Label(self._weapons_inner, text="Aucune arme trouvée",
                     font=FONT_BODY, bg=BG, fg=MUTED).pack(pady=20)
            return

        cols, card_w, card_h = grid_card_size(
            len(weapons), avail_w, pad=10, min_w=120, max_w=240)
        img_w = int(card_w * 0.78)
        img_h = int(card_h * 0.62)

        grid = tk.Frame(self._weapons_inner, bg=BG)
        grid.pack(fill="x", padx=5, pady=5)

        for i, weapon in enumerate(weapons):
            skins    = self.weapons_map.get(weapon, [])
            img_path = get_img_path_by_name(skins[0].get("name", "")) if skins else ""
            img_url  = "" if img_path else (skins[0].get("image", "") if skins else "")
            row, col = divmod(i, cols)
            SkinCard(
                grid, name=weapon,
                img_url=img_url, img_path=img_path or "",
                callback=lambda w=weapon: self._select_weapon(w),
                card_w=card_w, card_h=card_h, img_size=(img_w, img_h),
            ).grid(row=row, column=col, padx=5, pady=5, sticky="nsew")

        for c in range(cols):
            grid.columnconfigure(c, weight=1)

    def _select_weapon(self, weapon: str):
        self.sel_weapon = weapon
        self._show_skins()
