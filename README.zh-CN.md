# turing-smart-screen-python 简体中文说明

> [!WARNING]
>
> 本项目是社区维护的开源替代软件，**不是 Turing、TURZX、玄方（XuanFang）、奇叶（Kipye）、WeAct Studio 或其他硬件厂商的官方软件**，也未获得这些厂商的授权、认可或背书。所有产品名、公司名和商标均归其各自权利人所有。
>
> 与厂商原版 `USBMonitor.exe`、`ExtendScreen.exe`、硬件质量或售后有关的问题，请联系对应厂商、官方论坛或销售商，不要作为本项目的软件缺陷提交。

`turing-smart-screen-python` 是由 [mathoudebine](https://github.com/mathoudebine) 发起的 GPL-3.0 开源项目，用 Python 为小型 USB-C IPS 屏幕提供跨平台系统监控程序和统一显示抽象层。

本简体中文版本基于上游项目持续维护，保留原作者版权、GPL-3.0 许可证和上游项目链接：

- 上游项目：<https://github.com/mathoudebine/turing-smart-screen-python>
- 本汉化 Fork：<https://github.com/akaryc1b/turing-smart-screen-python>
- 许可证：[GPL-3.0](LICENSE)

## 主要功能

- Windows、Linux、macOS 和 Raspberry Pi 上的系统监控显示。
- 图形化配置向导和 `config.yaml` 配置文件。
- CPU、GPU、内存、磁盘、网络、温度、风扇、FPS、天气、Ping、运行时间和自定义数据。
- 多种硬件协议的统一抽象，包括 UART、USB 和模拟显示模式。
- 基于 YAML 的主题系统、主题编辑器和截图预览。
- `auto`、`en_US`、`zh_CN` 界面语言，以及 `TURING_LANGUAGE` 环境变量。
- Windows、macOS、Linux 系统中文字体发现和回退。
- 独立中文示例主题 `3.5inchTheme2-zh-CN`，不会覆盖上游英文主题。

## 支持的硬件

当前上游支持范围包括：

- Turing Smart Screen / TURZX：2.1、2.8、3.5、4.6、5、5.2、8.0、8.8、9.2、12.3 英寸的多种硬件版本。
- XuanFang 3.5 英寸 revision B 与旗舰版。
- UsbPCMonitor 3.5 / 5 英寸。
- 奇叶智显（Kipye Qiye Smart Display）3.5 英寸。
- WeAct Studio Display FS V1 0.96 / 3.5 英寸。
- `SIMU` 模拟显示模式。

不同外观相似的屏幕可能使用完全不同的协议。购买或配置前请按上游的硬件版本说明确认型号，不要仅按屏幕尺寸判断。

## 文档导航

- [简体中文文档索引](docs/zh-CN/README.md)
- [安装说明](docs/zh-CN/installation.md)
- [配置向导与配置文件](docs/zh-CN/configuration.md)
- [主题制作与中文示例主题](docs/zh-CN/themes.md)
- [中文字体安装与字体别名](docs/zh-CN/fonts.md)
- [常见错误排查](docs/zh-CN/troubleshooting.md)
- [本地化架构说明](docs/zh-CN/LOCALIZATION.md)
- [简体中文贡献指南](docs/zh-CN/contributing.md)
- [Dependency Review 根因与维护边界](docs/zh-CN/dependency-review.md)
- [简体中文术语表](docs/zh-CN/glossary.md)
- [同步上游与处理分支冲突](docs/zh-CN/upstream-sync.md)
- [简体中文版本发布检查清单](docs/zh-CN/release-checklist.md)

## 快速开始

建议先安装 Python 3.9 或更高版本，并在虚拟环境中安装依赖：

```bash
python -m venv .venv
```

Windows PowerShell：

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python configure.py
```

Linux / macOS：

```bash
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python configure.py
```

配置完成后运行：

```bash
python main.py
```

没有连接真实屏幕时，可在配置向导中选择“模拟显示屏”，或将 `display.REVISION` 设置为 `SIMU`。程序会把画面写入 `screencap.png`，便于验证主题。

## 切换简体中文

配置向导中选择“简体中文”，或在 `config.yaml` 中设置：

```yaml
config:
  LANGUAGE: zh_CN
```

也可使用环境变量临时覆盖自动检测：

Windows PowerShell：

```powershell
$env:TURING_LANGUAGE = "zh_CN"
python configure.py
```

Linux / macOS：

```bash
TURING_LANGUAGE=zh_CN python configure.py
```

`LANGUAGE: auto` 时，程序按 `TURING_LANGUAGE`、系统区域设置和英文回退的顺序确定界面语言。翻译缺失时会回退到英文，不会把中文显示文本写入协议值、枚举值或稳定配置字段。

## 中文示例主题

在配置向导中选择：

```text
3.5inchTheme2-zh-CN
```

该主题使用：

- `system:cjk`：常规中文字体。
- `system:cjk-bold`：粗体中文字体。
- 仓库自带 Roboto Mono：CPU、GPU、FPS、百分比和速率等数值。

系统没有可用中文字体时，程序会输出明确提示并安全回退，不会因为主题字体缺失而直接崩溃。安装建议见[中文字体说明](docs/zh-CN/fonts.md)。

## 开源与贡献

本项目遵循 GPL-3.0。再分发修改版时必须保留许可证、原作者版权声明和对应源代码义务。

汉化实现遵循以下兼容原则：

- 不翻译硬件协议、硬件修订号、API 参数、天气语言代码和程序标识符。
- `AUTO`、`TUR_USB`、`SIMU`、`DISPLAY_REVERSE`、`metric`、`imperial`、`standard` 等稳定值保持不变。
- 英文默认行为和社区主题格式保持兼容。
- 汉化功能通过堆叠 Draft PR 开发，不自动合并。

提交翻译、中文主题、打包或维护改动前，请阅读[本地化架构说明](docs/zh-CN/LOCALIZATION.md)、[简体中文贡献指南](docs/zh-CN/contributing.md)和[简体中文术语表](docs/zh-CN/glossary.md)。准备发布时使用[发布检查清单](docs/zh-CN/release-checklist.md)，同步上游前先生成路径重叠报告。
