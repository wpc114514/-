"""配置的加载与保存（config.json 位于应用根目录 / exe 同目录）"""
import json
import os
import sys
import tempfile


def _writable(path):
    try:
        with tempfile.TemporaryFile(dir=path):
            return True
    except OSError:
        return False


def _base_dir():
    """源码运行时为项目目录；打包成 exe 后为 exe 所在目录。"""
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# 打包后的内置资源目录（PyInstaller 解压目录），源码运行时为项目目录
RESOURCE_DIR = getattr(sys, "_MEIPASS", _base_dir())

# 配置/术语表/日志目录：优先 exe 同目录，不可写（如 Program Files）则退回 %APPDATA%
APP_DIR = _base_dir()
if not _writable(APP_DIR):
    APP_DIR = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), "划词翻译")
    try:
        os.makedirs(APP_DIR, exist_ok=True)
    except OSError:
        pass

CONFIG_PATH = os.path.join(APP_DIR, "config.json")


def resource_path(name):
    """获取打包内置资源（如 icon.ico）的路径。"""
    return os.path.join(RESOURCE_DIR, name)

DEFAULTS = {
    "auto_translate": True,                 # 复制/选中文字后自动弹出翻译
    "select_translate": False,              # 划词即译：拖选文字自动翻译（无需 Ctrl+C）
    "direction": "auto",                    # auto | zh2en | en2zh
    "primary_engine": "auto",               # auto | deepl | baidu | google | mymemory
    "engine_order": ["deepl", "baidu", "google", "mymemory"],
    "deepl_key": "",                        # DeepL API key（deepl.com 免费注册，50 万字符/月）
    "baidu_appid": "",                      # 百度翻译开放平台（免费）: https://fanyi-api.baidu.com
    "baidu_secret": "",
    "glossary_path": "",                    # 术语表路径，空 = 默认 glossary.txt
    "segment_sentences": True,              # 长文本按句分段翻译，减少语义漂移
    "segment_threshold": 300,               # 超过该字符数才分段
    "hotkey_translate": "f8",               # 翻译选中文字（自动模拟 Ctrl+C）
    "hotkey_toggle": "f9",                  # 开/关自动翻译
    "popup_timeout": 0,                     # 弹窗自动关闭秒数，0 = 不自动关闭（点击别处/Esc 关闭）
    "max_text_length": 1500,                # 超过则截断
    "network_timeout": 4,                   # 每个引擎的请求超时秒数
}


def load():
    cfg = dict(DEFAULTS)
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            cfg.update({k: v for k, v in data.items() if k in DEFAULTS})
    except FileNotFoundError:
        pass
    except (json.JSONDecodeError, OSError):
        pass
    return cfg


def save(cfg):
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except OSError:
        pass
