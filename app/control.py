"""主控制窗口：开关、方向、引擎、手动翻译（现代浅色主题）"""
import os
import tkinter as tk
from tkinter import ttk

from .config import CONFIG_PATH, save as save_config
from . import config as config_mod
from . import theme

ENGINE_CHOICES = [
    ("自动（依次尝试）", "auto"),
    ("DeepL 翻译（需注册 key）", "deepl"),
    ("百度翻译（需配置密钥）", "baidu"),
    ("Google 翻译", "google"),
    ("MyMemory 翻译", "mymemory"),
]

DIRS = [("auto", "自动检测 · 中⇄英"), ("zh2en", "中 → 英"), ("en2zh", "英 → 中")]


class ControlWindow:
    def __init__(self, root, cfg, app):
        self.root = root
        self.cfg = cfg
        self.app = app

        theme.apply_style(root)
        root.configure(bg=theme.BG)
        root.title("划词翻译 · 中英互译")
        root.geometry("700x760")
        root.minsize(660, 700)

        self._build()

    # ── 构建 UI ──
    def _card(self, parent):
        return tk.Frame(parent, bg=theme.CARD,
                        highlightbackground=theme.BORDER, highlightthickness=1)

    def _build(self):
        root = self.root

        # 标题区
        header = tk.Frame(root, bg=theme.BG)
        header.pack(fill="x", padx=28, pady=(22, 10))
        left = tk.Frame(header, bg=theme.BG)
        left.pack(side="left")
        tk.Label(left, text="划词翻译", font=(theme.FONT, theme.TITLE, "bold"),
                 bg=theme.BG, fg=theme.TEXT).pack(anchor="w")
        tk.Label(left, text="中英互译 · 选中即译，光标旁弹窗",
                 font=(theme.FONT, theme.SUBTITLE), bg=theme.BG,
                 fg=theme.MUTED).pack(anchor="w")
        self.badge = tk.Label(header, text="", font=(theme.FONT, theme.SMALL),
                              padx=14, pady=5)
        self.badge.pack(side="right", anchor="n")

        body = tk.Frame(root, bg=theme.BG)
        body.pack(fill="both", expand=True, padx=28, pady=(0, 12))

        # 卡片 1：划词即译（拖选即翻译，无需 Ctrl+C）
        card = self._card(body)
        card.pack(fill="x", pady=6)
        inner = tk.Frame(card, bg=theme.CARD)
        inner.pack(fill="x", padx=18, pady=14)
        self.select_var = tk.BooleanVar(value=bool(self.cfg.get("select_translate", False)))
        ttk.Checkbutton(inner, text="划词即译（选中文字自动翻译，无需 Ctrl+C）",
                        variable=self.select_var, command=self._on_select_toggle,
                        style="Card.TCheckbutton").pack(side="left")
        tk.Label(inner, text="开启后，鼠标拖选文字松开即翻译", bg=theme.CARD,
                 fg=theme.FAINT, font=(theme.FONT, theme.TINY)).pack(side="right")

        # 卡片 2：自动翻译
        card = self._card(body)
        card.pack(fill="x", pady=6)
        inner = tk.Frame(card, bg=theme.CARD)
        inner.pack(fill="x", padx=18, pady=14)
        self.auto_var = tk.BooleanVar(value=bool(self.cfg.get("auto_translate", True)))
        ttk.Checkbutton(inner, text="自动翻译复制/选中的文字", variable=self.auto_var,
                        command=self._on_auto, style="Card.TCheckbutton").pack(side="left")
        tk.Label(inner, text="选中文字后 Ctrl+C 即弹翻译", bg=theme.CARD,
                 fg=theme.FAINT, font=(theme.FONT, theme.TINY)).pack(side="right")

        # 卡片 2：翻译方向
        card = self._card(body)
        card.pack(fill="x", pady=6)
        inner = tk.Frame(card, bg=theme.CARD)
        inner.pack(fill="x", padx=18, pady=14)
        tk.Label(inner, text="翻译方向", bg=theme.CARD, fg=theme.TEXT,
                 font=(theme.FONT, theme.BODY, "bold")).pack(side="left", padx=(0, 18))
        self.dir_var = tk.StringVar(value=self.cfg.get("direction", "auto"))
        for val, label in DIRS:
            ttk.Radiobutton(inner, text=label, value=val, variable=self.dir_var,
                            command=self._on_dir,
                            style="Card.TRadiobutton").pack(side="left", padx=10)

        # 卡片 3：首选引擎
        card = self._card(body)
        card.pack(fill="x", pady=6)
        inner = tk.Frame(card, bg=theme.CARD)
        inner.pack(fill="x", padx=18, pady=14)
        tk.Label(inner, text="首选引擎", bg=theme.CARD, fg=theme.TEXT,
                 font=(theme.FONT, theme.BODY, "bold")).pack(side="left", padx=(0, 18))
        self.engine_combo = ttk.Combobox(inner, state="readonly", width=24,
                                         values=[c[0] for c in ENGINE_CHOICES])
        self.engine_combo.pack(side="left")
        try:
            idx = [c[1] for c in ENGINE_CHOICES].index(self.cfg.get("primary_engine", "auto"))
        except ValueError:
            idx = 0
        self.engine_combo.current(idx)
        self.engine_combo.bind("<<ComboboxSelected>>", self._on_engine)
        tk.Label(inner, text="失败自动切换下一个", bg=theme.CARD,
                 fg=theme.FAINT, font=(theme.FONT, theme.TINY)).pack(side="left", padx=10)

        # 使用提示
        tip = "使用：任意软件选中文字 → Ctrl+C（或直接按 {h}）；{t} 开关自动翻译。".format(
            h=self.cfg.get("hotkey_translate", "f8").upper(),
            t=self.cfg.get("hotkey_toggle", "f9").upper())
        tk.Label(body, text=tip, bg=theme.BG, fg=theme.MUTED,
                 font=(theme.FONT, theme.SMALL), anchor="w").pack(fill="x", pady=(4, 2))

        # 卡片 4：手动翻译
        card = self._card(body)
        card.pack(fill="both", expand=True, pady=6)
        inner = tk.Frame(card, bg=theme.CARD)
        inner.pack(fill="both", expand=True, padx=18, pady=14)
        inner.columnconfigure(0, weight=1)
        inner.rowconfigure(3, weight=1)

        tk.Label(inner, text="手动翻译", bg=theme.CARD, fg=theme.TEXT,
                 font=(theme.FONT, theme.BODY, "bold")).grid(row=0, column=0, sticky="w")

        self.input_text = tk.Text(inner, height=4, wrap="word", font=(theme.FONT, theme.BODY),
                                  relief="solid", bd=1, highlightthickness=0,
                                  highlightbackground=theme.BORDER, highlightcolor=theme.ACCENT,
                                  bg="#fbfcfd", fg=theme.TEXT, insertbackground=theme.TEXT,
                                  padx=10, pady=8)
        self.input_text.grid(row=1, column=0, sticky="ew", pady=(10, 6))
        self.input_text.bind("<Control-Return>", lambda e: self._on_manual())

        btns = tk.Frame(inner, bg=theme.CARD)
        btns.grid(row=2, column=0, sticky="ew", pady=4)
        ttk.Button(btns, text="翻译　Ctrl+Enter", command=self._on_manual,
                   style="Accent.TButton").pack(side="left")
        ttk.Button(btns, text="清空", command=self._on_clear,
                   style="Ghost.TButton").pack(side="left", padx=8)
        self.copy_btn = ttk.Button(btns, text="复制译文", command=self._copy_output,
                                   style="Ghost.TButton", state="disabled")
        self.copy_btn.pack(side="right")

        self.output_text = tk.Text(inner, height=8, wrap="word",
                                   font=(theme.FONT, theme.RESULT), relief="solid", bd=1,
                                   highlightthickness=0, highlightbackground=theme.BORDER,
                                   highlightcolor=theme.ACCENT, bg="#fbfcfd", fg=theme.TEXT,
                                   padx=12, pady=10)
        self.output_text.grid(row=3, column=0, sticky="nsew")
        self.output_text.insert("1.0", "翻译结果将显示在这里")
        self.output_text.config(state="disabled")

        # 底部状态栏
        bottom = tk.Frame(root, bg=theme.BG)
        bottom.pack(fill="x", padx=28, pady=(0, 16))
        self._dot = tk.Label(bottom, text="●", bg=theme.BG, fg=theme.GREEN,
                             font=(theme.FONT, theme.BODY))
        self._dot.pack(side="left")
        self.status_var = tk.StringVar(value="就绪")
        tk.Label(bottom, textvariable=self.status_var, bg=theme.BG, fg=theme.MUTED,
                 font=(theme.FONT, theme.SMALL)).pack(side="left", padx=(6, 0))
        ttk.Button(bottom, text="编辑术语表", command=self._edit_glossary,
                   style="Ghost.TButton").pack(side="right", padx=6)
        ttk.Button(bottom, text="打开配置", command=self._open_config,
                   style="Ghost.TButton").pack(side="right")
        ttk.Button(bottom, text="帮助", command=self._open_readme,
                   style="Ghost.TButton").pack(side="right", padx=6)
        ttk.Button(bottom, text="退出", command=self.app.on_close,
                   style="Ghost.TButton").pack(side="right")

        self._update_badge()

    # ── 回调 ──
    def _on_select_toggle(self):
        self.app.set_select_translate(self.select_var.get())

    def _on_auto(self):
        self.app.set_auto(self.auto_var.get())
        self._update_badge()

    def _update_badge(self):
        on = self.auto_var.get()
        if on:
            self.badge.config(text="● 自动翻译已开启", bg=theme.ACCENT_BG, fg=theme.ACCENT)
        else:
            self.badge.config(text="● 自动翻译已关闭", bg="#eef0f2", fg=theme.MUTED)

    def _on_dir(self):
        self.cfg["direction"] = self.dir_var.get()
        save_config(self.cfg)

    def _on_engine(self, event=None):
        idx = self.engine_combo.current()
        self.cfg["primary_engine"] = ENGINE_CHOICES[idx][1]
        save_config(self.cfg)
        self.app.rebuild_chain()

    def _on_manual(self):
        text = self.input_text.get("1.0", "end-1c").strip()
        if not text:
            self.set_status("请先输入要翻译的文字")
            return
        self.app.translate(text, source="manual")

    def _on_clear(self):
        self.input_text.delete("1.0", "end")
        self.show_result("翻译结果将显示在这里")
        self.copy_btn.config(state="disabled")

    def _copy_output(self):
        text = self.output_text.get("1.0", "end-1c").strip()
        if not text:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.app.on_self_copy(text)
        self.set_status("译文已复制")

    def _open_config(self):
        save_config(self.cfg)  # 确保文件存在
        os.startfile(CONFIG_PATH)

    def _open_readme(self):
        path = os.path.join(config_mod.APP_DIR, "README.md")
        if os.path.exists(path):
            os.startfile(path)

    def _edit_glossary(self):
        from . import glossary
        path = self.cfg.get("glossary_path") or glossary.default_path()
        path = glossary.ensure_example(path)
        os.startfile(path)
        self.set_status("术语表已打开（保存后立即生效）")

    # ── 外部调用 ──
    def toggle_auto(self):
        self.auto_var.set(not self.auto_var.get())
        self._on_auto()

    def set_status(self, text):
        self.status_var.set(text)

    def show_result(self, text):
        self.output_text.config(state="normal")
        self.output_text.delete("1.0", "end")
        self.output_text.insert("1.0", text)
        self.output_text.config(state="disabled")
        self.copy_btn.config(state="normal")
