import io
import threading
import tkinter as tk

import requests
from PIL import Image, ImageTk

from config import (
    BG, BG2, CARD, CARD_H, MUTED, TEXT,
    FONT_SMALL,
)

IMG_CACHE: dict[str, ImageTk.PhotoImage] = {}


def load_image(url: str, size: tuple = (80, 60)) -> ImageTk.PhotoImage | None:
    key = f"{url}_{size}"
    if key in IMG_CACHE:
        return IMG_CACHE[key]
    try:
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
    def __init__(self, parent, name: str, img_url: str, callback,
                 card_w=120, card_h=110, img_size=(90, 68), **kw):
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
            w.bind("<Button-1>", lambda e: self._cb())
            w.bind("<Enter>",    lambda e: self._hover(True))
            w.bind("<Leave>",    lambda e: self._hover(False))

        if img_url:
            threading.Thread(
                target=self._load_img, args=(img_url, img_size), daemon=True
            ).start()

    def _load_img(self, url: str, size: tuple):
        img = load_image(url, size)
        if img:
            self._img_lbl.after(0, self.set_image, img)

    def _hover(self, on: bool):
        c = CARD_H if on else CARD
        for w in (self, self._img_lbl, self._name):
            w.config(bg=c)

    def set_image(self, tk_img: ImageTk.PhotoImage):
        self._img_lbl.config(image=tk_img, text="", bg=CARD)
        self._img_lbl.image = tk_img
