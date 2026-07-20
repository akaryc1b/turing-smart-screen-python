# 简体中文本地化覆盖率审计

本仓库使用 `tools/localization_coverage.py` 对翻译目录、翻译键引用、格式占位符和可能面向用户的硬编码文本进行可重复审计。审计只约束显示给用户的文字，不改变 USB、串口、设备识别、协议指令、硬件 revision 或配置文件中的稳定内部值。

## 什么属于用户可见文本

下列内容通常应使用 `tr("key")` 或安装器的本地化消息：

- Tk/ttk 窗口标题、标签、按钮、菜单和提示框文本；
- 配置向导与主题编辑器直接展示的说明和错误；
- Inno Setup 类型、组件、任务和运行页面中的说明；
- 明确会直接显示给用户的普通英文句子。

`print(...)` 与 `logger.error(...)`、`logger.warning(...)` 可能既用于终端用户，也可能只是诊断信息。静态分析无法确认时会记录为 warning，供维护者人工判断，不会仅因 warning 阻断 CI。

## 必须保持稳定的内部值

以下内容不是翻译目标，不能为了中文界面而改写：

- `AUTO`、`STATIC`、`SIMU`、`TUR_USB`、`LHM` 等协议或配置枚举；
- `metric`、`imperial`、`standard` 等 API 与配置值；
- 设备 revision、串口/USB 标识、协议命令和配置键；
- URL、文件路径、文件名、环境变量和 PyInstaller 参数；
- CPU、GPU、FPS、Wi-Fi、产品名、协议名等技术文本。

界面需要展示这些选项时，应保留内部值作为映射键，并通过翻译目录提供显示标签。审计会把直接作为 UI 文本使用的稳定内部值列为 error。

## 运行方式

生成 JSON 报告：

```bash
python tools/localization_coverage.py \
  --format json \
  --output localization-coverage.json
```

生成 Markdown 报告：

```bash
python tools/localization_coverage.py \
  --format markdown \
  --output localization-coverage.md
```

在存在 error 时返回非零状态：

```bash
python tools/localization_coverage.py \
  --format json \
  --output localization-coverage.json \
  --fail-on-errors
```

可使用 `--repository-root` 指定仓库根目录，使用 `--allowlist` 指定允许列表。默认允许列表为 `tools/localization-allowlist.json`。

## 报告严重性

- **error**：会使 `--fail-on-errors` 和 CI 失败，例如中英文目录缺键、引用不存在的键、占位符不一致、损坏的格式字符串、确定属于 UI 的硬编码英文、安装器缺少中文消息、UI 直接展示内部值，以及失效或过宽的允许项。
- **warning**：需要人工复核但不会单独阻断 CI，例如动态生成的翻译键、可能未使用的键，以及无法静态判断是否面向用户的终端或日志文本。
- **info**：已由精确允许列表解释并匹配的例外。

CI 生成的 `localization-coverage.json` 和 `localization-coverage.md` 只作为 GitHub Actions artifact 保留 14 天，不提交到 Git。根目录 `.gitignore` 会忽略这两个生成报告。

## 新增或修改翻译键

1. 同时更新 `locales/en_US.json` 与 `locales/zh_CN.json`。
2. 使用相同的扁平化键，例如 `config.save_button`。
3. 调用处使用静态字符串键，例如 `tr("config.save_button")`。
4. 不依赖英文 fallback 掩盖中文缺键；两个目录的键集合必须完全一致。
5. 运行覆盖率工具和完整测试：

```bash
python -m unittest tests.test_localization_coverage -v
python -m unittest discover -s tests -t . -v
```

## 占位符规则

工具解析 Python format 占位符，包括名称、转换、格式说明符和嵌套格式字段。中英文可以调整字段顺序，但必须保留兼容的字段和格式，例如：

```text
{name}
{size}
{error}
{status}
{x:.0f}
{value:{width}}
```

中文条目遗漏字段、修改字段名、丢失格式说明符或包含未闭合花括号都会成为 error。

## 精确允许列表

只有确认应保留英文或技术形式的文本才可加入 `tools/localization-allowlist.json`。每项必须包含：

- 精确的仓库相对路径；
- 精确的规则名；
- 精确的 `key` 或 `value`，二选一；
- 类型，例如 `technical-term`、`stable-internal-value`、`protocol`、`path`、`url`、`log-only` 或 `product-name`；
- 可审计的允许原因。

禁止 `.*`、glob、目录级或整文件跳过。允许项必须恰好匹配一个当前 finding；不再匹配会成为 `allowlist-unused` error，匹配多个 finding 会成为 `allowlist-broad` error。

## GitHub Actions

`.github/workflows/localization-coverage.yml` 在相关 pull request 和手动 `workflow_dispatch` 时运行，使用只读 `contents: read` 权限。流程先执行语法检查和单元测试，再生成并上传 JSON/Markdown 报告，最后只按 error 数量决定成功或失败。

Dependency Review 仍由独立 workflow 使用 `actions/dependency-review-action@v5` 执行。本仓库作为 GitHub Fork 时出现的平台限制与本覆盖率审计无关，不得通过 `continue-on-error`、warn-only、恒假条件或路径忽略来弱化 Dependency Review。
