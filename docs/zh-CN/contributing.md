# 简体中文贡献指南

本文补充上游英文 [`CONTRIBUTING.md`](../../CONTRIBUTING.md)，用于维护本 Fork 的简体中文界面、词库、主题、字体回退、打包和中文文档。通用行为准则、缺陷报告要求和 GPL-3.0 许可要求仍以上游文档为准。

## 贡献前须知

- 本项目是社区维护的非官方软件，不代表任何硬件厂商。
- 提交内容必须由贡献者合法提供，并可按 GPL-3.0 分发。
- 必须保留上游作者、版权、许可证、项目链接和第三方归属说明。
- 不要把厂商软件、固件、字体或其他无明确再分发许可的二进制文件提交到仓库。
- 汉化提交不得顺手重构硬件协议、采集逻辑或生命周期代码。

## 推荐开发流程

1. 配置 Fork 和上游远程：

   ```bash
   git remote add upstream https://github.com/mathoudebine/turing-smart-screen-python.git
   git fetch upstream --prune
   ```

2. 从当前汉化栈的正确父分支创建功能分支，不要默认从 `main` 创建后续阶段。
3. 修改前生成上游同步报告：

   ```bash
   python tools/upstream_sync_report.py \
     --upstream-ref upstream/main \
     --local-ref HEAD \
     --output upstream-sync-report.md
   ```

4. 一个 PR 只处理一个清晰主题，并先创建 Draft PR。
5. 在 PR 描述中记录实际执行的测试和 GitHub Actions 状态，不把“已触发”写成“已通过”。

## 用户可见文本

用户可见文本应进入翻译词库，并通过 `tr("key")` 使用：

```python
from library.i18n import tr

window.title(tr("app.configuration_title"))
```

新增词条时：

1. 在 `locales/en_US.json` 中加入英文默认文本。
2. 在 `locales/zh_CN.json` 中加入对应中文。
3. 保持两份词库扁平化后的键集合完全一致。
4. 保持命名占位符完全一致。
5. 使用字符串字面量作为 `tr()` 的键，便于静态分析。

示例：

```json
{
  "error": {
    "file_missing": "File not found: {path}"
  }
}
```

中文必须继续使用同名占位符：

```json
{
  "error": {
    "file_missing": "未找到文件：{path}"
  }
}
```

不要：

- 在核心 Python 文件中直接写用户可见中文。
- 动态拼接翻译键。
- 在中文词条中删除、重命名或改变占位符。
- 为了消除“未使用词条”测试而建立永久白名单。

## 不应翻译的内容

以下内容是协议值、配置值、标识符或行业缩写，应保持稳定：

- `AUTO`、`TUR_USB`、`SIMU`、`DISPLAY_REVERSE`
- `metric`、`imperial`、`standard`
- `en_US`、`zh_CN`、天气 API 语言代码
- 硬件 revision 字母和设备协议命令
- YAML schema 键、Python 标识符、文件名和环境变量名
- CPU、GPU、RAM、FPS、USB、UART、HID、API、URL、COM

界面可以翻译显示标签，但保存到 `config.yaml` 的内部值必须保持原样。术语选择参见[简体中文术语表](glossary.md)。

## 配置向导与运行时

修改 `configure.py`、`main.py` 或 `theme-editor.py` 时，先保留上游行为，再接入翻译。

重点检查：

- 显示文本到内部配置值的双向映射。
- Windows 窗口消息、睡眠和唤醒处理。
- POSIX 信号退出和队列清理。
- 托盘菜单、macOS 阻塞事件循环和屏幕关闭。
- 主题编辑器坐标换算、缩放、文件刷新和异常处理。

内部调试日志通常保持英文，只有明确面向最终用户的提示才进入词库。

## 主题与字体

- 中文示例主题必须使用独立目录，不覆盖上游英文主题。
- 中文静态标签使用 `system:cjk` 或 `system:cjk-bold`。
- 数值和通用缩写可继续使用随项目提供的 Roboto Mono。
- 不向主题目录提交字体二进制。
- 更新主题后验证图片格式、分辨率、坐标边界和截图。
- 缺少系统 CJK 字体时必须安全回退，并提供可操作提示。

## 打包与安装器

修改 `.spec`、资源解析或发布流程时必须确认：

- `locales/en_US.json` 和 `locales/zh_CN.json` 进入所有 PyInstaller 入口。
- 中文主题 YAML、背景图和预览图进入发布包。
- Windows 正式版、Windows Debug 版和 Linux 包都运行 `tools/validate_release_bundle.py`。
- Windows 安装器保留简体中文语言和 PawnIO 中文说明。
- 外部安装器翻译必须固定到不可变提交并校验内容，不跟随远端可变分支。
- 发布前不应把构建目录、编译日志、下载生成文件或临时工作流提交到仓库。

## 文档贡献

- 中文文档使用 UTF-8。
- 保留命令、路径、配置键和协议值的原始拼写。
- 相对链接应从当前文档位置正确解析。
- 不把尚未验证的功能描述成已支持。
- 涉及发布或 CI 的结论应注明具体 workflow 和实际状态。
- 新增中文文档后更新[中文文档索引](README.md)和根目录 `README.zh-CN.md`。

## 必须执行的检查

至少运行：

```bash
python -m py_compile \
  main.py configure.py theme-editor.py \
  library/i18n.py library/fonts.py library/resources.py \
  tools/upstream_sync_report.py

python -m unittest tests.test_i18n -v
python -m unittest tests.test_i18n_usage -v
python -m unittest tests.test_packaged_resources -v
python -m unittest tests.test_font_discovery -v
python -m unittest tests.test_chinese_theme -v
python -m unittest tests.test_release_validation -v
python -m unittest tests.test_upstream_sync_report -v
python -m unittest tests.test_localization_maintenance -v
python -m unittest discover -s tests -t . -v
flake8
```

涉及打包时还应等待 `Release bundle validation` 完成。完整发布前按[发布检查清单](release-checklist.md)逐项确认。

## PR 审查清单

- [ ] PR base 指向正确的前置分支。
- [ ] Diff 仅包含本阶段文件。
- [ ] 没有硬编码用户可见中文。
- [ ] 英文和中文词库键、占位符一致。
- [ ] 稳定内部值未翻译。
- [ ] 上游生命周期和协议行为未被意外重写。
- [ ] 没有新增无许可字体或厂商二进制。
- [ ] 本地测试与 GitHub Actions 状态记录准确。
- [ ] Dependency Review、CodeQL 等检查没有被删除或弱化。
- [ ] PR 保持 Draft，除非维护者明确决定进入审查或合并流程。
