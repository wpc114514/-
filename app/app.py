"""应用核心：剪贴板监听 + 全局热键 + 翻译调度"""
import threading
import time
import tkinter as tk

from . import config as config_mod
from .control import ControlWindow
from .hotkey import HotkeyWatcher, SelectionWatcher, send_copy
from .popup import TranslatePopup, Toast
from .translators import TranslatorChain, TranslateError, resolve_langs


class App:
    def __init__(self, root, cfg):
        self.root = root
        self.cfg = cfg
        self.popup = TranslatePopup(root, timeout=int(cfg.get("popup_timeout", 0)),
                                    on_copy=self.on_self_copy)
        self.toast = Toast(root)
        self.control = ControlWindow(root, cfg, self)
        self.rebuild_chain()

        self.last_clip = None      # 上次见到的剪贴板内容（防自己复制触发）
        self.force_until = 0.0     # F8 触发的强制翻译窗口
        self._version = 0          # 丢弃过期翻译结果

        self.watcher = HotkeyWatcher({
            str(cfg.get("hotkey_translate", "f8")): self.on_hotkey_translate,
            str(cfg.get("hotkey_toggle", "f9")): self.on_hotkey_toggle,
        })
        self.selection = SelectionWatcher(self.on_select_translate)
        self.select_enabled = bool(cfg.get("select_translate", False))

        root.protocol("WM_DELETE_WINDOW", self.on_close)
        root.after(50, self._poll_hotkeys)
        root.after(250, self._poll_clipboard)

    # ── 引擎 ──────────────────────────────────────────────────
    def rebuild_chain(self):
        self.chain = TranslatorChain(self.cfg)

    # ── 轮询 ──────────────────────────────────────────────────
    def _poll_hotkeys(self):
        try:
            self.watcher.poll()
            if self.select_enabled:
                self.selection.poll()
        except Exception:
            pass
        self.root.after(50, self._poll_hotkeys)

    def _poll_clipboard(self):
        text = None
        try:
            text = self.root.clipboard_get()
        except tk.TclError:
            text = None
        if isinstance(text, str):
            text = text.strip()
            forced = time.time() < self.force_until
            changed = text != self.last_clip
            if text and (changed or forced) and (forced or self.cfg.get("auto_translate", True)):
                self.last_clip = text
                self.force_until = 0.0
                limit = int(self.cfg.get("max_text_length", 1500))
                if len(text) > limit:
                    text = text[:limit] + "…（已截断）"
                self.translate(text, source="clipboard")
        self.root.after(250, self._poll_clipboard)

    # ── 热键 ──────────────────────────────────────────────────
    def on_hotkey_translate(self):
        """F8：自动复制当前选中文字并翻译（无需手动 Ctrl+C）。"""
        self.force_until = time.time() + 1.5
        send_copy()

    def on_hotkey_toggle(self):
        """F9：开/关自动翻译。"""
        self.control.toggle_auto()

    def on_select_translate(self):
        """划词即译：拖选文字后延迟一点再复制并翻译。"""
        self.root.after(120, self.on_hotkey_translate)

    # ── 翻译流程 ──────────────────────────────────────────────
    def translate(self, text, source="clipboard", direction=None):
        direction = direction or self.cfg.get("direction", "auto")
        self._version += 1
        v = self._version
        if source == "clipboard":
            self.popup.show(text)
        self.control.set_status("正在翻译…")

        def worker():
            result = engine = err = None
            try:
                result, engine = self.chain.translate(text, direction)
            except TranslateError as e:
                err = str(e)
            except Exception as e:
                err = "未知错误：{}".format(e)
            try:
                self.root.after(0, lambda: self._on_done(v, source, text, direction,
                                                         result, engine, err))
            except (tk.TclError, RuntimeError):
                pass  # 主窗口已关闭
        threading.Thread(target=worker, daemon=True).start()

    def _on_done(self, v, source, text, direction, result, engine, err):
        if v != self._version:
            return  # 已有更新的翻译请求
        if err is not None:
            self.control.set_status("翻译失败")
            if source == "clipboard":
                self.popup.set_result("翻译失败：{}".format(err), "", "")
            else:
                self.control.show_result("翻译失败：{}".format(err))
            return
        src, dst = resolve_langs(text, direction)
        dir_label = ("中文" if src.startswith("zh") else "英文") + " → " + \
                    ("中文" if dst.startswith("zh") else "英文")
        engine_label = self.chain.label_of(engine)
        self.control.set_status("翻译完成（{}）".format(engine_label))
        if source == "clipboard":
            self.popup.set_result(result, engine=engine_label, direction=dir_label)
        else:
            self.control.show_result(result)

    # ── 其它 ──────────────────────────────────────────────────
    def set_select_translate(self, enabled):
        self.select_enabled = bool(enabled)
        self.cfg["select_translate"] = bool(enabled)
        config_mod.save(self.cfg)
        self.control.set_status("划词即译已开启" if enabled else "划词即译已关闭")
        self.toast.show("🖱 划词即译已开启" if enabled else "🖱 划词即译已关闭")

    def set_auto(self, enabled):
        self.cfg["auto_translate"] = bool(enabled)
        config_mod.save(self.cfg)
        self.control.set_status("自动翻译已开启" if enabled else "自动翻译已关闭")
        self.toast.show("✅ 自动翻译已开启" if enabled else "⏸ 自动翻译已关闭")

    def on_self_copy(self, text):
        """自己复制的内容（译文等）不再触发翻译。"""
        self.last_clip = text

    def on_close(self):
        config_mod.save(self.cfg)
        self.root.destroy()
