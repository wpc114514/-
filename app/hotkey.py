"""全局快捷键：基于 ctypes 轮询 GetAsyncKeyState，无需任何第三方库。

支持格式：f1-f24、a-z、0-9，可组合 ctrl/alt/shift/win，如 "ctrl+shift+d"。
"""
import ctypes
import os
import time
from ctypes import wintypes

user32 = ctypes.windll.user32

_MODS = {"ctrl": 0x11, "alt": 0x12, "shift": 0x10, "win": 0x5B}
_KEYUP = 0x0002
_VK_CONTROL = 0x11
_VK_C = 0x43


def _key_vk(name):
    name = name.lower()
    if name.startswith("f") and name[1:].isdigit():
        n = int(name[1:])
        if 1 <= n <= 24:
            return 0x6F + n
    if len(name) == 1:
        if "a" <= name <= "z":
            return ord(name.upper())
        if "0" <= name <= "9":
            return ord(name)
    return None


def parse_hotkey(spec):
    """解析 "f8" / "ctrl+shift+d" 等，失败返回 None。"""
    parts = [p.strip().lower() for p in str(spec).split("+")]
    mods, key = [], None
    for p in parts:
        if p in _MODS:
            mods.append(_MODS[p])
        elif key is None:
            key = p
        else:
            return None
    vk = _key_vk(key) if key else None
    if vk is None:
        return None
    return tuple(sorted(set(mods))), vk


class HotkeyWatcher:
    """hotkeys: {快捷键字符串: 回调函数}。需在 UI 主循环里高频调用 poll()。"""

    def __init__(self, hotkeys):
        self._keys = []
        self._state = {}
        for spec, callback in hotkeys.items():
            parsed = parse_hotkey(spec)
            if parsed is None:
                continue
            mods, vk = parsed
            self._keys.append((mods, vk, callback))
            self._state[(mods, vk)] = False

    def poll(self):
        for mods, vk, callback in self._keys:
            down = (user32.GetAsyncKeyState(vk) & 0x8000) != 0
            mods_ok = all((user32.GetAsyncKeyState(m) & 0x8000) != 0 for m in mods)
            active = down and mods_ok
            if active and not self._state[(mods, vk)]:
                self._state[(mods, vk)] = True
                try:
                    callback()
                except Exception:
                    pass
            elif not active:
                self._state[(mods, vk)] = False


def send_copy():
    """向系统模拟一次 Ctrl+C，把当前选中的文字放进剪贴板。"""
    time.sleep(0.02)
    user32.keybd_event(_VK_CONTROL, 0, 0, 0)
    time.sleep(0.02)
    user32.keybd_event(_VK_C, 0, 0, 0)
    time.sleep(0.02)
    user32.keybd_event(_VK_C, 0, _KEYUP, 0)
    time.sleep(0.02)
    user32.keybd_event(_VK_CONTROL, 0, _KEYUP, 0)


# ── 划词即译：鼠标拖选监听 ──
_VK_LBUTTON = 0x01


def cursor_pos():
    pt = wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y


def _window_pid_at(x, y):
    """返回屏幕 (x, y) 处窗口所属进程 PID，失败返回 None。"""
    hwnd = user32.WindowFromPoint(wintypes.POINT(x, y))
    if not hwnd:
        return None
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return pid.value


class SelectionWatcher:
    """监听鼠标左键拖选（按下→拖动→释放），判定为划词后触发回调。

    仅识别拖选（距离超过阈值），并排除本进程窗口内的操作。
    """

    def __init__(self, on_select, threshold=6):
        self.on_select = on_select
        self.threshold = threshold
        self._down = False
        self._down_pos = (0, 0)
        self._own_pid = os.getpid()

    def poll(self):
        down = (user32.GetAsyncKeyState(_VK_LBUTTON) & 0x8000) != 0
        if down and not self._down:
            self._down = True
            self._down_pos = cursor_pos()
        elif not down and self._down:
            self._down = False
            x, y = cursor_pos()
            dx = x - self._down_pos[0]
            dy = y - self._down_pos[1]
            if dx * dx + dy * dy < self.threshold * self.threshold:
                return  # 是点击而非拖选
            if _window_pid_at(x, y) == self._own_pid:
                return  # 本程序窗口内，不触发
            try:
                self.on_select()
            except Exception:
                pass
