# 简体中文文档索引

本目录是 `turing-smart-screen-python` 汉化 Fork 的简体中文维护文档。通用项目介绍见根目录 [`README.zh-CN.md`](../../README.zh-CN.md)，上游英文文档和 Wiki 仍是硬件兼容信息的重要来源。

## 用户文档

- [安装说明](installation.md)：Windows 安装器、portable、Debug、Linux 包和源码安装。
- [配置向导与配置文件](configuration.md)：界面选项、内部配置值和常见配置组合。
- [主题制作](themes.md)：主题 schema、中文示例主题和截图验证。
- [中文字体](fonts.md)：跨平台 CJK 字体发现、别名和安全回退。
- [常见错误排查](troubleshooting.md)：启动、硬件、字体、主题和打包问题。

## 维护者文档

- [本地化架构说明](LOCALIZATION.md)：语言选择、词库契约、冻结资源和已完成范围。
- [本地化覆盖率审计](localization-coverage.md)：翻译键、占位符、硬编码文本、允许列表和 CI 报告。
- [简体中文贡献指南](contributing.md)：词库、代码、主题、打包和 PR 规则。
- [Dependency Review 根因与维护边界](dependency-review.md)：Fork 平台限制、运行证据和不可弱化的安全 CI 合同。
- [简体中文术语表](glossary.md)：推荐译法、稳定缩写和内部值。
- [同步上游](upstream-sync.md)：堆叠分支、冲突处理和同步报告工具。
- [发布检查清单](release-checklist.md)：源码、CI、bundle、安装器和发布后验证。

## 文档维护原则

- 中文文档保持 UTF-8，并使用实际命令、路径和配置值。
- 不翻译协议值、环境变量、配置键、文件名和行业缩写。
- 新增或删除文档时同步更新本索引和根目录 `README.zh-CN.md`。
- 不把未经过测试或 GitHub Actions 验证的能力写成已支持。
- 保留 GPL-3.0、上游作者、非官方声明和第三方归属。
