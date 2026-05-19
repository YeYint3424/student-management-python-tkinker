# widgets.py
import customtkinter as ctk
from config import CARD2, BORDER, TEXT, SUBTEXT, PRIMARY, PRIMARY_H, BG_DARK


class StyledEntry(ctk.CTkEntry):
    def __init__(self, master, placeholder="", show="", **kw):
        super().__init__(master,
                         placeholder_text=placeholder,
                         show=show,
                         fg_color=CARD2,
                         border_color=BORDER,
                         text_color=TEXT,
                         placeholder_text_color=SUBTEXT,
                         height=38,
                         **kw)


class StyledButton(ctk.CTkButton):
    def __init__(self, master, text="", color=PRIMARY, hover=PRIMARY_H, **kw):
        super().__init__(master,
                         text=text,
                         fg_color=color,
                         hover_color=hover,
                         text_color=TEXT,
                         height=38,
                         corner_radius=8,
                         **kw)


class SectionLabel(ctk.CTkLabel):
    def __init__(self, master, text, **kw):
        super().__init__(master, text=text,
                         font=ctk.CTkFont(size=18, weight="bold"),
                         text_color=TEXT, **kw)


class ScrollablePage(ctk.CTkFrame):
    def __init__(self, master, **kw):
        super().__init__(master, fg_color="transparent", **kw)

        self._canvas = ctk.CTkCanvas(self, bg=BG_DARK, highlightthickness=0)
        self._scrollbar = ctk.CTkScrollbar(self, command=self._canvas.yview,
                                           fg_color=CARD2, button_color=BORDER,
                                           button_hover_color=PRIMARY)
        self._canvas.configure(yscrollcommand=self._scrollbar.set)

        self._scrollbar.pack(side="right", fill="y")
        self._canvas.pack(side="left", fill="both", expand=True)

        self.inner = ctk.CTkFrame(self._canvas, fg_color="transparent")
        self._window_id = self._canvas.create_window((0, 0), window=self.inner, anchor="nw")

        self.inner.bind("<Configure>", self._on_inner_configure)
        self._canvas.bind("<Configure>", self._on_canvas_configure)

        self._canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self._canvas.bind_all("<Button-4>", self._on_mousewheel)
        self._canvas.bind_all("<Button-5>", self._on_mousewheel)

    def _on_inner_configure(self, _event):
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self._canvas.itemconfig(self._window_id, width=event.width)

    def _on_mousewheel(self, event):
        if not self.winfo_ismapped():
            return
        if event.num == 4:
            self._canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self._canvas.yview_scroll(1, "units")
        else:
            self._canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def scroll_to_top(self):
        self._canvas.yview_moveto(0)