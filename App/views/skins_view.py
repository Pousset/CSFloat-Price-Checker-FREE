"""Mixin - Ecran 2 : grille de selection des skins."""
import tkinter as tk

from config import ACCENT, BG, BG3, BORDER, FONT_BODY, FONT_HEAD, MUTED, TEXT
from widgets import ScrollFrame, SkinCard


class SkinsViewMixin:
    def _show_skins(self):
        self._update_breadcrumb(weapon=self.sel_weapon)
        sf = ScrollFrame(self.main_area)
        self._swap(sf)
        tk.Label(sf.inner, text=f"Skins - {self.sel_weapon}", font=FONT_HEAD,
                 bg=BG, fg=MUTED, padx=20, pady=14).pack(anchor="w")
        bar = tk.Frame(sf.inner, bg=BG, padx=20)
        bar.pack(fill="x", pady=(0, 10))
        self._skin_search = tk.StringVar()
        tk.Entry(bar, textvariable=self._skin_search, bg=BG3, fg=TEXT,
                 insertbackground=ACCENT, font=FONT_BODY, bd=0, width=30,
                 highlightthickness=1, highlightbackground=BORDER
                 ).pack(side="left", ipady=5, padx=(0, 8))
        self._all_skins  = self.weapons_map.get(self.sel_weapon, [])
        self._skins_grid = tk.Frame(sf.inner, bg=BG, padx=20)
        self._skins_grid.pack(fill="both")
        self._skin_search.trace_add("write", lambda *_: self._refresh_skins_grid())
        self._refresh_skins_grid()

    def _refresh_skins_grid(self):
        for w in self._skins_grid.winfo_children():
            w.destroy()
        q = self._skin_search.get().lower()
        skins = [s for s in self._all_skins
                 if q in s.get("name", "").lower()] if q else self._all_skins
        for i, skin in enumerate(skins):
            parts     = skin.get("name", "").split(" | ")
            skin_name = parts[1] if len(parts) > 1 else skin.get("name", "")
            row, col  = divmod(i, 6)
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
