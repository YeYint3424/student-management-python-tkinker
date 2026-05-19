# utils.py
import hashlib


def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()


def styled_table(parent, columns, col_widths=None):
    from tkinter import ttk
    import customtkinter as ctk
    from config import CARD, TEXT, CARD2, SUBTEXT, PRIMARY, BORDER

    style = ttk.Style()
    style.theme_use("default")
    style.configure("SMS.Treeview",
                    background=CARD, foreground=TEXT,
                    fieldbackground=CARD, rowheight=32,
                    borderwidth=0, font=("Segoe UI", 10))
    style.configure("SMS.Treeview.Heading",
                    background=CARD2, foreground=SUBTEXT,
                    font=("Segoe UI", 10, "bold"), relief="flat")
    style.map("SMS.Treeview",
              background=[("selected", PRIMARY)],
              foreground=[("selected", TEXT)])

    tree = ttk.Treeview(parent, columns=columns, show="headings",
                        style="SMS.Treeview")
    for i, col in enumerate(columns):
        w = (col_widths[i] if col_widths else 120)
        tree.heading(col, text=col)
        tree.column(col, width=w, anchor="center")

    sb = ctk.CTkScrollbar(parent, command=tree.yview,
                          fg_color=CARD, button_color=BORDER,
                          button_hover_color=PRIMARY)
    tree.configure(yscrollcommand=sb.set)
    return tree, sb