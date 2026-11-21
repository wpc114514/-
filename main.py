"""划词翻译 · 中英互译 —— 入口

用法：
    python main.py               正常启动
    python main.py --selftest    测试翻译引擎后退出
    python main.py --gui-smoke   打开界面自检后自动退出
"""
import argparse
import os
import sys
import time
import traceback

from app import config as config_mod


def enable_dpi_awareness():
    """启用系统级 DPI 感知，避免高分屏下界面被拉伸模糊。须在创建任何窗口前调用。"""
    import ctypes
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)  # PROCESS_SYSTEM_DPI_AWARE
        return
    except Exception:
        pass
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


def _log_error(text):
    try:
        with open(os.path.join(config_mod.APP_DIR, "error.log"), "a",
                  encoding="utf-8") as f:
            f.write("\n[{}]\n{}\n".format(time.strftime("%Y-%m-%d %H:%M:%S"), text))
    except OSError:
        pass


def setup_excepthook():
    def hook(tp, val, tb):
        text = "".join(traceback.format_exception(tp, val, tb))
        _log_error(text)
        try:
            import tkinter.messagebox as mb
            mb.showerror("划词翻译出错了",
                         "发生错误，详情已写入 error.log：\n\n{}".format(val))
        except Exception:
            pass
    sys.excepthook = hook


def selftest():
    from app.translators import TranslatorChain
    from app.hotkey import parse_hotkey

    # 控制台可能是 GBK，强制 UTF-8 输出避免编码崩溃
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    cfg = config_mod.load()
    chain = TranslatorChain(cfg)
    print("可用引擎:", "、".join(e.label for e in chain.engines))
    print("网络超时:", cfg["network_timeout"], "秒")
    print("-" * 50)

    samples = [
        "Hello, world!",
        "你好世界，今天天气很好。",
        "The quick brown fox jumps over the lazy dog.",
    ]
    ok = True
    for s in samples:
        try:
            result, engine = chain.translate(s, "auto")
            print("[OK]   [{}] {!r} -> {!r}".format(chain.label_of(engine), s, result))
        except Exception as e:
            ok = False
            print("[FAIL] {!r} -> {}".format(s, e))

    print("-" * 50)
    from app import glossary
    from app.translators import split_sentences
    entries = [("transformer", "Transformer 模型"),
               ("attention mechanism", "注意力机制"),
               ("attention", "注意力")]
    sample = "The transformer uses an attention mechanism."
    prot, mapping = glossary.protect(sample, entries, source_is_zh=False)
    print("术语保护:", prot)
    print("术语还原:", glossary.restore(prot, mapping))
    print("长文分句:", split_sentences("First sentence ends. e.g. this stays. 第二句结束了。第三句也结束。"))

    print("-" * 50)
    for spec in ["f8", "f9", "ctrl+shift+d", "bad_spec"]:
        print("热键解析 {!r}: {}".format(spec, parse_hotkey(spec)))
    print("自检完成:", "全部通过" if ok else "部分引擎失败（运行时会自动切换引擎）")
    return 0 if ok else 1


def main():
    parser = argparse.ArgumentParser(description="划词翻译 · 中英互译")
    parser.add_argument("--selftest", action="store_true", help="测试翻译引擎后退出")
    parser.add_argument("--gui-smoke", action="store_true", help="打开界面自检后自动退出")
    args = parser.parse_args()

    cfg = config_mod.load()

    if args.selftest:
        sys.exit(selftest())

    setup_excepthook()  # 仅 GUI 模式弹错误框

    enable_dpi_awareness()  # 须在创建 Tk 窗口前启用

    import tkinter as tk
    from app.app import App

    root = tk.Tk()
    icon = config_mod.resource_path("icon.ico")
    if os.path.exists(icon):
        try:
            root.iconbitmap(icon)
        except tk.TclError:
            pass
    app = App(root, cfg)

    if args.gui_smoke:
        def smoke():
            app.popup.show("Hello, world!")
            app.popup.set_result("你好，世界！", engine="界面自检", direction="英文 → 中文")
            app.toast.show("界面冒烟测试")
        root.after(800, smoke)
        root.after(4000, app.on_close)

    root.mainloop()


if __name__ == "__main__":
    main()
