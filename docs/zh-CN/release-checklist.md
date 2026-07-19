# 简体中文版本发布检查清单

本清单用于发布包含简体中文界面、中文主题和本地化安装器的版本。它不替代上游发布流程，而是补充汉化 Fork 的资源、兼容性和可追溯性检查。

## 1. 确认发布范围

- [ ] 发布分支基于计划中的上游版本或提交。
- [ ] 已记录上游项目、上游提交和本 Fork 发布提交。
- [ ] 发布说明区分上游功能、Fork 汉化功能和本次新增内容。
- [ ] 没有把未完成的 Draft PR 内容误纳入发布分支。
- [ ] 没有修改或删除 GPL-3.0、作者版权、非官方声明和商标归属。

## 2. 检查上游同步风险

更新上游引用：

```bash
git fetch upstream --prune
```

生成同步报告：

```bash
python tools/upstream_sync_report.py \
  --upstream-ref upstream/main \
  --local-ref HEAD \
  --output upstream-sync-report.md
```

需要把路径重叠作为阻塞条件时：

```bash
python tools/upstream_sync_report.py \
  --upstream-ref upstream/main \
  --local-ref HEAD \
  --fail-on-overlap
```

- [ ] 已人工审查所有 high 风险重叠路径。
- [ ] 已确认报告表示路径重叠，而不是自动证明语义冲突。
- [ ] `main.py`、`configure.py`、`theme-editor.py` 的上游生命周期行为已保留。
- [ ] 上游主题 schema、`.spec` 和发布工作流变化已同步评估。

## 3. 词库与界面

- [ ] `locales/en_US.json` 和 `locales/zh_CN.json` 均为 UTF-8 合法 JSON。
- [ ] 两份词库扁平化后的键集合完全一致。
- [ ] 每个词条的命名占位符一致。
- [ ] 所有 `tr("key")` 均使用字符串字面量并存在于词库。
- [ ] 没有未使用词条。
- [ ] 核心 Python UI 代码没有硬编码用户可见中文。
- [ ] `AUTO`、`SIMU`、单位值、revision 和其他稳定内部值未被翻译。
- [ ] 配置向导、托盘、主题编辑器和启动错误提示已手工检查中文布局。

## 4. 中文主题与字体

- [ ] `3.5inchTheme2-zh-CN` 仍是独立主题目录。
- [ ] `theme.yaml` 仍针对 3.5 英寸 portrait 画面。
- [ ] `background.png` 和 `preview.png` 是有效的 320×480 PNG。
- [ ] 所有静态图片引用存在。
- [ ] 中文静态标签使用 `system:cjk` 或 `system:cjk-bold`。
- [ ] CPU、GPU、RAM、FPS 等缩写保持稳定。
- [ ] 主题目录不包含字体二进制。
- [ ] Windows、Linux 和 macOS 的字体发现与缺失字体回退测试通过。
- [ ] Theme Screenshot 工作流成功生成并验证中文主题截图。

## 5. 本地测试

```bash
python -m py_compile \
  main.py configure.py theme-editor.py \
  library/config.py library/fonts.py library/i18n.py library/resources.py \
  tools/validate_release_bundle.py tools/upstream_sync_report.py

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

- [ ] 所有命令以退出码 0 完成。
- [ ] 没有通过删除测试、跳过真实失败或建立无依据白名单来变绿。

## 6. 发布包

等待 `Release bundle validation` 完成，并确认：

- [ ] Linux release bundle 构建和内容验证成功。
- [ ] Windows release bundle 构建和内容验证成功。
- [ ] Windows Debug bundle 构建和内容验证成功。
- [ ] 打包词库可通过 `TURING_LANGUAGE=zh_CN` 从冻结资源根目录加载。
- [ ] 中文主题 YAML、背景图、预览图和 Roboto Mono 回退字体存在。
- [ ] `config.yaml`、`external`、`res/fonts`、`res/themes` 和入口程序存在。
- [ ] 缺少系统 CJK 字体时，冻结包安全回退而不崩溃。

## 7. Windows 安装器

- [ ] 安装器包含简体中文语言选项。
- [ ] PawnIO 自定义页面的标题、说明、复选框和错误信息可显示中文。
- [ ] `compiler:Default.isl` 作为新消息的英文 fallback。
- [ ] 简体中文翻译从固定提交下载，不跟随可变分支。
- [ ] 下载文件的 Git blob SHA 和必要语言标记验证成功。
- [ ] Inno Setup 编译成功并生成预期文件名。
- [ ] 正式版安装器和 Debug 安装器的发布工作流都调用语言准备脚本。
- [ ] 升级安装默认不覆盖用户主题和配置。
- [ ] portable 包要求完整目录，不把单个 EXE 当作完整发布物。

## 8. GitHub Actions

只有 GitHub 报告 `completed/success` 时才能勾选：

- [ ] Localization。
- [ ] Lint with flake8。
- [ ] Linux / Windows / macOS System Monitor。
- [ ] Linux / Windows / macOS Simple Program。
- [ ] System monitor themes screenshot。
- [ ] Release bundle validation。
- [ ] CodeQL；仅在当前 PR 或提交符合其触发条件时要求。
- [ ] Dependency Review。

Dependency Review 或 CodeQL 未触发、失败或权限不足时，应在发布记录中准确说明。不要删除或弱化安全工作流。

## 9. 发布产物检查

- [ ] Windows 安装器可以启动并选择简体中文。
- [ ] Windows portable 包完整解压后可以运行配置向导。
- [ ] Linux 归档完整解压后可以运行 `./configure` 或 `./turing-smart-screen`。
- [ ] Debug 版本保留控制台输出。
- [ ] 发布包中没有 `build/`、测试日志、临时 workflow 或本地同步报告。
- [ ] 发布包和源码归档保留许可证、作者与上游链接。
- [ ] 发布说明列出已知限制和未通过的检查。

## 10. 发布后

- [ ] 从发布页重新下载每个产物并校验文件可读。
- [ ] 使用 `TURING_LANGUAGE=zh_CN` 完成一次配置向导启动。
- [ ] 使用 `SIMU` 和 `STATIC` 完成一次无硬件烟雾测试。
- [ ] 确认中文主题生成 `screencap.png` 且没有缺字方框。
- [ ] 记录发布提交 SHA、Actions run 和产物名称。
- [ ] 新发现的问题进入后续 Draft PR，不直接重写已发布 tag。
