import io
import threading
import tkinter as tk

import requests
from PIL import Image, ImageTk

from api import cache_img
from config import (
    ACCENT, BG, BG2, BORDER, CARD, CARD_H, MUTED, TEXT,
    FONT_SMALL,
)

IMG_CACHE: dict[str, ImageTk.PhotoImage] = {}


def load_image(url: str, size: tuple = (80, 60)) -> ImageTk.PhotoImage | None:
    key = f"{url}_{size}"
    if key in IMG_CACHE:
        return IMG_CACHE[key]
    try:
        path = cache_img(url)
        if path:
            img = Image.open(path).convert("RGBA")
        else:
            r = requests.get(url, timeout=8)
            img = Image.open(io.BytesIO(r.content)).convert("RGBA")
        img.thumbnail(size, Image.LANCZOS)
        bg = Image.new("RGBA", size, (13, 15, 20, 0))
        offset = ((size[0] - img.width) // 2, (size[1] - img.height) // 2)
        bg.paste(img, offset, img)
        tk_img = ImageTk.PhotoImage(bg)
        IMG_CACHE[key] = tk_img
        return tk_img
    except Exception:
        return None


def load_image_from_path(path: str, size: tuple = (80, 60)) -> ImageTk.PhotoImage | None:
    """Charge une image depuis un chemin JPEG local (cache disque), sans appel réseau."""
    key = f"local:{path}_{size}"
    if key in IMG_CACHE:
        return IMG_CACHE[key]
    try:
        img = Image.open(path).convert("RGB")
        img.thumbnail(size, Image.LANCZOS)
        canvas = Image.new("RGB", size, (30, 34, 48))
        offset = ((size[0] - img.width) // 2, (size[1] - img.height) // 2)
        canvas.paste(img, offset)
        tk_img = ImageTk.PhotoImage(canvas)
        IMG_CACHE[key] = tk_img
        return tk_img
    except Exception:
        return None


class ScrollFrame(tk.Frame):
    def __init__(self, parent, **kw):
        super().__init__(parent, bg=BG, **kw)
        self.canvas = tk.Canvas(self, bg=BG, bd=0, highlightthickness=0)
        self.vsb    = tk.Scrollbar(self, orient="vertical",
                                   command=self.canvas.yview,
                                   bg=BG2, troughcolor=BG2)
        self.vsb.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.canvas.configure(yscrollcommand=self.vsb.set)
        self.inner = tk.Frame(self.canvas, bg=BG)
        self._win  = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.inner.bind("<Configure>",
                        lambda e: self.canvas.configure(
                            scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>",
                         lambda e: self.canvas.itemconfig(self._win, width=e.width))
        self.canvas.bind_all("<MouseWheel>",
                             lambda e: self.canvas.yview_scroll(
                                 -1 * (e.delta // 120), "units"))


def grid_card_size(n: int, avail_w: int, pad: int = 10,
                   min_w: int = 130, max_w: int = 250) -> tuple[int, int, int]:
    """Calcule (cols, card_w, card_h) adaptatif au nombre d'items et à la largeur."""
    avail_w = max(avail_w, 300)
    n = max(n, 1)
    for cols in range(min(n, 10), 0, -1):
        cw = (avail_w - pad * (cols + 1)) / cols
        if cw >= min_w:
            cw = min(int(cw), max_w)
            return cols, cw, int(cw * 0.85)
    cw = min(avail_w - pad * 2, max_w)
    return 1, cw, int(cw * 0.85)


class SkinCard(tk.Canvas):
    """Card de skin avec coins arrondis (Canvas), taille adaptative."""

    _RADIUS = 12

    def __init__(self, parent, name: str, img_url: str = "", img_path: str = "",
                 callback=None, card_w=148, card_h=130, img_size=(115, 80),
                 subtitle: str = "", **kw):
        try:
            bg_p = parent.cget("bg")
        except Exception:
            bg_p = BG
        super().__init__(parent, width=card_w, height=card_h,
                         highlightthickness=0, bd=0, bg=bg_p,
                         cursor="hand2", **kw)
        self._cw       = card_w
        self._ch       = card_h
        self._cb       = callback
        self._name     = name
        self._subtitle = subtitle
        self._img_url  = img_url
        self._img_path = img_path
        self._isize    = img_size
        self._hovered  = False
        self._tk_img   = None
        self._loading  = False

        self.bind("<Button-1>", lambda e: self._cb() if self._cb else None)
        self.bind("<Enter>",    lambda e: self._on_hover(True))
        self.bind("<Leave>",    lambda e: self._on_hover(False))
        # Diffère le dessin jusqu'à ce que le widget existe dans Tcl/Tk
        self.after_idle(self._draw)

    # ── Dessin ────────────────────────────────────────────────────────────────

    def _poly_round_rect(self, x1: int, y1: int, x2: int, y2: int, r: int, **kw):
        pts = [x1 + r, y1,  x2 - r, y1,
               x2,     y1,  x2,     y1 + r,
               x2,     y2 - r,  x2, y2,
               x2 - r, y2,  x1 + r, y2,
               x1,     y2,  x1,     y2 - r,
               x1,     y1 + r,  x1, y1]
        return self.create_polygon(pts, smooth=True, **kw)

    def _draw(self):
        try:
            self.delete("all")
        except tk.TclError:
            return
        bg  = CARD_H if self._hovered else CARD
        bdr = ACCENT  if self._hovered else BORDER
        lw  = 2 if self._hovered else 1
        cw, ch = self._cw, self._ch

        self._poly_round_rect(1, 1, cw - 1, ch - 1, self._RADIUS,
                              fill=bg, outline=bdr, width=lw)

        has_sub = bool(self._subtitle)
        img_cy = int(ch * (0.38 if has_sub else 0.42))
        if self._tk_img:
            self.create_image(cw // 2, img_cy, image=self._tk_img, anchor="center")
        else:
            self.create_text(cw // 2, img_cy, text="·",
                             font=("Segoe UI", 14), fill=MUTED)

        label = self._name if len(self._name) <= 20 else self._name[:18] + "…"
        if has_sub:
            self.create_text(cw // 2, ch - 22, text=label,
                             font=("Segoe UI", 8), fill=TEXT,
                             anchor="center", width=cw - 12)
            self.create_text(cw // 2, ch - 9, text=self._subtitle,
                             font=("Segoe UI", 8, "bold"), fill=ACCENT,
                             anchor="center", width=cw - 12)
        else:
            self.create_text(cw // 2, ch - 14, text=label,
                             font=("Segoe UI", 8), fill=TEXT,
                             anchor="center", width=cw - 12)

        # Chargement image (une seule fois)
        if not self._loading:
            self._loading = True
            if self._img_path:
                threading.Thread(target=self._do_load_path, daemon=True).start()
            elif self._img_url:
                threading.Thread(target=self._do_load_url, daemon=True).start()

    def _do_load_path(self):
        img = load_image_from_path(self._img_path, self._isize)
        if img:
            self._tk_img = img
            try:
                self.after(0, self._draw)
            except Exception:
                pass

    def _do_load_url(self):
        img = load_image(self._img_url, self._isize)
        if img:
            self._tk_img = img
            try:
                self.after(0, self._draw)
            except Exception:
                pass

    def _on_hover(self, on: bool):
        self._hovered = on
        try:
            self._draw()
        except Exception:
            pass


class CategoryCard(tk.Frame):
    """Card de catégorie Frame-based avec effet hover ACCENT."""

    def __init__(self, parent, title: str, icon: str, count: int,
                 callback, w: int = 210, h: int = 150,
                 subtitle: str = "", **kwargs):
        super().__init__(
            parent, bg=CARD, cursor="hand2",
            highlightbackground=BORDER, highlightthickness=1,
            **kwargs,
        )

        self._cb = callback

        # Contenu centré
        inner = tk.Frame(self, bg=CARD)
        inner.place(relx=0.5, rely=0.5, anchor="center")

        self._icon_lbl = tk.Label(inner, text=icon,
                                   font=("Segoe UI", 30), bg=CARD, fg=TEXT)
        self._icon_lbl.pack()
        self._title_lbl = tk.Label(inner, text=title,
                                    font=("Segoe UI", 11, "bold"), bg=CARD, fg=TEXT)
        self._title_lbl.pack(pady=(6, 0))
        self._count_lbl = tk.Label(inner,
                                    text=subtitle if subtitle else (f"{count} armes" if count >= 0 else ""),
                                    font=("Segoe UI", 9), bg=CARD, fg=MUTED)
        self._count_lbl.pack(pady=(2, 0))

        # Taille fixe
        self.config(width=w, height=h)
        self.pack_propagate(False)

        # Bind hover sur tous les enfants
        for widget in (self, inner, self._icon_lbl, self._title_lbl, self._count_lbl):
            widget.bind("<Button-1>", lambda e: callback())
            widget.bind("<Enter>",    lambda e: self._hover(True))
            widget.bind("<Leave>",    lambda e: self._hover(False))

    def _hover(self, on: bool):
        bg  = CARD_H if on else CARD
        fg  = ACCENT if on else TEXT
        bdr = ACCENT if on else BORDER
        self.config(bg=bg, highlightbackground=bdr,
                    highlightthickness=2 if on else 1)
        for child in self.winfo_children():
            try:
                child.config(bg=bg)
            except Exception:
                pass
        self._icon_lbl.config(fg=fg)
        self._title_lbl.config(fg=TEXT)
        self._count_lbl.config(fg=MUTED)
