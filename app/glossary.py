"""术语表：翻译前把术语替换为占位符保护，翻译后还原，保证术语准确且一致"""
import os
import re

from .config import APP_DIR

DEFAULT_GLOSSARY = "glossary.txt"

# 占位符 [[0]]：ASCII 双中括号，各引擎都会原样保留（已实测 MyMemory 保留）
_PLACEHOLDER_RE = re.compile(r"\[\[\s*(\d+)\s*\]\]")

_EXAMPLE = """# 术语表：每行一条「英文<TAB>中文」，翻译时自动保护这些术语，保证译法准确且全文一致。
# 以 # 开头为注释；可随意增删改，保存后立即生效。
# 分隔用 Tab（英文和中文之间按一下 Tab 键）。

transformer	Transformer 模型
attention	注意力
attention mechanism	注意力机制
embedding	词嵌入
neural network	神经网络
machine learning	机器学习
deep learning	深度学习
gradient descent	梯度下降
overfitting	过拟合
natural language processing	自然语言处理
large language model	大语言模型
fine-tuning	微调
inference	推理
"""


def default_path():
    return os.path.join(APP_DIR, DEFAULT_GLOSSARY)


def ensure_example(path=None):
    """若术语表不存在则创建示例，返回路径。"""
    p = path or default_path()
    if not os.path.exists(p):
        try:
            with open(p, "w", encoding="utf-8") as f:
                f.write(_EXAMPLE)
        except OSError:
            pass
    return p


def load(path=None):
    """读取术语表，返回 [(英文, 中文), ...]。"""
    entries = []
    p = path or default_path()
    try:
        with open(p, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                # 支持 Tab、两个以上空格、=> 作为分隔
                parts = re.split(r"\t+|\s{2,}|\s*=>\s*", line, maxsplit=1)
                if len(parts) != 2:
                    continue
                a, b = parts[0].strip(), parts[1].strip()
                if a and b:
                    entries.append((a, b))
    except OSError:
        pass
    return entries


def protect(text, entries, source_is_zh):
    """把文本中出现的术语替换为占位符。

    返回 (protected_text, mapping)，mapping = {占位符: 目标术语}。
    source_is_zh 为 True 时匹配术语的中文侧、还原为英文侧，反之亦然。
    """
    mapping = {}
    pairs = [(zh if source_is_zh else en, en if source_is_zh else zh)
             for en, zh in entries]
    # 长术语优先匹配，避免短术语先替换掉长术语的一部分
    pairs.sort(key=lambda p: -len(p[0]))

    result = text
    for i, (src_term, dst_term) in enumerate(pairs):
        if not src_term:
            continue
        ph = "[[{}]]".format(i)
        if source_is_zh:
            if src_term in result:
                result = result.replace(src_term, ph)
                mapping[ph] = dst_term
        else:
            # 英文术语：大小写不敏感 + 词边界（避免 attention 匹配 attentional）
            pat = re.compile(
                r"(?<![A-Za-z0-9])" + re.escape(src_term) + r"(?![A-Za-z0-9])",
                re.IGNORECASE)
            if pat.search(result):
                result = pat.sub(ph, result)
                mapping[ph] = dst_term
    return result, mapping


def restore(text, mapping):
    """把占位符还原为目标术语。"""
    if not mapping:
        return text
    return _PLACEHOLDER_RE.sub(
        lambda m: mapping.get("[[{}]]".format(m.group(1)), m.group(0)), text)
