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


class SkinCard(tk.Frame):
    def __init__(self, parent, name: str, img_url: str = "", img_path: str = "",
                 callback=None, card_w=120, card_h=110, img_size=(90, 68), **kw):
        super().__init__(parent, bg=CARD, width=card_w, height=card_h,
                         cursor="hand2", **kw)
        self.pack_propagate(False)
        self._cb = callback

        self._img_lbl = tk.Label(self, bg=CARD, text="…", fg=MUTED, font=FONT_SMALL)
        self._img_lbl.pack(expand=True)

        label_text = name if len(name) <= 18 else name[:16] + "…"
        self._name = tk.Label(self, text=label_text, bg=CARD, fg=TEXT,
                              font=FONT_SMALL, wraplength=card_w - 8)
        self._name.pack(pady=(0, 4))

        for w in (self, self._img_lbl, self._name):
            w.bind("<Button-1>", lambda e: self._cb() if self._cb else None)
            w.bind("<Enter>",    lambda e: self._hover(True))
            w.bind("<Leave>",    lambda e: self._hover(False))

        if img_path:
            threading.Thread(
                target=self._load_img_path, args=(img_path, img_size), daemon=True
            ).start()
        elif img_url:
            threading.Thread(
                target=self._load_img, args=(img_url, img_size), daemon=True
            ).start()

    def _load_img(self, url: str, size: tuple):
        img = load_image(url, size)
        if img:
            self._img_lbl.after(0, self.set_image, img)

    def _load_img_path(self, path: str, size: tuple):
        img = load_image_from_path(path, size)
        if img:
            self._img_lbl.after(0, self.set_image, img)

    def _hover(self, on: bool):
        c = CARD_H if on else CARD
        for w in (self, self._img_lbl, self._name):
            w.config(bg=c)

    def set_image(self, tk_img: ImageTk.PhotoImage):
        self._img_lbl.config(image=tk_img, text="", bg=CARD)
        self._img_lbl.image = tk_img


class CategoryCard(tk.Frame):
    """Card de catégorie Frame-based avec effet hover ACCENT."""

    def __init__(self, parent, title: str, icon: str, count: int,
                 callback, w: int = 210, h: int = 150, **kwargs):
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
        self._count_lbl = tk.Label(inner, text=f"{count} armes",
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
