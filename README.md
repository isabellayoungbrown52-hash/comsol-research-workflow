# COMSOL Research Workflow

**Model. Solve. Understand.**

![COMSOL Research Workflow：从建模、求解到证据与验证](assets/social-preview.png)

让 AI Agent 通过自然语言真正操作 COMSOL：首次选择 Java 或 MCP 后端，然后建立或修改模型、排查失败、完成求解、提取结果并形成物理解读。它不是一份只供阅读的工作指南。

[English](README.en.md) · [Skill instructions](SKILL.md) · [Java batch](references/java-batch.md) · [MCP interactive](references/mcp-interactive.md) · [Physics review](references/physics-review.md)

## 它解决什么问题

很多 COMSOL Agent 工作流只覆盖两端：要么会发 API 命令但不理解科研问题，要么建立了严格检查框架却让日常建模寸步难行。本 skill 把重心放在实际推进：

- 从实验问题或研究假设整理出可计算的模型任务；
- 快速检查和修改已有 MPH、Java/Method 或 MCP 会话；
- 诊断几何、物理场、选择集、Study、求解器和结果表达式；
- 完成参数测试、正式扫描、数据导出和科学绘图；
- 默认交付一个带完整模型树、当前解和结果树、打开即可查看的 MPH；
- 根据结果风险决定验证深度，而不是对每个小任务执行完整审计。

默认工作循环是：

```text
Understand → Model → Run → Inspect → Iterate → Deliver
```

只有论文主结果、跨人复现、正式晋级或争议结果才升级到完整证据链。

## 首次选择两种模式

| 模式 | 如何真正调用 COMSOL | 最适合 |
|---|---|---|
| Java 模式 | Agent 生成或修改 Java API 源码，调用随包 runner、`comsolcompile` 和 `comsolbatch` | 正式扫描、长计算、稳定复现 |
| MCP 模式 | Agent 调用随包可选 MCP 后端提供的模型、参数、几何、物理场、网格、Study 和结果工具 | 探索、诊断、模型树和即时可视化 |

当用户第一次提出实际 COMSOL 操作时，Skill 会让用户选择一次模式。选定后立即调用对应后端推进任务，不反复询问，也不只返回教程。用户可随时用自然语言要求切换。

## 两种模式，同一个最终产物

Java 和 MCP 只是操作 COMSOL 的两条通道。只要任务创建、修改或求解模型，默认最终产物都是一个可直接打开的 `.mph`，而不是仅有代码、会话状态、CSV 或图片。

这个 MPH 会保留任务实际使用的参数与单位、几何、命名选择、材料、物理接口和边界、网格、Study/solver、当前 solution、datasets，以及可在 COMSOL 中直接查看的 plot groups、绘图层、derived values 和 tables。结果树完成后才执行最终保存；若后处理有更新，会再次保存。正式结果还会通过只读重载确认文件中的模型与结果确实可见。

若模型依赖不能内嵌的外部 CAD、插值数据或用户函数，Skill 会连同 MPH 打包这些文件、采用稳定相对路径并列明依赖，而不会把它误称为完全自包含文件。

## 30 秒开始

实际求解需要本机已安装且已获许可的 COMSOL Multiphysics。Java 模式需要 Agent 具有本地终端权限；MCP 模式首次使用需要安装并添加随包连接器。

1. 克隆仓库或下载 Release ZIP，把 `comsol-research-workflow/` 完整目录放入 Agent 的 skills 目录；不要只复制 `SKILL.md`。
2. 在 COMSOL 项目任务中调用：

```text
使用 $comsol-research-workflow 帮我通过自然语言操作 COMSOL。
```

3. Agent 将显示：

```text
请选择执行模式：
1. Java 模式——稳定批处理，不需要 MCP
2. MCP 模式——实时交互建模，需要本地连接器
```

Java 模式可先执行无求解自检：

```powershell
pwsh -File scripts/java-mode.ps1 -Stage Doctor -ComsolRoot "<COMSOL安装目录>"
```

MCP 模式首次安装：

```powershell
pwsh -File scripts/install-mcp.ps1
```

详细配置见 [MCP 模式](references/mcp-interactive.md)。

## 可运行的中文示例

MCP 后端随包提供 `heat_sink_3d` 原创三维传热示例，可用于验证从自然语言、建模、网格、稳态/瞬态求解到结果导出的完整链。案例数据和适用版本见 [验证记录](mcp_backend/examples/validation/README.md)。

![三维散热器温度场示例](mcp_backend/examples/validation/temperature_3d.png)

4. 只有需要正式复现或晋级时，才执行机器证据核查：

```bash
python scripts/validate_run_evidence.py /absolute/path/to/runs/<run_id>
```

校验器会检查 artifact 是否留在运行根内、文件是否存在、大小是否达标、SHA-256 是否一致，以及当前阶段所需证据是否齐全。它不会把结构校验冒充物理正确性。

## 三种强度

| 强度 | 适用任务 | 默认检查 |
|---|---|---|
| 工作模式 | 建模、调试、参数测试、绘图 | 当前解、变量、单位、主要趋势 |
| 正式复现 | 长计算、正式扫描、论文主结果 | 稳定入口、模型/工况身份、日志、原始导出 |
| 验收晋级 | 跨人复现、争议结果、正式归档 | 完整 evidence gate、manifest、哈希和科学 QA |

这使日常任务保持轻快，同时不牺牲正式科研结果需要的严谨性。

## 它不做什么

- 不捆绑 COMSOL、商业许可、官方模型或手册；
- 不包含 COMSOL 本体、商业许可证或官方 MPH；
- 不把任意代码执行包装成安全沙盒；
- 不承诺跨 COMSOL 版本复现相同数值；
- 不用流程合规替代领域物理判断。

## 目录

```text
comsol-research-workflow/
├── SKILL.md
├── agents/openai.yaml
├── mcp_backend/               # 可选本地 MCP 执行后端
├── scripts/java-mode.ps1      # Java 模式入口
├── scripts/validate_run_evidence.py
├── references/
├── assets/social-preview.png
├── assets/icon-400.png
├── assets/icon-800.png
├── README.md
├── README.en.md
├── CHANGELOG.md
├── CONTRIBUTING.md
├── SECURITY.md
├── LICENSE
└── NOTICE.md
```

## 设计来源

本项目融合了科研项目中积累的 Java 隔离批处理、建模判断和科学 QA 方法，并随包提供基于开源 COMSOL MCP 项目改编的可选本地后端。第三方代码、许可证和改编边界见 [NOTICE.md](NOTICE.md)。

## 状态

`v1.0.1`：Java/MCP 双后端、中文自然语言入口、所见即所得 MPH 交付和分级科研工作流。

COMSOL Multiphysics 是 COMSOL AB 的商业软件及商标。本项目独立开发，与 COMSOL AB 无隶属或背书关系。
