"""统一主题：配色、字体与 ttk 样式（浅色现代主题）"""
import tkinter as tk
from tkinter import ttk

FONT = "Microsoft YaHei UI"

# ── 配色 ──
BG = "#f5f6f8"          # 窗口背景
CARD = "#ffffff"        # 卡片背景
BORDER = "#e4e6ea"      # 细边框
TEXT = "#1f2329"        # 主文字
MUTED = "#6b7280"       # 次要文字
FAINT = "#9ca3af"       # 弱化文字
ACCENT = "#2563eb"      # 主色（蓝）
ACCENT_HOVER = "#1d4ed8"
ACCENT_BG = "#eef3ff"   # 主色浅底
GREEN = "#16a34a"
RED = "#dc2626"
HEADER_BG = "#f7f8fa"

# ── 字号（配合 DPI 感知，按真实点渲染）──
TITLE = 18
SUBTITLE = 11
BODY = 11
SMALL = 10
TINY = 9
RESULT = 12


def apply_style(root):
    """配置 ttk 现代浅色主题。"""
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    style.configure(".", font=(FONT, BODY), background=BG, foreground=TEXT)

    # 普通按钮
    style.configure("TButton", font=(FONT, SMALL), padding=(14, 7),
                    background="#ffffff", foreground=TEXT, borderwidth=0,
                    relief="flat", focuscolor="")
    style.map("TButton",
              background=[("active", "#e8eaed"), ("pressed", "#dde1e6")])

    # 主按钮（强调）
    style.configure("Accent.TButton", font=(FONT, SMALL), padding=(18, 8),
                    background=ACCENT, foreground="#ffffff", borderwidth=0,
                    relief="flat", focuscolor="")
    style.map("Accent.TButton",
              background=[("active", ACCENT_HOVER), ("pressed", ACCENT_HOVER)])

    # 次要按钮
    style.configure("Ghost.TButton", font=(FONT, SMALL), padding=(12, 6),
                    background=BG, foreground=MUTED, borderwidth=0, relief="flat",
                    focuscolor="")
    style.map("Ghost.TButton", background=[("active", "#e8eaed")])

    # 复选/单选（根背景）
    for base in ("TCheckbutton", "TRadiobutton"):
        style.configure(base, background=BG, foreground=TEXT, font=(FONT, BODY))
        style.map(base, background=[("active", BG)],
                  indicatorcolor=[("selected", ACCENT), ("!selected", "#b6bcc6")])

    # 卡片内的复选/单选
    style.configure("Card.TCheckbutton", background=CARD, foreground=TEXT,
                    font=(FONT, BODY))
    style.map("Card.TCheckbutton", background=[("active", CARD)],
              indicatorcolor=[("selected", ACCENT), ("!selected", "#b6bcc6")])
    style.configure("Card.TRadiobutton", background=CARD, foreground=TEXT,
                    font=(FONT, BODY))
    style.map("Card.TRadiobutton", background=[("active", CARD)],
              indicatorcolor=[("selected", ACCENT), ("!selected", "#b6bcc6")])

    # 组合框
    style.configure("TCombobox", padding=(10, 5), fieldbackground="#ffffff",
                    background="#ffffff", foreground=TEXT, font=(FONT, BODY),
                    arrowsize=14, bordercolor=BORDER, lightcolor=BORDER,
                    darkcolor=BORDER)
    style.map("TCombobox", fieldbackground=[("readonly", "#ffffff")],
              selectbackground=[("readonly", "#ffffff")],
              selectforeground=[("readonly", TEXT)])
