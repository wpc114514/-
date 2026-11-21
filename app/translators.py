"""翻译引擎：DeepL / 百度 / Google / MyMemory，按顺序自动切换 + 术语保护 + 长文本分段"""
import hashlib
import html
import json
import random
import re
import urllib.error
import urllib.parse
import urllib.request

USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
              "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

_BAIDU_ERRORS = {
    "52001": "请求超时，请重试",
    "52002": "系统错误，请重试",
    "52003": "appid 无效，请检查 config.json",
    "54001": "签名错误，请检查 baidu_secret",
    "54003": "访问频率受限，请稍后再试",
    "54004": "账户余额不足",
    "58001": "不支持该翻译方向",
}


class TranslateError(Exception):
    """翻译失败（所有引擎都试过了）"""


def _http_get(url, timeout=6):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def _http_post(url, data, timeout=6, extra_headers=None):
    body = urllib.parse.urlencode(data).encode("utf-8")
    headers = {"User-Agent": USER_AGENT,
               "Content-Type": "application/x-www-form-urlencoded"}
    if extra_headers:
        headers.update(extra_headers)
    req = urllib.request.Request(url, data=body, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def contains_cjk(text):
    return any("一" <= ch <= "鿿" for ch in text)


def resolve_langs(text, direction):
    """返回 (src, dst)。direction 为 auto 时按是否含中文判断。"""
    if direction == "zh2en":
        return "zh-CN", "en"
    if direction == "en2zh":
        return "en", "zh-CN"
    return ("zh-CN", "en") if contains_cjk(text) else ("en", "zh-CN")


# ── 长文本分句（逐句翻译，减少语义漂移）──
_ABBREV = re.compile(
    r"\b(e\.g\.|i\.e\.|et al\.|vs\.|cf\.|etc\.|fig\.|eq\.|approx\.|resp\.|no\.|vol\.|pp\.)"
    r"(?![A-Za-z])", re.IGNORECASE)
# 中文句末标点直接切；英文句末标点需后接空格+大写字母（避免切到小数点/URL）
_SENT_SPLIT = re.compile(r"(?<=[。！？；])\s*|(?<=[.!?])\s+(?=[A-Z])")


def split_sentences(text):
    out = []
    for para in [p.strip() for p in re.split(r"\n+", text) if p.strip()]:
        if len(para) <= 160:
            out.append(para)
            continue
        markers = {}

        def _protect_abbrev(m):
            k = "[[A{}]]".format(len(markers))
            markers[k] = m.group(0)
            return k

        protected = _ABBREV.sub(_protect_abbrev, para)
        for piece in _SENT_SPLIT.split(protected):
            piece = piece.strip()
            if not piece:
                continue
            for k, v in markers.items():
                piece = piece.replace(k, v)
            out.append(piece)
    return out


# ── 引擎 ──
class GoogleEngine:
    """谷歌翻译免费接口（gtx）。中国大陆网络通常无法直连，需代理。"""
    name = "google"
    label = "Google 翻译"

    def __init__(self, timeout=6):
        self.timeout = timeout

    def translate(self, text, direction):
        src, dst = resolve_langs(text, direction)
        src = "auto" if direction == "auto" else src
        url = ("https://translate.googleapis.com/translate_a/single"
               "?client=gtx&sl={}&tl={}&dt=t&q={}").format(
                   src, dst, urllib.parse.quote(text))
        data = json.loads(_http_get(url, self.timeout))
        parts = []
        for seg in data[0]:
            if isinstance(seg, (list, tuple)) and seg and isinstance(seg[0], str):
                parts.append(seg[0])
        result = "".join(parts).strip()
        if not result:
            raise TranslateError("返回内容为空")
        return result


class MyMemoryEngine:
    """MyMemory 免费接口（无需密钥，适合短句，长文本自动分段）。"""
    name = "mymemory"
    label = "MyMemory 翻译"
    MAX_CHUNK = 400

    def __init__(self, timeout=6):
        self.timeout = timeout

    def translate(self, text, direction):
        src, dst = resolve_langs(text, direction)
        outs = []
        for i in range(0, len(text), self.MAX_CHUNK):
            chunk = text[i:i + self.MAX_CHUNK]
            url = ("https://api.mymemory.translated.net/get?q={}&langpair={}|{}").format(
                urllib.parse.quote(chunk), src, dst)
            data = json.loads(_http_get(url, self.timeout))
            if data.get("responseStatus") != 200:
                raise TranslateError(data.get("responseDetails", "接口错误"))
            out = (data.get("responseData") or {}).get("translatedText", "")
            outs.append(html.unescape(out))
        result = "".join(outs).strip()
        if not result:
            raise TranslateError("返回内容为空")
        return result


class BaiduEngine:
    """百度翻译（通用文本翻译免费版，需在 config.json 配置 appid/secret）。"""
    name = "baidu"
    label = "百度翻译"

    def __init__(self, appid, secret, timeout=6):
        self.appid = appid
        self.secret = secret
        self.timeout = timeout

    def translate(self, text, direction):
        src, dst = resolve_langs(text, direction)
        src = "auto" if direction == "auto" else src.split("-")[0]
        dst = dst.split("-")[0]
        salt = str(random.randint(10000, 99999))
        sign = hashlib.md5((self.appid + text + salt + self.secret).encode("utf-8")).hexdigest()
        params = {"q": text, "from": src, "to": dst,
                  "appid": self.appid, "salt": salt, "sign": sign}
        url = ("https://fanyi-api.baidu.com/api/trans/vip/translate?"
               + urllib.parse.urlencode(params))
        data = json.loads(_http_get(url, self.timeout))
        if "error_code" in data:
            code = str(data["error_code"])
            raise TranslateError("百度翻译错误 {}：{}".format(
                code, _BAIDU_ERRORS.get(code, data.get("error_msg", "未知错误"))))
        trans = data.get("trans_result") or []
        result = "".join(t.get("dst", "") for t in trans).strip()
        if not result:
            raise TranslateError("返回内容为空")
        return result


class DeepLEngine:
    """DeepL 翻译（学术文本质量最优）。免费版 50 万字符/月。"""
    name = "deepl"
    label = "DeepL 翻译"

    def __init__(self, key, timeout=6):
        self.key = key.strip()
        self.timeout = timeout
        # 免费版 key 以 :fx 结尾，用 api-free 端点；否则为 Pro，用 api.deepl.com
        self.base = ("https://api-free.deepl.com/v2/translate"
                     if self.key.endswith(":fx") else
                     "https://api.deepl.com/v2/translate")

    def translate(self, text, direction):
        src, dst = resolve_langs(text, direction)
        target = "ZH" if dst.startswith("zh") else "EN-US"
        data = {"text": text, "target_lang": target}
        if direction != "auto":
            data["source_lang"] = "ZH" if src.startswith("zh") else "EN"
        body = urllib.parse.urlencode(data).encode("utf-8")
        req = urllib.request.Request(self.base, data=body, headers={
            "User-Agent": USER_AGENT,
            "Authorization": "DeepL-Auth-Key " + self.key,
            "Content-Type": "application/x-www-form-urlencoded",
        })
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            raise TranslateError("DeepL {}：{}".format(e.code, _deepl_error(e.code)))
        j = json.loads(raw)
        result = "".join(t.get("text", "") for t in (j.get("translations") or [])).strip()
        if not result:
            raise TranslateError("返回内容为空")
        return result


def _deepl_error(code):
    return {400: "请求参数错误", 403: "API key 无效或无权限", 404: "资源不存在",
            413: "文本过长", 429: "请求过于频繁，请稍候", 456: "本月配额已用完",
            503: "服务暂时不可用"}.get(code, "HTTP {}".format(code))


class TranslatorChain:
    """按顺序尝试各引擎 + 术语保护 + 长文本分句翻译。"""

    def __init__(self, cfg):
        order = [str(x) for x in cfg.get("engine_order") or
                 ["deepl", "baidu", "google", "mymemory"]]
        primary = cfg.get("primary_engine", "auto")
        if primary != "auto":
            if primary in order:
                order.remove(primary)
            order.insert(0, primary)
        # 已配置密钥的引擎即使不在 engine_order 里也自动启用
        if cfg.get("deepl_key") and "deepl" not in order:
            order.insert(0, "deepl")
        if cfg.get("baidu_appid") and cfg.get("baidu_secret") and "baidu" not in order:
            order.append("baidu")

        timeout = int(cfg.get("network_timeout", 4))
        self.engines = []
        for name in order:
            if name == "google":
                self.engines.append(GoogleEngine(timeout))
            elif name == "mymemory":
                self.engines.append(MyMemoryEngine(timeout))
            elif name == "baidu":
                appid = cfg.get("baidu_appid", "")
                secret = cfg.get("baidu_secret", "")
                if appid and secret:
                    self.engines.append(BaiduEngine(appid, secret, timeout))
            elif name == "deepl":
                key = cfg.get("deepl_key", "")
                if key:
                    self.engines.append(DeepLEngine(key, timeout))
        if not self.engines:
            self.engines.append(GoogleEngine(timeout))

        self.segment = bool(cfg.get("segment_sentences", True))
        self.threshold = int(cfg.get("segment_threshold", 300))
        self.glossary_path = cfg.get("glossary_path", "") or None
        self._fails = {}  # 引擎名 -> 连续失败次数

    def label_of(self, name):
        for eng in self.engines:
            if eng.name == name:
                return eng.label
        return name

    def translate(self, text, direction):
        from . import glossary
        src, dst = resolve_langs(text, direction)
        # 分段后每段可能不含中文，须用显式方向，避免引擎重新 auto 检测导致方向翻转
        explicit = direction if direction != "auto" else ("zh2en" if dst == "en" else "en2zh")
        source_is_zh = src.startswith("zh")
        entries = glossary.load(self.glossary_path)

        segments = split_sentences(text) if (self.segment and len(text) > self.threshold) else [text]

        outs = []
        engine_name = None
        for seg in segments:
            protected, mapping = glossary.protect(seg, entries, source_is_zh)
            result, en = self._translate_plain(protected, explicit)
            if engine_name is None:
                engine_name = en
            outs.append(glossary.restore(result, mapping))

        sep = " " if dst == "en" else ""
        final = sep.join(o for o in outs if o).strip()
        if not final:
            raise TranslateError("所有翻译引擎均不可用")
        return final, engine_name

    def _translate_plain(self, text, direction):
        errors = []
        for eng in self.engines:
            if self._fails.get(eng.name, 0) >= 2:
                continue  # 连续失败 2 次，本进程内暂时跳过（避免每次都等超时）
            try:
                result = eng.translate(text, direction)
                if result and result.strip():
                    self._fails[eng.name] = 0
                    return result, eng.name
            except Exception as e:  # noqa: BLE001 —— 单个引擎失败继续尝试下一个
                self._fails[eng.name] = self._fails.get(eng.name, 0) + 1
                errors.append("{}: {}".format(eng.label, e))
        raise TranslateError("；".join(errors) or "所有翻译引擎均不可用")
