"""翻译结果悬浮窗：圆角卡片 + 阴影 + 彩色顶条，可拖拽调整大小，显示在选中文字附近"""
import ctypes
from ctypes import wintypes
import tkinter as tk

from . import theme

TRANSPARENT = "#ff00ff"   # 透明色 key（内容中不会出现此色）
SHADOW = 4
SHADOW_COLOR = "#dbe0e6"
RADIUS = 16
HEADER_H = 40
HEADER_TEXT = "#ffffff"   # 顶条方向文字
HEADER_ENGINE = "#dbeafe"  # 顶条引擎名
GRIP_COLOR = "#c3c8d0"    # 右下角调整手柄


class GUITHREADINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("hwndActive", wintypes.HWND),
        ("hwndFocus", wintypes.HWND),
        ("hwndCapture", wintypes.HWND),
        ("hwndMenuOwner", wintypes.HWND),
        ("hwndMoveSize", wintypes.HWND),
        ("hwndCaret", wintypes.HWND),
        ("rcCaret", wintypes.RECT),
    ]


def cursor_pos():
    pt = wintypes.POINT()
    ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y


def caret_pos():
    """当前输入光标（caret，即选中文字末尾）的屏幕坐标，失败返回 None。"""
    try:
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return None
        tid = user32.GetWindowThreadProcessId(hwnd, None)
        gti = GUITHREADINFO()
        gti.cbSize = ctypes.sizeof(gti)
        if not user32.GetGUIThreadInfo(tid, ctypes.byref(gti)):
            return None
        rc = gti.rcCaret
        if rc.left or rc.top or rc.right or rc.bottom:
            return rc.left, rc.top
    except Exception:
        pass
    return None


def _truncate(text, limit=160):
    return text[:limit] + "…" if len(text) > limit else text


def _round_rect(canvas, x1, y1, x2, y2, r, **kw):
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
           x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
           x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return canvas.create_polygon(pts, smooth=True, **kw)


def _top_round_rect(canvas, x1, y1, x2, y2, r, **kw):
    """顶部圆角、底部直角的矩形（用作卡片顶条）。"""
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
           x2, y2, x1, y2, x1, y1 + r, x1, y1]
    return canvas.create_polygon(pts, smooth=True, **kw)


class TranslatePopup:
    PAD = 18
    MIN_W = 320
    MAX_W = 900

    def __init__(self, root, timeout=0, on_copy=None):
        self.root = root
        self.timeout = timeout
        self.on_copy = on_copy
        self.win = None
        self.pinned = False
        self._timer = None
        self._result = ""
        self._source = ""
        self._header_color = theme.ACCENT
        self.card_w = 500
        self._total_h = 0
        self._grip = []
        self._resizing = False
        self._resize_start = None
        self.canvas = None
        self._dir_item = None
        self._engine_item = None
        self._src_item = None
        self._sep_item = None
        self._bar_item = None
        self._text_item = None
        self._btn_item = None
        self.text = None
        self._btn_frame = None
        self.copy_btn = None
        self.pin_btn = None

    # ── 生命周期 ──
    def show(self, source, pending="翻译中…"):
        self.close()
        self._source = _truncate(source)
        self.card_w = 500
        self._resizing = False
        self._resize_start = None

        win = tk.Toplevel(self.root)
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        try:
            win.attributes("-transparentcolor", TRANSPARENT)
        except tk.TclError:
            pass
        win.configure(bg=TRANSPARENT)
        self.win = win

        c = tk.Canvas(win, bg=TRANSPARENT, highlightthickness=0, bd=0)
        c.pack(fill="both", expand=True)
        self.canvas = c

        self._dir_item = c.create_text(self.PAD, HEADER_H // 2, anchor="w", text="",
                                       fill=HEADER_TEXT, font=(theme.FONT, theme.BODY, "bold"))
        self._engine_item = c.create_text(self.card_w - self.PAD, HEADER_H // 2, anchor="e",
                                          text="", fill=HEADER_ENGINE, font=(theme.FONT, theme.TINY))
        self._src_item = c.create_text(self.PAD, HEADER_H + 14, anchor="nw", text=self._source,
                                       fill=theme.MUTED, font=(theme.FONT, theme.SMALL),
                                       width=self.card_w - 2 * self.PAD)
        self._sep_item = c.create_line(self.PAD, 0, self.card_w - self.PAD, 0, fill=theme.BORDER)
        self._bar_item = c.create_line(self.PAD - 8, 0, self.PAD - 8, 0,
                                       fill=self._header_color, width=3)

        self.text = tk.Text(win, bg=theme.CARD, fg=theme.TEXT,
                            font=(theme.FONT, theme.RESULT), wrap="word", relief="flat",
                            bd=0, highlightthickness=0, cursor="arrow",
                            width=50, height=3, padx=0, pady=0)
        self.text.bind("<<Modified>>", self._restore_text)
        self._text_item = c.create_window(self.PAD, 0, anchor="nw", window=self.text,
                                          width=self.card_w - 2 * self.PAD)

        self._btn_frame = tk.Frame(win, bg=theme.CARD)
        self.copy_btn = self._mk_btn("📋 复制", self._copy, theme.ACCENT)
        self.copy_btn.pack(side="left")
        self.pin_btn = self._mk_btn("📌 固定", self._toggle_pin, theme.MUTED)
        self.pin_btn.pack(side="left", padx=4)
        self._mk_btn("✕", self.close, theme.MUTED).pack(side="right")
        self._btn_item = c.create_window(self.PAD, 0, anchor="nw", window=self._btn_frame)

        # 右下角调整手柄（三条斜线）
        self._grip = []
        for _ in range(3):
            self._grip.append(c.create_line(0, 0, 0, 0, fill=GRIP_COLOR, width=2))

        win.bind("<Escape>", self.close)
        win.bind("<FocusOut>", self._on_focus_out)
        c.bind("<ButtonPress-1>", self._on_press)
        c.bind("<B1-Motion>", self._on_drag)
        c.bind("<ButtonRelease-1>", self._on_release)

        self.set_result(pending, "", "")
        win.after(60, self._focus)
        if self.timeout > 0:
            self._timer = win.after(int(self.timeout * 1000), self.close)

    def close(self, event=None):
        if self._timer is not None:
            try:
                self.root.after_cancel(self._timer)
            except tk.TclError:
                pass
            self._timer = None
        if self.win is not None:
            try:
                self.win.destroy()
            except tk.TclError:
                pass
            self.win = None
        self.pinned = False
        self.text = None
        self.canvas = None
        self._btn_frame = None
        self._grip = []
        self._resizing = False

    # ── 内容 ──
    def set_result(self, result, engine="", direction=""):
        self._result = result
        self._direction = direction
        if self.win is None:
            return
        # 顶条颜色区分方向：中→英 蓝色，英→中 绿色
        self._header_color = theme.ACCENT if direction.startswith("中") else theme.GREEN
        self.text.delete("1.0", "end")
        self.text.insert("1.0", result)
        self.canvas.itemconfig(self._dir_item, text=direction)
        self.canvas.itemconfig(self._engine_item, text=engine)
        self._relayout()

    def _relayout(self):
        c = self.canvas
        W = self.card_w
        P = self.PAD

        # 内容宽度跟随卡片宽度
        c.itemconfig(self._src_item, width=W - 2 * P)
        c.itemconfig(self._text_item, width=W - 2 * P)
        c.update_idletasks()

        src_h = 0
        b = c.bbox(self._src_item)
        if b:
            src_h = b[3] - b[1]

        # 译文行数随宽度自动调整（超出 10 行可滚轮滚动）
        try:
            n = self.text.count("1.0", "end", "displaylines")[0]
            self.text.config(height=min(max(n, 2), 10))
        except tk.TclError:
            pass
        c.update_idletasks()

        text_h = self.text.winfo_reqheight()
        btn_h = self._btn_frame.winfo_reqheight()

        y_src = HEADER_H + 14
        y_sep = y_src + src_h + 10
        y_text = y_sep + 12
        y_btn = y_text + text_h + 8
        total_h = y_btn + btn_h + 12
        self._total_h = total_h

        c.coords(self._dir_item, P, HEADER_H // 2)
        c.coords(self._engine_item, W - P, HEADER_H // 2)
        c.coords(self._src_item, P, y_src)
        c.coords(self._sep_item, P, y_sep, W - P, y_sep)
        c.coords(self._bar_item, P - 8, y_text, P - 8, y_text + text_h)
        c.itemconfig(self._bar_item, fill=self._header_color)
        c.coords(self._text_item, P, y_text)
        c.coords(self._btn_item, P, y_btn)

        # 调整手柄位置
        for i, item in enumerate(self._grip):
            x1 = W - 18 + i * 6
            y1 = total_h - 4
            x2 = W - 4
            y2 = total_h - 18 + i * 6
            c.coords(item, x1, y1, x2, y2)

        c.delete("bg")
        _round_rect(c, SHADOW, SHADOW, SHADOW + W, SHADOW + total_h, RADIUS,
                    fill=SHADOW_COLOR, outline="", tags="bg")
        _round_rect(c, 0, 0, W, total_h, RADIUS, fill=theme.CARD,
                    outline=theme.BORDER, tags="bg")
        _top_round_rect(c, 0, 0, W, HEADER_H, RADIUS, fill=self._header_color,
                        outline="", tags="bg")
        c.tag_lower("bg")

        c.config(width=W + SHADOW, height=total_h + SHADOW)
        self._position()

    # ── 调整大小 ──
    def _in_grip(self, x, y):
        return x >= self.card_w - 24 and y >= self._total_h - 24

    def _on_press(self, e):
        if self._in_grip(e.x, e.y):
            self._resizing = True
            self._resize_start = (e.x_root, e.y_root, self.card_w)

    def _on_drag(self, e):
        if not self._resizing:
            return
        sx, sy, sw = self._resize_start
        new_w = max(self.MIN_W, min(self.MAX_W, sw + (e.x_root - sx)))
        if new_w != self.card_w:
            self.card_w = new_w
            self._relayout()

    def _on_release(self, e):
        self._resizing = False
        self._resize_start = None

    # ── 控件 ──
    def _mk_btn(self, text, command, fg):
        return tk.Button(self._btn_frame, text=text, command=command, relief="flat",
                         bd=0, bg=theme.CARD, fg=fg, activebackground=theme.ACCENT_BG,
                         activeforeground=fg, font=(theme.FONT, theme.SMALL),
                         cursor="hand2", padx=10, pady=4)

    def _copy(self):
        if self.on_copy:
            self.on_copy(self._result)
        self.copy_btn.config(text="✅ 已复制")

        def revert():
            try:
                self.copy_btn.config(text="📋 复制")
            except tk.TclError:
                pass  # 窗口已关闭
        self.copy_btn.after(1200, revert)

    def _toggle_pin(self):
        self.pinned = not self.pinned
        if self.pinned:
            self.pin_btn.config(text="📌 已固定", fg=theme.ACCENT)
            if self._timer is not None:
                try:
                    self.root.after_cancel(self._timer)
                except tk.TclError:
                    pass
                self._timer = None
        else:
            self.pin_btn.config(text="📌 固定", fg=theme.MUTED)

    def _restore_text(self, event=None):
        t = self.text
        if not t.edit_modified():
            return
        t.edit_modified(False)
        if t.get("1.0", "end-1c") != self._result:
            t.delete("1.0", "end")
            t.insert("1.0", self._result)

    def _on_focus_out(self, event=None):
        if self.pinned or self.win is None:
            return
        win = self.win

        def check():
            if not win.winfo_exists():
                return
            focused = win.focus_get()
            if focused is None or not str(focused).startswith(str(win)):
                self.close()
        win.after(120, check)

    def _focus(self):
        try:
            if self.win is not None and self.win.winfo_exists():
                self.win.focus_force()
                self.win.lift()
        except tk.TclError:
            pass

    def _position(self):
        if self.win is None:
            return
        try:
            self.win.update_idletasks()
            w = self.win.winfo_reqwidth()
            h = self.win.winfo_reqheight()
            # 优先定位到选中文字末尾（caret），否则回退到鼠标位置
            pos = caret_pos() or cursor_pos()
            x, y = pos
            sw = self.win.winfo_screenwidth()
            sh = self.win.winfo_screenheight()
            px, py = x, y + 22
            if px + w > sw - 4:
                px = max(4, sw - w - 4)
            if py + h > sh - 4:
                py = max(4, y - h - 8)
            self.win.geometry("+%d+%d" % (px, py))
        except tk.TclError:
            pass


class Toast:
    """短暂提示气泡（如 F9 开关状态）。"""

    def __init__(self, root):
        self.root = root
        self.win = None

    def show(self, msg, duration=1400):
        self.close()
        win = tk.Toplevel(self.root)
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        tk.Label(win, text=msg, bg="#2f3237", fg="#ffffff",
                 font=(theme.FONT, theme.BODY), padx=16, pady=9).pack()
        win.update_idletasks()
        x, y = cursor_pos()
        w = win.winfo_reqwidth()
        h = win.winfo_reqheight()
        sw = win.winfo_screenwidth()
        sh = win.winfo_screenheight()
        win.geometry("+%d+%d" % (min(x + 14, sw - w - 4), min(y + 20, sh - h - 4)))
        win.after(duration, self.close)
        self.win = win

    def close(self):
        if self.win is not None:
            try:
                self.win.destroy()
            except tk.TclError:
                pass
            self.win = None
