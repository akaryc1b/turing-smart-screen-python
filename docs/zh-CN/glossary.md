# 简体中文术语表

本文统一项目界面和中文文档中的常用术语。代码标识符、协议值、配置键和行业缩写不受中文表达影响，仍按原始拼写保存。

## 推荐术语

| English | 推荐中文 | 使用说明 |
| --- | --- | --- |
| configuration wizard | 配置向导 | 指 `configure.py` 图形界面 |
| configuration file | 配置文件 | 通常指 `config.yaml` |
| system monitor | 系统监控程序 | 指主程序或其运行模式 |
| theme | 主题 | 指 YAML 布局及其静态资源 |
| theme editor | 主题编辑器 | 指 `theme-editor.py` |
| system tray | 系统托盘 | 简写“托盘”也可 |
| hardware revision | 硬件修订版 | revision 字母本身保持 A/B/C/D 等原值 |
| display orientation | 屏幕方向 | portrait、landscape 等内部值不翻译 |
| fallback | 回退 | 指语言、字体或资源不可用时的替代路径 |
| locale | 区域与语言设置 | 语言代码仍写作 `en_US`、`zh_CN` |
| translation catalog | 翻译词库 | 指 `locales/*.json` |
| bundle | 打包产物 | 指 PyInstaller 输出目录或归档前内容 |
| release artifact | 发布产物 | 指安装器、压缩包等最终文件 |
| portable package | portable 便携版 | 文件名中的 `portable` 保持英文 |
| debug package | Debug 调试版 | 文件名和构建标识保持 `debug` |
| upstream | 上游 | 指 `mathoudebine/turing-smart-screen-python` |
| fork | Fork | 文档中可写“本 Fork” |
| stacked pull request | 堆叠 PR | 每个 PR 的 base 指向前置分支 |
| merge base | 共同基线 | Git 中两条历史的共同祖先 |
| overlap | 重叠路径 | 不等同于已发生语义冲突 |
| placeholder | 占位符 | 如 `{path}`，中英文必须一致 |
| font discovery | 字体发现 | 查找系统已安装字体的过程 |
| font alias | 字体别名 | 如 `system:cjk` |
| screenshot workflow | 主题截图工作流 | GitHub Actions 中生成模拟截图的流程 |

## 保持原样的缩写

以下缩写一般不翻译，也不要在主题中改成全角字符：

- CPU
- GPU
- RAM
- FPS
- USB
- UART
- HID
- API
- URL
- COM
- IP
- DNS
- YAML
- JSON
- PNG
- GPL

中文可解释其含义，但界面指标名、配置值、文件名和协议字段继续使用原缩写。

## 保持原样的内部值

以下示例是程序内部值，不是界面翻译文本：

```text
AUTO
TUR_USB
SIMU
STATIC
PYTHON
LHM
DISPLAY_REVERSE
metric
imperial
standard
auto
en_US
zh_CN
portrait
landscape
reverse_portrait
reverse_landscape
```

显示给用户时可以使用中文标签，但写回配置或传入协议时必须使用稳定原值。

## 中文排版约定

- 中文句子使用全角标点。
- 命令、路径、环境变量、配置键和代码使用反引号。
- 中文与英文缩写或数字之间保留一个半角空格，例如“CPU 温度”“Python 3.13”。
- 不翻译代码块中的实际命令参数。
- 文件名与发布产物名保持实际大小写。
- 错误信息中的动态值使用命名占位符，不用位置占位符替代。

## 词条命名

翻译键使用稳定、语义化的英文层级：

```text
app.configuration_title
tray.open_configuration
error.font_missing
```

不要把英文句子直接作为键，也不要把中文、平台名或当前版本号写进键名。复用词条前先确认语境和占位符完全一致，避免为减少键数量而产生含义模糊的翻译。
