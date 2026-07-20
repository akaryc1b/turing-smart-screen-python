# 简体中文版本最终维护审查

本指南用于简体中文本地化堆叠 PR 的最终维护阶段。该阶段不新增硬件能力，重点是验证分支祖先、仓库卫生、工作流策略和文档是否与实际实现一致。

## 当前堆叠链路

```text
main
└── agent/zh-cn-integration-review
    └── agent/zh-cn-upstream-compat
        └── agent/zh-cn-release-candidate
            └── agent/zh-cn-frozen-smoke
                └── agent/zh-cn-coverage-audit
                    └── agent/zh-cn-final-maintenance
```

每个阶段的 PR base 必须指向前一阶段分支。后续分支相对 base 应为 ahead 且 behind 为 0，merge base 应等于前一阶段最终 Head。不要通过复制累计文件来伪造正确祖先关系。

## 仓库卫生

最终提交不得包含：

- `build/`、`dist/` 或 PyInstaller 临时目录；
- `*.exe`、`*.zip`、`*.tar.gz`、安装程序或冻结程序；
- `*.log`、缓存、截图或测试生成物；
- 下载的 `ChineseSimplified.isl`；
- `release-manifest.json`；
- `localization-coverage.json`、`localization-coverage.md`；
- `upstream-sync-report.*`、`upstream-sync-metadata.json`；
- 临时诊断、源码传输、队列清理或一次性 apply workflow。

生成报告可以作为 GitHub Actions artifact 上传，但不得进入 Git diff。

## 工作流策略

维护审查必须确认：

- 不需要写权限的 workflow 只使用 `contents: read`；
- job 设置合理的 timeout，重复 PR run 使用 concurrency；
- 不使用 `continue-on-error`、warn-only、恒假条件或路径忽略掩盖失败；
- Dependency Review 保持 `actions/dependency-review-action@v5`；
- Release Candidate workflow 仍然只由 `workflow_dispatch` 触发；
- 发布验证不创建或修改 GitHub Release；
- Frozen smoke 不上传 executable、`build/`、`dist/` 或日志；
- Localization coverage 只上传 JSON 与 Markdown 报告；
- 失败日志和临时诊断 artifact 不进入最终工作流。

GitHub Fork 上的 Dependency Review 平台限制必须如实记录，不能通过弱化策略把失败伪装成成功。

## 稳定内部值

维护改动不得翻译或改写硬件 revision、协议值、环境变量和配置枚举，例如：

```text
AUTO
STATIC
SIMU
TUR_USB
metric
imperial
standard
```

界面显示文本可以本地化，但保存到配置、协议或设备识别逻辑中的稳定值必须保持不变。

## 最终验证

至少运行：

```bash
python -m py_compile tests/test_repository_hygiene.py
python -m unittest tests.test_repository_hygiene -v
python -m unittest discover -s tests -t . -v
```

GitHub Actions 需要等待 flake8、Localization、Localization coverage、三平台 System Monitor、三平台 Simple Program、Frozen smoke、主题截图和发布包验证达到最终状态。

只有状态为 `completed/success` 的 run 才能写成通过。Dependency Review 的 Fork 限制应单独列出，不计作其他检查成功。

## PR 状态边界

最终维护 PR 必须保持：

- Open；
- Draft；
- 未合并；
- 未启用 auto-merge；
- 未标记 Ready for review。

阶段闭环后再决定是否创建以 `main` 为 base 的最终累计 Draft PR。