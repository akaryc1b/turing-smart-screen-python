# Dependency Review 根因与维护边界

本文记录汉化堆叠 PR 中 `Dependency Review` 的真实失败证据、已排除原因和必须由仓库管理员决定的后续操作。工作流必须继续保留并执行，不得通过删除工作流、`continue-on-error`、`warn-only: true`、条件跳过或放宽漏洞策略来制造绿色结果。

## 已验证的工作流配置

`.github/workflows/dependency-review.yml` 使用：

- `pull_request` 事件。
- `permissions: contents: read`。
- `actions/checkout@v6`。
- `actions/dependency-review-action@v5`。
- 并发取消和作业超时，避免旧 PR Head 的检查继续占用资源。

2026-07-19 的失败运行下载了 `actions/dependency-review-action@v5` 对应提交 `a1d282b36b6f3519aa1f3fc636f609c47dddb294`。Runner 版本满足 v5 的 Node.js 24 运行要求，因此失败不是 action 下载、Runner 版本或事件类型问题。

## GitHub Actions 证据

### PR #8

- PR Head：`00b8ba098eb6e5eebd345392cddd9b35859acc0f`
- Workflow run：`29678127959`
- Job：`88169245045`
- 失败步骤：`Dependency Review`
- Checkout：成功
- Action：`actions/dependency-review-action@v5`
- `GITHUB_TOKEN`：`Contents: read`、`Metadata: read`
- 错误：`Dependency review is not supported on this repository`
- Workflow artifacts：空列表，没有可下载 artifact

### PR #7

- PR Head：`dbd11dbb74d7fb12e9ad95b8f131c736a6dc2df4`
- Workflow run：`29676836107`
- Job：`88165649248`
- Checkout：成功
- 失败步骤：`Dependency Review`
- 失败模式与 PR #8 一致

连续多个不同 Head 和不同堆叠 Base 都在 action 调用 Dependency Review API 时失败，说明问题发生在依赖比较之前。

## 根因判断

当前仓库 `akaryc1b/turing-smart-screen-python` 是 `mathoudebine/turing-smart-screen-python` 的 GitHub Fork。GitHub 的 Dependency Review REST API 文档明确列出：`Get a diff of the dependencies between commits` 在 `used against a fork` 时返回 `403`。

因此，action 输出的“请启用 Dependency graph”是通用错误提示；对当前 Fork 而言，单独启用 Dependency Graph 不能消除 Dependency Review API 对 Fork 的限制。这个限制不能通过工作流代码修复。

已排除：

- **Token 权限不足**：工作流使用官方要求的 `contents: read`，失败发生在 API 能力检查。
- **私有仓库功能限制**：仓库是公开仓库。
- **action 配置错误**：工作流与官方基本配置一致，并使用 v5。
- **许可证或漏洞策略命中**：API 未返回依赖 diff，许可证和漏洞规则尚未执行。
- **事件类型错误**：工作流由受支持的 `pull_request` 事件触发。
- **堆叠 PR Base 异常**：PR #7 和 PR #8 使用不同 Base，失败结果相同。
- **Dependency Graph 中缺少清单**：错误发生在 API 支持检查，而不是依赖清单解析阶段。

官方参考：

- Dependency Review API：<https://docs.github.com/en/rest/dependency-graph/dependency-review>
- Dependency Review Action：<https://github.com/actions/dependency-review-action>
- 解除 Fork 关系：<https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/working-with-forks/detaching-a-fork>

## 人工操作边界

当前已连接的 GitHub 工具没有提供 Dependency Graph 开关或解除 Fork 网络的写操作，不能声称已修改仓库设置。

要让同一仓库中的 Dependency Review API 具备成功条件，需要把仓库转换为独立仓库。GitHub 网页中的入口是：

`Settings → General → Danger Zone → Leave fork network`

这是永久且高风险的操作。GitHub 明确警告，离开 Fork 网络后不会保留现有 issues、pull requests、wikis、stars、watchers、comments、child forks 等元数据，并且不能重新连接到原 Fork 网络。当前存在 PR #1–#9 堆叠链时不得执行该操作。

只有在完成 PR 和分支元数据备份、确认仓库大小及 child forks 满足 GitHub 条件、并由仓库所有者接受不可逆影响后，才能考虑解除 Fork 关系。解除后还应进入：

`Settings → Security → Advanced Security`

确认 `Dependency Graph` 已启用，然后重新运行 Dependency Review。只有 GitHub 返回 `completed/success` 才能记录为通过。

## 当前维护决策

- 保留 `actions/dependency-review-action@v5`。
- 保留失败状态，不伪造成功。
- 通过测试阻止未来加入弱化配置。
- 在累计集成 PR 中继续观察该工作流，但在仓库仍是 Fork 时预期同一平台限制仍存在。
- 不把 Dependency Review 的失败归因于汉化代码、依赖许可证或漏洞，除非 API 将来实际返回依赖差异结果。
