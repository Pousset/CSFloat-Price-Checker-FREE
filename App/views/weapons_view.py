"""Mixin - Ecran 1 : sélection par sections (onglets) puis armes."""
import tkinter as tk

from api import get_img_path_by_name
from config import (
    ACCENT, BG, BG2, BG3, BORDER, CARD, CARD_H,
    FONT_BODY, FONT_SMALL, MUTED, SECTION_ORDER, TEXT,
)
from widgets import ScrollFrame, SkinCard


class WeaponsViewMixin:
    # ── Écran principal : onglets ──────────────────────────────────────────────

    def _show_weapons(self):
        self.sel_weapon = ""
        self._update_breadcrumb()

        outer = tk.Frame(self.main_area, bg=BG)
        self._swap(outer)

        # ── Barre d'onglets ──────────────────────────────────────────────────
        tabs_frame = tk.Frame(outer, bg=BG2, padx=16, pady=0)
        tabs_frame.pack(fill="x")

        self._tab_buttons: dict[str, tk.Label] = {}
        for section in SECTION_ORDER:
            if not self.category_weapons_map.get(section):
                continue
            btn = tk.Label(
                tabs_frame, text=section, font=FONT_SMALL,
                bg=BG2, fg=MUTED, cursor="hand2",
                padx=14, pady=10,
            )
            btn.pack(side="left")
            btn.bind("<Button-1>", lambda e, s=section: self._select_section(s))
            btn.bind("<Enter>", lambda e, b=btn: b.config(fg=TEXT) if b.cget("bg") == BG2 else None)
            btn.bind("<Leave>", lambda e, b=btn: b.config(fg=MUTED) if b.cget("bg") == BG2 else None)
            self._tab_buttons[section] = btn

        tk.Frame(outer, bg=BORDER, height=1).pack(fill="x")

        # ── Zone de contenu ──────────────────────────────────────────────────
        self._cat_content = tk.Frame(outer, bg=BG)
        self._cat_content.pack(fill="both", expand=True)

        # Activer la section mémorisée ou la première disponible
        target = (self.sel_section
                  if self.sel_section in self._tab_buttons
                  else next((s for s in SECTION_ORDER
                             if self.category_weapons_map.get(s)), None))
        if target:
            self._select_section(target)

    # ── Sélection d'une section ───────────────────────────────────────────────

    def _select_section(self, section: str):
        self.sel_section = section
        self._update_breadcrumb(section=section)

        # Mettre à jour l'apparence des onglets
        for s, btn in self._tab_buttons.items():
            if s == section:
                btn.config(bg=ACCENT, fg=BG)
            else:
                btn.config(bg=BG2, fg=MUTED)

        # Vider et remplir la zone de contenu
        for w in self._cat_content.winfo_children():
            w.destroy()

        weapons = self.category_weapons_map.get(section, [])
        if not weapons:
            tk.Label(self._cat_content, text="Aucune arme disponible",
                     font=FONT_BODY, bg=BG, fg=MUTED).pack(pady=40)
            return

        # ── Recherche ────────────────────────────────────────────────────────
        search_bar = tk.Frame(self._cat_content, bg=BG, padx=20, pady=8)
        search_bar.pack(fill="x")
        self._weapon_search = tk.StringVar()
        tk.Entry(
            search_bar, textvariable=self._weapon_search,
            bg=BG3, fg=TEXT, insertbackground=ACCENT, font=FONT_BODY,
            bd=0, width=28, highlightthickness=1, highlightbackground=BORDER,
        ).pack(side="left", ipady=4)
        tk.Label(search_bar, text=f"{len(weapons)} armes",
                 font=FONT_SMALL, bg=BG, fg=MUTED).pack(side="left", padx=10)

        # ── Grille scrollable ────────────────────────────────────────────────
        sf = ScrollFrame(self._cat_content)
        sf.pack(fill="both", expand=True)
        self._weapons_grid = tk.Frame(sf.inner, bg=BG, padx=20)
        self._weapons_grid.pack(fill="both", pady=10)

        self._current_weapons = weapons
        self._weapon_search.trace_add(
            "write", lambda *_: self._refresh_section_grid()
        )
        self._refresh_section_grid()

    # ── Grille d'armes ────────────────────────────────────────────────────────

    def _refresh_section_grid(self):
        for w in self._weapons_grid.winfo_children():
            w.destroy()
        q = self._weapon_search.get().lower()
        weapons = [w for w in self._current_weapons if q in w.lower()] if q else self._current_weapons
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
