"""翻译结果悬浮窗：圆角卡片 + 阴影 + 彩色顶条

定位：锚定选区/光标，窗口打开后锁死；尺寸按内容自适应；支持拖动与拖拽缩放。
"""
import ctypes
from ctypes import wintypes
import tkinter as tk
import tkinter.font as tkfont

from . import theme

TRANSPARENT = "#ff00ff"   # 透明色 key（内容中不会出现此色）
SHADOW = 4
SHADOW_COLOR = "#dbe0e6"
RADIUS = 14
HEADER_H = 38
HEADER_TEXT = "#ffffff"
HEADER_ENGINE = "#dbeafe"
GRIP_COLOR = "#c3c8d0"
MARGIN = 8                # 弹窗与屏幕边缘最小距离

user32 = ctypes.windll.user32


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


class MONITORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", wintypes.RECT),
        ("rcWork", wintypes.RECT),
        ("dwFlags", wintypes.DWORD),
    ]


def cursor_pos():
    pt = wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y


def work_area_at(x, y):
    """返回 (left, top, right, bottom)：锚点所在显示器的可用区域（避开任务栏）。"""
    try:
        hmon = user32.MonitorFromPoint(wintypes.POINT(x, y), 2)  # NEAREST
        mi = MONITORINFO()
        mi.cbSize = ctypes.sizeof(mi)
        if user32.GetMonitorInfoW(hmon, ctypes.byref(mi)):
            r = mi.rcWork
            if r.right > r.left and r.bottom > r.top:
                return r.left, r.top, r.right, r.bottom
    except Exception:
        pass
    return (0, 0, user32.GetSystemMetrics(0), user32.GetSystemMetrics(1))


def caret_screen_pos():
    """当前输入光标（选区焦点）的屏幕坐标；失败返回 None。"""
    try:
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return None
        tid = user32.GetWindowThreadProcessId(hwnd, None)
        gti = GUITHREADINFO()
        gti.cbSize = ctypes.sizeof(gti)
        if not user32.GetGUIThreadInfo(tid, ctypes.byref(gti)):
            return None
        if not gti.hwndCaret:
            return None
        pt = wintypes.POINT(gti.rcCaret.left, gti.rcCaret.top)
        if not user32.ClientToScreen(gti.hwndCaret, ctypes.byref(pt)):
            return None
        # 合理性检查：必须落在虚拟屏幕范围内
        vx, vy = user32.GetSystemMetrics(76), user32.GetSystemMetrics(77)
        vw, vh = user32.GetSystemMetrics(78), user32.GetSystemMetrics(79)
        if vx <= pt.x < vx + vw and vy <= pt.y < vy + vh:
            return pt.x, pt.y
    except Exception:
        pass
    return None


def _truncate(text, limit):
    return text[:limit] + "…" if len(text) > limit else text


def _cjk_ratio(text):
    if not text:
        return 0.0
    n = sum(1 for ch in text[:800] if "一" <= ch <= "鿿")
    return n / min(len(text), 800)


def _visual_units(text):
    """视觉长度：中文按 2 计，其余按 1 计。"""
    return sum(2 if "一" <= ch <= "鿿" else 1 for ch in text[:800])


def _round_rect(canvas, x1, y1, x2, y2, r, **kw):
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
           x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
           x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
    return canvas.create_polygon(pts, smooth=True, **kw)


def _top_round_rect(canvas, x1, y1, x2, y2, r, **kw):
    pts = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
           x2, y2, x1, y2, x1, y1 + r, x1, y1]
    return canvas.create_polygon(pts, smooth=True, **kw)


class TranslatePopup:
    PAD = 16
    MIN_W = 360
    MAX_W = 760

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
        self.card_w = 420
        self._total_h = 0
        self._anchor = (0, 0)
        self._pos = None
        self._manual_width = None
        self._grip = []
        self._resizing = False
        self._resize_start = None
        self._moving = False
        self._move_start = None
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
    def show(self, source, pending="翻译中…", anchor=None):
        self.close()
        # 锚点在创建窗口前捕获（此时焦点仍在原应用上）
        self._anchor = anchor or caret_screen_pos() or cursor_pos()
        self._pos = None
        self._manual_width = None
        self._source = _truncate(source, 160)
        self.card_w = self._auto_width(source)

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
                                          text="", fill=HEADER_ENGINE,
                                          font=(theme.FONT, theme.TINY))
        self._src_item = c.create_text(self.PAD, HEADER_H + 14, anchor="nw",
                                       text=self._source, fill=theme.MUTED,
                                       font=(theme.FONT, theme.SMALL),
                                       width=self.card_w - 2 * self.PAD)
        self._sep_item = c.create_line(self.PAD, 0, self.card_w - self.PAD, 0,
                                       fill=theme.BORDER)
        self._bar_item = c.create_line(self.PAD - 8, 0, self.PAD - 8, 0,
                                       fill=self._header_color, width=3)

        self.text = tk.Text(win, bg=theme.CARD, fg=theme.TEXT,
                            font=(theme.FONT, theme.RESULT), wrap="word",
                            relief="flat", bd=0, highlightthickness=0, cursor="arrow",
                            width=40, height=3, padx=0, pady=0,
                            selectbackground="#cfe0ff", selectforeground=theme.TEXT)
        self.text.tag_configure("body", spacing1=2,
                                spacing2=theme.POPUP_LINE_SPACING,
                                spacing3=theme.POPUP_PARA_SPACING)
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
        self._moving = False

    # ── 尺寸 ──
    def _auto_width(self, text):
        wl, _, wr, _ = work_area_at(*self._anchor)
        max_w = max(self.MIN_W, min(self.MAX_W, int((wr - wl) * 0.55)))
        units = _visual_units(text)
        if units <= 40:
            w = 360
        elif units <= 90:
            w = 440
        elif units <= 180:
            w = 520
        elif units <= 360:
            w = 620
        else:
            w = 720
        return max(self.MIN_W, min(w, max_w))

    def _fit_source(self, text, width_px, wrap, max_lines):
        """把原文摘要截到最多 max_lines 行。"""
        if self._estimate_lines(text, width_px, wrap, theme.SMALL) <= max_lines:
            return text
        lo, hi = 0, len(text)
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if self._estimate_lines(text[:mid] + "…", width_px, wrap, theme.SMALL) <= max_lines:
                lo = mid
            else:
                hi = mid - 1
        return text[:lo].rstrip() + "…"

    @staticmethod
    def _estimate_lines(text, width_px, wrap, font_size):
        """按字体实际宽度估算显示行数（不依赖窗口是否已布局）。"""
        if not text:
            return 1
        f = tkfont.Font(font=(theme.FONT, font_size))
        limit = max(width_px, 40)
        total = 0
        for para in text.split("\n"):
            if not para:
                total += 1
                continue
            if wrap == "char":
                cur, n = 0, 1
                for ch in para:
                    w = f.measure(ch)
                    if cur + w > limit and cur > 0:
                        n += 1
                        cur = w
                    else:
                        cur += w
                total += n
            else:
                cur, n = 0, 1
                for word in para.split(" "):
                    w = f.measure(word + " ")
                    if cur + w > limit and cur > 0:
                        n += 1
                        cur = w
                    else:
                        cur += w
                total += n
        return max(1, total)

    # ── 内容 ──
    def set_result(self, result, engine="", direction=""):
        self._result = result
        if self.win is None:
            return
        self._header_color = theme.ACCENT if direction.startswith("中") else theme.GREEN
        if self._manual_width is None:
            self.card_w = self._auto_width(result or self._source)
        wrap = "char" if _cjk_ratio(result) >= 0.35 else "word"
        self.text.config(wrap=wrap)
        self.text.delete("1.0", "end")
        self.text.insert("1.0", result, "body")
        self.canvas.itemconfig(self._dir_item, text=direction)
        self.canvas.itemconfig(self._engine_item, text=engine)
        self._relayout()

    def _relayout(self):
        c = self.canvas
        W = self.card_w
        P = self.PAD

        avail = W - 2 * P
        c.itemconfig(self._src_item, width=avail)
        c.itemconfig(self._text_item, width=avail)
        c.update_idletasks()

        # 原文摘要：最多 2 行，超出省略
        src_font = tkfont.Font(font=(theme.FONT, theme.SMALL))
        src_wrap = "char" if _cjk_ratio(self._source) >= 0.35 else "word"
        src_text = self._fit_source(self._source, avail, src_wrap, 2)
        c.itemconfig(self._src_item, text=src_text)
        src_lines = self._estimate_lines(src_text, avail, src_wrap, theme.SMALL)
        src_h = src_lines * (src_font.metrics("linespace") + 2)
        btn_h = self._btn_frame.winfo_reqheight()

        # 译文行数：按字体宽度自行估算，避免未映射时 Tk 计数失真
        result_font = tkfont.Font(font=(theme.FONT, theme.RESULT))
        wrap = "char" if _cjk_ratio(self._result) >= 0.35 else "word"
        n = self._estimate_lines(self._result, avail, wrap, theme.RESULT)
        line_h = result_font.metrics("linespace") + theme.POPUP_LINE_SPACING

        # 按工作区高度限制最大行数，超出时在卡片内滚动
        _, wt, _, wb = work_area_at(*self._anchor)
        max_total_h = int((wb - wt) * 0.6)
        chrome = HEADER_H + 12 + src_h + 8 + 10 + 6 + btn_h + 10
        max_lines = max(4, (max_total_h - chrome) // max(line_h, 1))

        # 行距会额外撑高内容，按像素换算成行数，避免最后一行被裁切
        linespace = result_font.metrics("linespace")
        content_px = n * linespace + (n - 1) * theme.POPUP_LINE_SPACING
        height_lines = (content_px + linespace - 1) // max(1, linespace)
        height_lines = min(max(height_lines, 1), max_lines)

        # 让 Text 的请求宽度与卡片一致
        self.text.config(width=max(10, avail // max(1, result_font.measure("0"))))
        self.text.config(height=height_lines)
        c.update_idletasks()

        text_h = self.text.winfo_reqheight()
        y_src = HEADER_H + 12
        y_sep = y_src + src_h + 8
        y_text = y_sep + 10
        y_btn = y_text + text_h + 6
        total_h = y_btn + btn_h + 10
        self._total_h = total_h

        c.coords(self._dir_item, P, HEADER_H // 2)
        c.coords(self._engine_item, W - P, HEADER_H // 2)
        c.coords(self._src_item, P, y_src)
        c.coords(self._sep_item, P, y_sep, W - P, y_sep)
        c.coords(self._bar_item, P - 8, y_text, P - 8, y_text + text_h)
        c.itemconfig(self._bar_item, fill=self._header_color)
        c.coords(self._text_item, P, y_text)
        c.coords(self._btn_item, P, y_btn)

        for i, item in enumerate(self._grip):
            c.coords(item, W - 18 + i * 6, total_h - 4, W - 4, total_h - 18 + i * 6)

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

    # ── 定位 ──
    def _position(self):
        """首次按锚点定位；之后只做边界修正，不再重新取光标。"""
        if self.win is None:
            return
        try:
            self.win.update_idletasks()
            W = self.win.winfo_reqwidth()
            H = self.win.winfo_reqheight()
            ax, ay = self._anchor
            wl, wt, wr, wb = work_area_at(ax, ay)

            if self._pos is None:
                x, y = ax + 8, ay + 18
                if x + W > wr - MARGIN:
                    x = ax - W - 8
                if x < wl + MARGIN:
                    x = wl + MARGIN
                if y + H > wb - MARGIN:
                    y = ay - H - 12
                if y < wt + MARGIN:
                    y = wt + MARGIN
            else:
                x, y = self._pos

            # 尺寸变化后保证仍在工作区内（只移位，不跳动）
            x = max(wl + MARGIN, min(x, wr - W - MARGIN))
            y = max(wt + MARGIN, min(y, wb - H - MARGIN))
            self._pos = (x, y)
            self.win.geometry("+%d+%d" % (x, y))
        except tk.TclError:
            pass

    # ── 拖动 / 缩放 ──
    def _in_grip(self, x, y):
        return x >= self.card_w - 24 and y >= self._total_h - 24

    def _on_press(self, e):
        if self._in_grip(e.x, e.y):
            self._resizing = True
            self._resize_start = (e.x_root, e.y_root, self.card_w)
        elif e.y <= HEADER_H + 2:
            self._moving = True
            x, y = self._pos or (0, 0)
            self._move_start = (e.x_root, e.y_root, x, y)

    def _on_drag(self, e):
        if self._resizing:
            sx, _, sw = self._resize_start
            new_w = max(self.MIN_W, min(self.MAX_W, sw + (e.x_root - sx)))
            if new_w != self.card_w:
                self.card_w = new_w
                self._manual_width = new_w
                self._relayout()
        elif self._moving:
            sx, sy, ox, oy = self._move_start
            ax, ay = self._anchor
            wl, wt, wr, wb = work_area_at(ax, ay)
            W, H = self.win.winfo_reqwidth(), self.win.winfo_reqheight()
            nx = max(wl + MARGIN, min(ox + (e.x_root - sx), wr - W - MARGIN))
            ny = max(wt + MARGIN, min(oy + (e.y_root - sy), wb - H - MARGIN))
            self._pos = (nx, ny)
            self.win.geometry("+%d+%d" % (nx, ny))

    def _on_release(self, e):
        self._resizing = False
        self._resize_start = None
        self._moving = False
        self._move_start = None

    # ── 控件 ──
    def _mk_btn(self, text, command, fg):
        return tk.Button(self._btn_frame, text=text, command=command, relief="flat",
                         bd=0, bg=theme.CARD, fg=fg, activebackground=theme.ACCENT_BG,
                         activeforeground=fg, font=(theme.FONT, theme.SMALL),
                         cursor="hand2", padx=9, pady=3)

    def _copy(self):
        if self.on_copy:
            self.on_copy(self._result)
        self.copy_btn.config(text="✅ 已复制")

        def revert():
            try:
                self.copy_btn.config(text="📋 复制")
            except tk.TclError:
                pass
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
            t.insert("1.0", self._result, "body")

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
