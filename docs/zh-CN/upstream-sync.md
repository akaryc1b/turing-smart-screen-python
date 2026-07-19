# 同步上游与处理汉化分支冲突

本汉化 Fork 持续跟踪：

```text
mathoudebine/turing-smart-screen-python
```

推荐为本地仓库保留两个远程：

```bash
git remote -v
git remote add upstream https://github.com/mathoudebine/turing-smart-screen-python.git
git fetch upstream --prune
```

常见约定：

- `origin`：自己的 Fork `akaryc1b/turing-smart-screen-python`。
- `upstream`：原项目 `mathoudebine/turing-smart-screen-python`。

## 当前堆叠分支结构

功能阶段继续使用逐层堆叠 Draft PR：

```text
main
└── agent/zh-cn-i18n-foundation          # PR #1
    └── agent/zh-cn-configurator         # PR #2
        └── agent/zh-cn-runtime-editor   # PR #3
            └── agent/zh-cn-packaging    # PR #4
                └── agent/zh-cn-font-support       # PR #5
                    └── agent/zh-cn-theme-docs     # PR #6
                        └── agent/zh-cn-release-validation  # PR #7
                            └── agent/zh-cn-maintenance      # PR #8
                                └── agent/zh-cn-security-ci  # PR #9
```

累计与兼容审查分支使用另一条清晰链路：

```text
main
└── agent/zh-cn-integration-review       # PR #10，累计目标为 main
    └── agent/zh-cn-upstream-compat      # PR #11，基于累计分支
```

`agent/zh-cn-integration-review` 从 PR #9 的最终 Head 创建，但 PR base 是 `main`，用于触发 CodeQL 和面向主分支的累计保护规则。`agent/zh-cn-upstream-compat` 的 base 必须保持为累计集成分支，避免把兼容审计误混入 PR #9 的阶段 diff。

每个阶段只包含一个清晰目标。前置 PR 未合并时，不要随意把后续堆叠 PR 改为 `main`，否则会把所有前置提交重复显示在 diff 中。重建父分支历史后，应保证后续分支真正以新 Head 为祖先，而不只是复制相同文件内容。

## 生成上游同步报告

`tools/upstream_sync_report.py` 会：

1. 验证上游和本地 ref。
2. 自动计算共同基线；也可以显式指定 merge base。
3. 分别收集共同基线到上游、本地汉化分支的改动路径。
4. 计算两侧都修改过的路径。
5. 按词库、运行时、打包、主题、文档和测试分类并标记风险。

先获取最新上游引用：

```bash
git fetch upstream --prune
```

生成 Markdown 报告：

```bash
python tools/upstream_sync_report.py \
  --upstream-ref upstream/main \
  --local-ref HEAD \
  --format markdown \
  --output upstream-sync-report.md
```

生成 JSON：

```bash
python tools/upstream_sync_report.py \
  --upstream-ref upstream/main \
  --local-ref HEAD \
  --format json \
  --output upstream-sync-report.json
```

在自动流程中把路径重叠视为需要人工处理的状态：

```bash
python tools/upstream_sync_report.py \
  --upstream-ref upstream/main \
  --local-ref HEAD \
  --fail-on-overlap
```

退出码：

- `0`：报告成功，且未要求因重叠失败。
- `1`：仓库、ref 或 Git 命令无效。
- `2`：报告成功，但 `--fail-on-overlap` 检测到重叠路径。

> 同步报告检测的是“路径级重叠”，不是语义冲突证明。没有重叠不代表行为一定兼容；存在重叠也不代表应无条件保留 Fork 版本。

报告文件属于临时审查工件，不应提交到功能 PR。分析结束后确认：

```bash
git status --short
```

输出中不得出现 `upstream-sync-report.md`、`upstream-sync-report.json` 或临时审计 workflow。

## 2026-07-19 上游兼容审计记录

本次审计在 GitHub-hosted Ubuntu Runner 上实际获取上游远程，并对累计汉化 Head 执行了上述 Markdown 和 JSON 命令。

记录的引用：

- 上游 `main` Head：`a3a375dbfe52ae8ee48349cb6ff476c4767a232a`。
- Fork `main` Head：`a3a375dbfe52ae8ee48349cb6ff476c4767a232a`。
- 汉化累计 Head：`6fb4dc5f8cb5dfea02f47e3c8ac23e999f526e93`。
- 共同基线：`a3a375dbfe52ae8ee48349cb6ff476c4767a232a`。

机器报告结果：

- 上游变化路径：0。
- 汉化变化路径：57。
- 路径级重叠：0。
- 汉化路径状态：新增 35、修改 22。

由于上游 `main` 与 Fork `main` 完全一致，本次不存在上游新增路径，也不存在需要合并的路径级重叠。以下重点路径均没有“共同基线到上游”的新改动：

- `main.py`
- `configure.py`
- `theme-editor.py`
- `library/config.py`
- `library/i18n.py`
- `library/fonts.py`
- `library/resources.py`
- `turing-system-monitor.spec`
- `turing-system-monitor-debug.spec`
- 发布 workflow
- Windows 安装器
- 主题 schema 与中文主题

因此本次没有上游新增用户可见文本需要补入 `locales/en_US.json` 或 `locales/zh_CN.json`，也没有上游生命周期、协议或 UI 结构变化需要重新接入翻译。

这只说明审计时点没有新的上游提交。累计汉化仍必须通过 CodeQL、Localization、flake8、三平台 System Monitor、三平台 Simple Program、主题截图和发布包验证。审计生成的 Markdown、JSON、元数据和临时 workflow 均不进入最终 diff。

## 同步上游 main

先更新本地上游引用：

```bash
git fetch upstream --prune
```

在 Fork 的 `main` 上同步时，优先保留上游提交历史。团队采用 merge commit 时：

```bash
git switch main
git merge --no-ff upstream/main
git push origin main
```

采用 rebase 时：

```bash
git switch main
git rebase upstream/main
git push --force-with-lease origin main
```

已经有多人使用的共享分支不要随意 rebase。`--force-with-lease` 也不能替代团队确认。

## 更新堆叠分支

前置 PR 合并后，后续分支有两种稳妥处理方式。

### 方法一：仅更新 PR base

如果后续分支历史已经包含合并后的相同提交，直接把 PR base 改为新的正确分支或 `main`，然后确认 GitHub diff 只剩本阶段文件。

### 方法二：重建后续分支祖先关系

```bash
git switch agent/zh-cn-runtime-editor
git rebase --onto agent/zh-cn-configurator <旧父提交> agent/zh-cn-runtime-editor
git push --force-with-lease origin agent/zh-cn-runtime-editor
```

对下一层重复执行。操作前记录每个分支 Head SHA，避免把堆叠关系改乱。完成后逐个检查：

- PR base SHA 等于前一阶段当前 Head。
- 分支相对 base 为 ahead 且 behind 为 0。
- changed files 只属于当前阶段。
- PR 仍为 Open Draft，未合并且未启用 auto-merge。

仅把相同文件内容复制到后续分支，不能替代正确的 Git 祖先关系。

## 处理翻译冲突

### 词库冲突

`locales/en_US.json` 和 `locales/zh_CN.json` 必须满足：

- JSON 合法且为 UTF-8。
- 两份词库扁平化后的键集合完全一致。
- 同一键的命名占位符完全一致。
- 新英文原文先进入 `en_US.json`，再提供中文翻译。
- 删除键前确认源码中没有 `tr("key")` 使用。
- 术语符合[简体中文术语表](glossary.md)。

不要仅选择“ours”或“theirs”覆盖整份词库。应按键合并并运行国际化测试。

### 配置向导冲突

上游修改控件时：

1. 先保留上游控件结构、回调、内部值和保存逻辑。
2. 再把用户可见文本接入 `tr()`。
3. 检查显示文本到内部值的映射仍然双向正确。
4. 确认中文没有写入 `AUTO`、单位值、修订号、天气语言代码等配置字段。

### 运行时冲突

`main.py` 冲突需特别检查：

- Windows 控制台事件和窗口消息处理。
- `WM_POWERBROADCAST`、`WM_QUIT`、睡眠和唤醒。
- POSIX 信号退出。
- 调度队列清空和屏幕关闭。
- 托盘启动、配置、退出和 macOS 阻塞运行。
- 原有英文开发日志。

汉化只应更改用户可见文字和语言初始化，不应重写这些生命周期逻辑。

### 主题编辑器冲突

保留上游：

- 鼠标坐标换算。
- 区域绘制。
- 缩放比例。
- 文件自动刷新。
- 主题异常处理。
- Windows、macOS、Linux 打开文件方式。

只把窗口标题、按钮、坐标提示和命令行帮助接入词库。

### 打包与发布冲突

上游修改 `.spec`、安装器或发布工作流后，确认：

- `locales` 仍进入所有入口的 PyInstaller `datas`。
- 打包产物复制完整资源目录。
- `library.resources` 仍是源码模式和 `_MEIPASS` 的统一解析入口。
- Windows 安装器没有排除 `locales`。
- Windows 正式版、Debug 版和 Linux 包仍运行 `tools/validate_release_bundle.py`。
- 简体中文安装器翻译仍固定到不可变提交并验证 Git blob。
- `Release bundle validation` 仍构建真实产物而不只检查 YAML 或 spec 文本。
- 最终 workflow 不上传编译日志或其他诊断工件。

### 主题冲突

中文主题是独立目录，通常不会与上游英文主题冲突。上游改变主题 schema 时：

1. 对比 `res/themes/default.yaml` 和 `theme_example.yaml`。
2. 把新增必需节点加入中文主题。
3. 运行模拟显示和主题截图。
4. 不直接覆盖上游原主题目录。

## 冲突解决后的验证

至少执行：

```bash
python -m py_compile \
  main.py configure.py theme-editor.py \
  library/i18n.py library/fonts.py library/resources.py \
  tools/validate_release_bundle.py tools/upstream_sync_report.py

python -m unittest tests.test_i18n -v
python -m unittest tests.test_i18n_usage -v
python -m unittest tests.test_upstream_sync_report -v
python -m unittest tests.test_localization_maintenance -v
python -m unittest discover -s tests -t . -v
flake8
```

涉及打包时还要运行或等待：

- `Release bundle validation`。
- Windows / Linux 发布工作流的 bundle 校验步骤。
- 本地化 Windows 安装器编译。

并检查 GitHub Actions：

- Linux / Windows / macOS System Monitor。
- Linux / Windows / macOS Simple Program。
- System monitor themes screenshot。
- Localization。
- Release bundle validation。
- CodeQL；仅在触发条件适用时。
- Dependency Review。

只有状态为 `completed/success` 才能声明对应检查通过。未触发和成功不是同一状态。

## 保持可同步性的原则

- 一个阶段一个 Draft PR。
- 不在汉化提交中顺手重构无关业务逻辑。
- 不覆盖完整文件而不审查父分支差异。
- 不翻译协议、枚举、配置键和代码标识符。
- 内部开发日志保持英文。
- 新词条同时加入英文和中文词库。
- 不提交同步报告、一次性迁移脚本、诊断工件、构建目录或临时工作流。
- 依赖检查失败时读取完整 job/step 日志，不通过删除检查来变绿。
- 上游同步后按[发布检查清单](release-checklist.md)执行完整回归。

这些约束可以让汉化分支在上游持续演进时保持较小、可审查和可移植的差异。
