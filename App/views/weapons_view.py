"""Mixin - Ecran 1 : home avec catégories en cards, puis armes."""
import tkinter as tk

from api import get_img_path_by_name
from config import (
    ACCENT, BG, BG2, BG3, BORDER, CARD, CARD_H,
    FONT_BODY, FONT_HEAD, FONT_SMALL, MUTED, SECTION_ICONS, SECTION_ORDER, TEXT,
)
from widgets import CategoryCard, ScrollFrame, SkinCard


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

        # Séparateur
        sep = tk.Frame(outer, bg=BG, padx=24, pady=8)
        sep.pack(fill="x")
        tk.Frame(sep, bg=BORDER, height=1).pack(fill="x")

        # Inventaire inline
        self._build_inline_inventory(outer)

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
        self._weapons_grid = tk.Frame(sf.inner, bg=BG, padx=20)
        self._weapons_grid.pack(fill="both", pady=10)

        self._current_weapons = weapons
        self._weapon_search.trace_add("write", lambda *_: self._refresh_section_grid())
        self._refresh_section_grid()

    # ── Grille d'armes ────────────────────────────────────────────────────────

    def _refresh_section_grid(self):
        for w in self._weapons_grid.winfo_children():
            w.destroy()
        q = self._weapon_search.get().lower()
        weapons = ([w for w in self._current_weapons if q in w.lower()]
                   if q else self._current_weapons)
        cols = 6
        for i, weapon in enumerate(weapons):
            skins    = self.weapons_map.get(weapon, [])
            img_path = get_img_path_by_name(skins[0].get("name", "")) if skins else ""
            img_url  = "" if img_path else (skins[0].get("image", "") if skins else "")
            row, col = divmod(i, cols)
            SkinCard(
                self._weapons_grid, name=weapon,
                img_url=img_url, img_path=img_path or "",
                callback=lambda w=weapon: self._select_weapon(w),
                card_w=148, card_h=120, img_size=(115, 80),
            ).grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
        if not weapons:
            tk.Label(self._weapons_grid, text="Aucune arme trouvée",
                     font=FONT_BODY, bg=BG, fg=MUTED).pack(pady=20)

    def _select_weapon(self, weapon: str):
        self.sel_weapon = weapon
        self._show_skins()
