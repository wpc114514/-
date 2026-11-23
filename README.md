# 划词翻译 · 中英互译（论文翻译优化版）

[![CI](https://github.com/wpc114514/-/actions/workflows/ci.yml/badge.svg)](https://github.com/wpc114514/-/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)

一个 Windows 桌面小工具：在任意软件（浏览器 / Word / PDF 阅读器）中**选中文字**，按 `Ctrl+C`（或直接按 `F8`），翻译结果立即**弹出在靠近选中文字的位置**。针对**论文翻译**做了专业化优化。

> 直接下载可执行程序：见 [Releases](https://github.com/wpc114514/-/releases)（无需安装 Python）。

## 功能

- 🖱 **划词即译**：开启后鼠标拖选文字、松开即翻译，无需按 Ctrl+C
- 🖱 **复制即译**：选中/复制文字后自动弹出翻译（自动检测 中→英 / 英→中）
- ⌨ **全局快捷键**：`F8` 翻译当前选中的文字（自动帮你复制）；`F9` 开/关自动翻译
- 📚 **术语表**：本地 `glossary.txt` 维护学术术语中英对照，翻译时自动保护/还原，保证术语准确且全文一致
- ✂️ **智能分段**：长文本按句分段逐句翻译再合并，减少长句语义漂移
- 🔧 **多引擎自动切换**：DeepL → 百度 → Google → MyMemory（质量优先），一个失败自动换下一个，并自动跳过连续失败的引擎
- 📋 **手动翻译窗口**：粘贴长段落批量翻译（Ctrl+Enter 快捷翻译）
- 🪶 **零第三方依赖**：只用 Python 标准库 + tkinter，无需 pip install
- 🖥 **高 DPI 适配**：高分屏（125%/150% 缩放）下界面清晰不发虚，现代浅色主题 + 圆角悬浮窗

## 快速开始

1. 安装 [Python 3](https://www.python.org/downloads/)（官方安装包默认自带 tkinter）
2. 双击 `run.bat` 启动

也可以命令行启动：`python main.py`

## 使用说明

| 操作 | 效果 |
| --- | --- |
| 勾选"划词即译"后，鼠标拖选文字松开 | 自动弹出翻译（无需按任何键） |
| 任意软件中选中文字，按 `Ctrl+C` | 自动弹出翻译（需勾选"自动翻译"） |
| 选中文字后直接按 `F8` | 自动复制并弹出翻译（无需按 Ctrl+C） |
| 按 `F9` | 开/关自动翻译 |
| 弹窗中按 `Esc` / 点击其他位置（取消选中） | 关闭弹窗（不再自动超时关闭） |
| 拖动弹窗顶部标题栏 | 手动移动弹窗位置 |
| 拖拽弹窗任意边或角 | 自由调整宽高（宽高独立变化，四边四角均可） |
| 译文超过窗口高度 | 鼠标滚轮在译文内滚动查看 |
| 弹窗中点"📌 固定" | 弹窗不自动关闭，方便对照 |
| 弹窗中点"📋 复制" | 复制译文（不会再触发翻译） |
| 主窗口"手动翻译"区 | 粘贴长段落翻译，Ctrl+Enter 快捷翻译 |
| 主窗口"编辑术语表" | 打开术语表文件，保存后立即生效 |

## 弹窗设计

- **位置稳定**：弹窗出现在选中文字末尾（或鼠标松开位置）附近，打开后位置即锁定，译文加载、窗口尺寸变化都不会导致弹窗跳动；靠近屏幕边缘时自动翻转方向，始终完整显示在当前显示器内（避开任务栏）；可拖动标题栏手动移动。
- **尺寸自适应**：宽度按内容长度分档（360 / 440 / 520 / 620 / 720 px，最多占屏幕宽度 55%），高度随译文行数自适应，最高占屏幕高度 60%，超出时在弹窗内滚动。
- **自由缩放**：拖拽弹窗的上、下、左、右边或四个角均可调整尺寸，宽高独立变化（不会锁死比例）；调整后译文自动重排，空间不足时可在译文内滚动。
- **排版可读**：中文为主的译文按字符换行，英文按单词换行；增加行距与段间距；原文摘要最多显示 2 行。

## 术语表（论文翻译的核心）

术语表是保证**术语译法准确且全文一致**的关键。示例：术语表里有 `transformer → Transformer 模型`，那么翻译 "The transformer architecture…" 时会先把 `transformer` 保护起来，翻译完再还原，绝不会译成"变压器"。

- 位置：应用目录下的 `glossary.txt`（点主窗口"编辑术语表"直接打开）
- 格式：每行一条 `英文<TAB>中文`（用 Tab 键分隔），`#` 开头为注释
- 已内置一批机器学习/深度学习常见术语示例，按你的研究方向增删即可

## 翻译引擎说明

默认按顺序尝试：**DeepL → 百度 → Google → MyMemory**，失败自动切换下一个；连续失败 2 次的引擎会在本次运行内被暂时跳过（重启后恢复），避免每次都等超时。

| 引擎 | 密钥 | 说明 |
| --- | --- | --- |
| DeepL 翻译 | 需要 | **学术翻译质量最优**，强烈推荐。在 [deepl.com](https://www.deepl.com/pro-api) 免费注册 API key（免费版 50 万字符/月），填入 `config.json` 的 `deepl_key`。网络已实测可达 |
| 百度翻译 | 需要 | 国内最稳。在 [fanyi-api.baidu.com](https://fanyi-api.baidu.com) 注册（个人实名认证有免费额度），填 `baidu_appid` / `baidu_secret` |
| Google 翻译 | 不需要 | 质量好，但中国大陆网络通常无法直连（需代理/VPN） |
| MyMemory | 不需要 | 免费备用引擎，适合短句 |

未配置密钥的引擎会自动跳过。可在主窗口"首选引擎"下拉框切换首选，或直接编辑 `config.json` 的 `engine_order`。

## config.json 配置项

| 配置 | 默认 | 说明 |
| --- | --- | --- |
| `auto_translate` | `true` | 复制文字后自动弹出翻译 |
| `select_translate` | `false` | 划词即译：拖选文字自动翻译 |
| `direction` | `"auto"` | `auto` 自动检测 / `zh2en` 中→英 / `en2zh` 英→中 |
| `primary_engine` | `"auto"` | 首选引擎：`auto` / `deepl` / `baidu` / `google` / `mymemory` |
| `engine_order` | `["deepl","baidu","google","mymemory"]` | 引擎尝试顺序 |
| `deepl_key` | `""` | DeepL API key |
| `baidu_appid` / `baidu_secret` | `""` | 百度翻译密钥 |
| `glossary_path` | `""` | 术语表路径，空 = 默认 `glossary.txt` |
| `segment_sentences` | `true` | 长文本按句分段翻译 |
| `segment_threshold` | `300` | 超过该字符数才分段 |
| `hotkey_translate` | `"f8"` | 翻译选中文字的热键 |
| `hotkey_toggle` | `"f9"` | 开关自动翻译的热键 |
| `popup_timeout` | `15` | 弹窗自动关闭秒数，`0` 为不自动关闭 |
| `max_text_length` | `1500` | 超过则截断 |
| `network_timeout` | `4` | 每个引擎的请求超时秒数 |

热键支持 `f1`-`f24`、`a`-`z`、`0`-`9`，可组合 `ctrl`/`alt`/`shift`/`win`，如 `"ctrl+shift+d"`。

## 打包成 exe（无需安装 Python）

已打包好的程序：**`dist\划词翻译.exe`**（单文件，约 12 MB，双击即可运行）。

重新打包：

1. 双击 **`build.bat`**（自动安装依赖并打包，约 1-2 分钟）
2. 产物输出到 `dist\划词翻译.exe`

打包说明：

- 单文件模式，首次启动约 1-2 秒（解压内置运行时）
- `config.json`、`glossary.txt`、`error.log` 会生成在 **exe 同目录**；若该目录不可写（如 Program Files），自动改用 `%APPDATA%\划词翻译`
- 打包默认**不带配置**，首次运行后需在配置里填 DeepL key
- 未签名的 exe 首次运行可能被 Windows SmartScreen 提示，点"更多信息 → 仍要运行"即可

## 常见问题

- **双击 run.bat 没反应？** 命令行运行 `python main.py` 看报错；错误记录在 `error.log`。
- **复制文字不弹窗？** 确认勾选了"自动翻译"（或按 `F9`）；剪贴板里是图片等非文字内容会忽略。
- **DeepL 用不了？** 检查 `deepl_key` 是否正确、是否超免费额度；失败会自动回退百度/MyMemory。
- **翻译失败？** 运行 `python main.py --selftest` 测试当前网络下哪些引擎可用。

## 开发与贡献

```bash
pip install -r requirements-dev.txt   # 仅打包/图标生成需要
python main.py --selftest             # 测试当前网络可用的翻译引擎
build.bat                             # 重新打包 exe
```

> 注意：`config.json` 含 API 密钥，已被 `.gitignore` 排除，请勿提交。

## 许可协议

本项目基于 [MIT License](LICENSE) 开源。
