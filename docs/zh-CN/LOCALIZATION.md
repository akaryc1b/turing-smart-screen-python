# 简体中文本地化说明

本分支用于将 `turing-smart-screen-python` 的用户界面、提示信息、托盘菜单、主题编辑器和使用文档完整汉化，同时保留与上游项目同步的能力。

## 语言设置

`config.yaml` 中新增了界面语言设置：

```yaml
config:
  LANGUAGE: auto
```

可选值：

- `auto`：优先读取环境变量 `TURING_LANGUAGE`，否则跟随操作系统语言；无法识别时回退到英文。
- `en_US`：英文。
- `zh_CN`：简体中文。

临时切换语言也可以使用环境变量：

```bash
TURING_LANGUAGE=zh_CN python configure.py
```

Windows PowerShell：

```powershell
$env:TURING_LANGUAGE = "zh_CN"
python configure.py
```

## 设计原则

### 显示文本与配置值分离

界面可以显示“自动选择”“正常方向”“公制”等中文文本，但写入 `config.yaml` 的值仍保持 `AUTO`、`false`、`metric` 等稳定格式。

这样可以避免以下问题：

- 切换语言后配置无法读取；
- 汉化版本生成的配置无法在上游英文版本中使用；
- 下拉框显示值被误当作内部枚举；
- 后续同步上游代码时产生不必要的兼容性分支。

### 英文回退

`locales/zh_CN.json` 可以只覆盖需要翻译的词条。缺失的中文词条会自动使用 `locales/en_US.json`，两者都不存在时返回词条键名或调用方给出的默认文本。

### 词条格式

词条文件使用 UTF-8 JSON，并支持嵌套结构。代码通过点号键访问：

```python
from library.i18n import tr

tr("common.save_settings")
tr("config.author", name="someone")
```

动态内容必须使用命名占位符，不应通过拼接翻译片段组成句子。

## 当前阶段

本阶段包含：

- 通用国际化模块；
- 英文基础词库；
- 简体中文词库；
- 系统语言和环境变量识别；
- 英文回退与格式化保护；
- `config.yaml` 的界面语言配置；
- 国际化单元测试；
- 修复 2.8 英寸圆形 USB 屏幕常量命名错误。

后续阶段将依次接入：

1. 配置向导主窗口；
2. 天气与 Ping 配置窗口；
3. 系统托盘；
4. 主题编辑器；
5. 启动错误、警告和面向用户的日志；
6. 中文字体检测及内置主题适配；
7. 中文安装、配置、主题制作和故障排除文档。

## 新增词条检查

新增用户可见文本时，应同时执行：

```bash
python -m unittest tests.test_i18n -v
```

不得把中文直接硬编码进业务逻辑，也不得翻译协议名称、配置键、硬件修订号或 API 参数。
