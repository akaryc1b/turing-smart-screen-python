# 简体中文本地化架构说明

本文说明 `turing-smart-screen-python` 汉化 Fork 的语言选择、词库约束、资源加载和兼容原则。面向贡献者的具体流程见[简体中文贡献指南](contributing.md)，统一译法见[简体中文术语表](glossary.md)。

## 语言设置

`config.yaml` 使用稳定的界面语言值：

```yaml
config:
  LANGUAGE: auto
```

可选值：

- `auto`：优先读取环境变量 `TURING_LANGUAGE`，否则跟随操作系统语言；无法识别时回退到英文。
- `en_US`：英文。
- `zh_CN`：简体中文。

临时切换语言：

```bash
TURING_LANGUAGE=zh_CN python configure.py
```

Windows PowerShell：

```powershell
$env:TURING_LANGUAGE = "zh_CN"
python configure.py
```

打包后的 Windows portable 或安装版也使用同一变量：

```powershell
$env:TURING_LANGUAGE = "zh_CN"
.\configure.exe
```

## 显示文本与内部值分离

界面可以显示“自动选择”“正常方向”“公制”等中文文本，但写入 `config.yaml` 的值仍保持 `AUTO`、`false`、`metric` 等稳定格式。

这样可以避免：

- 切换语言后配置无法读取；
- 汉化版本生成的配置无法在上游英文版本中使用；
- 下拉框显示值被误当作内部枚举；
- 同步上游时产生不必要的协议兼容分支。

以下内容不得作为普通界面文本翻译：

```text
AUTO
TUR_USB
SIMU
DISPLAY_REVERSE
metric
imperial
standard
en_US
zh_CN
```

硬件 revision、协议命令、YAML schema、Python 标识符、环境变量和 API 参数同样保持原值。

## 翻译词库

词库文件：

```text
locales/en_US.json
locales/zh_CN.json
```

两份文件使用 UTF-8 JSON 和嵌套对象，代码通过点号键访问：

```python
from library.i18n import tr

tr("common.save_settings")
tr("config.author", name="someone")
```

当前质量门禁要求：

- 英文与中文词库扁平化后的键集合完全一致；
- 同一词条的命名占位符完全一致；
- 所有源码 `tr("key")` 均使用字符串字面量；
- 所有使用的键都存在；
- 词库中没有未使用键；
- 核心 Python UI 代码不直接嵌入用户可见中文。

运行时仍保留安全回退：请求的区域词条不可用时使用英文，英文也不可用时返回调用方默认文本或词条键。质量门禁的目标是让已提交词库在正常发布中不依赖这种兜底。

动态内容必须使用命名占位符，不应通过拼接翻译片段组成句子。

## 初始化位置

应用入口在创建用户界面前初始化语言：

- `configure.py`：配置向导；
- `main.py`：托盘、启动提示和运行时错误；
- `theme-editor.py`：主题编辑器。

业务模块通过 `library.i18n` 访问当前翻译器。语言初始化不得替换或重写窗口消息、信号退出、睡眠唤醒、托盘事件循环和队列清理逻辑。

## 源码与冻结资源

`library.resources` 提供统一资源根目录：

- 源码运行：仓库根目录；
- PyInstaller 运行：`sys._MEIPASS`。

发布包必须包含：

```text
locales/en_US.json
locales/zh_CN.json
res/themes/3.5inchTheme2-zh-CN/theme.yaml
res/themes/3.5inchTheme2-zh-CN/background.png
res/themes/3.5inchTheme2-zh-CN/preview.png
res/fonts/roboto-mono/RobotoMono-Regular.ttf
```

`tools/validate_release_bundle.py` 会对 Windows 正式版、Windows Debug 版和 Linux 版的真实 PyInstaller 目录进行验证，包括 `TURING_LANGUAGE=zh_CN` 的冻结词库加载。

## 中文字体与主题

中文示例主题位于独立目录：

```text
res/themes/3.5inchTheme2-zh-CN
```

中文标签使用：

- `system:cjk`
- `system:cjk-bold`

数值和 CPU、GPU、RAM、FPS 等缩写继续使用适合指标显示的字体和稳定拼写。系统没有可用 CJK 字体时，程序输出可操作提示并安全回退到随包提供的字体，不因字体缺失而崩溃。

主题目录不得提交字体二进制，也不得覆盖上游英文主题。

## Windows 安装器

安装器提供简体中文语言，并翻译 PawnIO 自定义页面。构建时：

1. 先使用 Inno Setup 的 `Default.isl` 为新消息提供英文 fallback；
2. 从固定提交下载维护者提供的简体中文翻译；
3. 验证下载文件的 Git blob SHA 和语言标记；
4. 编译并检查安装器输出。

下载生成的 `.isl` 文件不提交到仓库。

## 当前完成范围

当前汉化栈已经覆盖：

- 通用国际化模块和英文/简体中文词库；
- 配置向导及其子窗口；
- 系统托盘和运行时用户提示；
- 主题编辑器；
- PyInstaller 资源与发布包校验；
- Windows、Linux、macOS CJK 字体发现和回退；
- 独立中文示例主题；
- 简体中文安装器；
- 安装、配置、主题、字体、排障、同步、贡献和发布文档；
- 上游路径重叠报告和维护门禁。

## 验证

至少执行：

```bash
python -m unittest tests.test_i18n -v
python -m unittest tests.test_i18n_usage -v
python -m unittest tests.test_localization_maintenance -v
python -m unittest discover -s tests -t . -v
flake8
```

涉及发布时还要等待 `Release bundle validation`。只有 GitHub Actions 显示 `completed/success` 时，才能声明对应检查通过。
