"""Mixin - Ecran 1 : grille de selection des armes."""
import tkinter as tk

from config import ACCENT, BG, BG3, BORDER, FONT_BODY, FONT_HEAD, MUTED, TEXT, WEAPON_ORDER
from widgets import ScrollFrame, SkinCard


class WeaponsViewMixin:
    def _show_weapons(self):
        self.sel_weapon = ""
        self._update_breadcrumb()
        sf = ScrollFrame(self.main_area)
        self._swap(sf)
        tk.Label(sf.inner, text="Choisis une arme", font=FONT_HEAD,
                 bg=BG, fg=MUTED, padx=20, pady=14).pack(anchor="w")
        bar = tk.Frame(sf.inner, bg=BG, padx=20)
        bar.pack(fill="x", pady=(0, 10))
        self._weapon_search = tk.StringVar()
        tk.Entry(bar, textvariable=self._weapon_search, bg=BG3, fg=TEXT,
                 insertbackground=ACCENT, font=FONT_BODY, bd=0, width=30,
                 highlightthickness=1, highlightbackground=BORDER
                 ).pack(side="left", ipady=5, padx=(0, 8))
        self._weapons_grid = tk.Frame(sf.inner, bg=BG, padx=20)
        self._weapons_grid.pack(fill="both")
        self._weapon_search.trace_add("write", lambda *_: self._refresh_weapons_grid())
        self._refresh_weapons_grid()

    def _refresh_weapons_grid(self):
        for w in self._weapons_grid.winfo_children():
            w.destroy()
        q      = self._weapon_search.get().lower()
        known  = [w for w in WEAPON_ORDER if w in self.weapons_map]
        others = sorted(k for k in self.weapons_map if k not in WEAPON_ORDER)
        weapons = [w for w in known + others if q in w.lower()] if q else known + others
        for i, weapon in enumerate(weapons):
            skins   = self.weapons_map[weapon]
            img_url = skins[0].get("image", "") if skins else ""
            row, col = divmod(i, 7)
            SkinCard(self._weapons_grid, name=weapon, img_url=img_url,
                     callback=lambda w=weapon: self._select_weapon(w),
                     card_w=130, card_h=115, img_size=(100, 75)
                     ).grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
        if not weapons:
            tk.Label(self._weapons_grid, text="Aucune arme trouvee",
                     font=FONT_BODY, bg=BG, fg=MUTED).pack(pady=20)

    def _select_weapon(self, weapon):
        self.sel_weapon = weapon
        self._show_skins()
