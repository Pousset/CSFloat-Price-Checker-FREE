"""Mixin - Ecran 2 : grille de selection des skins."""
import tkinter as tk

from api import get_img_path_by_name
from config import ACCENT, BG, BG3, BORDER, FONT_BODY, FONT_HEAD, MUTED, TEXT
from widgets import ScrollFrame, SkinCard, grid_card_size


class SkinsViewMixin:
    def _show_skins(self):
        self._update_breadcrumb(section=self.sel_section, weapon=self.sel_weapon)
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
        self._skins_inner  = sf.inner
        self._skins_canvas = sf.canvas
        self._last_skins_w = 0

        self._skin_search.trace_add("write", lambda *_: self._refresh_skins_grid())
        sf.canvas.bind("<Configure>",
                       lambda e: self._on_skins_canvas_resize(e.width))
        sf.canvas.after_idle(
            lambda: self._refresh_skins_grid(self._skins_canvas.winfo_width()))

    def _on_skins_canvas_resize(self, width: int):
        if abs(width - self._last_skins_w) >= 20:
            self._refresh_skins_grid(width)

    def _refresh_skins_grid(self, avail_w: int = 0):
        if avail_w == 0:
            avail_w = self._skins_canvas.winfo_width()
        self._last_skins_w = avail_w

        # Supprimer uniquement le grid existant (pas le header/searchbar)
        for child in self._skins_inner.winfo_children():
            if getattr(child, "_is_skins_grid", False):
                child.destroy()

        q = self._skin_search.get().lower()
        skins = [s for s in self._all_skins
                 if q in s.get("name", "").lower()] if q else self._all_skins

        if not skins:
            lbl = tk.Label(self._skins_inner, text="Aucun skin trouvé",
                           font=FONT_BODY, bg=BG, fg=MUTED)
            lbl._is_skins_grid = True
            lbl.pack(pady=20)
            return

        cols, card_w, card_h = grid_card_size(
            len(skins), avail_w, pad=10, min_w=120, max_w=240)
        img_w = int(card_w * 0.78)
        img_h = int(card_h * 0.62)

        grid = tk.Frame(self._skins_inner, bg=BG)
        grid._is_skins_grid = True
        grid.pack(fill="x", padx=5, pady=5)

        for i, skin in enumerate(skins):
            parts     = skin.get("name", "").split(" | ")
            skin_name = parts[1] if len(parts) > 1 else skin.get("name", "")
            img_path  = get_img_path_by_name(skin.get("name", ""))
            img_url   = "" if img_path else skin.get("image", "")
            row, col  = divmod(i, cols)
            SkinCard(grid, name=skin_name,
                     img_url=img_url, img_path=img_path or "",
                     callback=lambda s=skin: self._select_skin(s),
                     card_w=card_w, card_h=card_h, img_size=(img_w, img_h),
                     ).grid(row=row, column=col, padx=5, pady=5, sticky="nsew")

        for c in range(cols):
            grid.columnconfigure(c, weight=1)

    def _select_skin(self, skin):
        self.sel_skin = skin
        self._show_quality_picker()
