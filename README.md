# COMSOL Research Workflow

**用自然语言建模、求解、查看结果，并交付完整可视的 COMSOL 模型。**

![COMSOL Research Workflow：自然语言驱动的双模式工作流](assets/social-preview.png)

这个 skill 让 AI Agent 通过两种执行模式真正操作本机 COMSOL。用户描述研究问题或修改目标，Agent 负责建立或读取模型、配置参数和物理场、运行 Study、查看结果并保存可继续编辑的 `.mph`。

[English](README.en.md) · [Skill instructions](SKILL.md) · [Java 模式](references/java-batch.md) · [MCP 模式](references/mcp-interactive.md)

## 可以完成什么

- 从自然语言研究问题建立二维、三维、稳态、瞬态或参数化模型；
- 读取并修改已有 MPH、Java/Method 和 MCP 会话；
- 配置参数、几何、选择集、材料、物理场、网格、Study 与 solver；
- 运行单个工况、参数测试和正式扫描；
- 在 COMSOL Results 树中建立场图、曲线、切片、派生值和表格；
- 导出数据与图像，并结合方程、单位和边界条件解释结果；
- 将参数、材料、物理、网格、解和结果树保存到一个可直接打开的 MPH；
- 根据报错位置恢复编译、连接、求解、保存或后处理任务。

核心工作循环：

```text
Understand → Model → Run → Inspect → Iterate → Deliver
```

## 首次选择执行模式

| 模式 | 工作方式 | 适合任务 |
|---|---|---|
| Java 模式 | Agent 生成或修改 Java API 源码，通过 `comsolcompile` 和 `comsolbatch` 运行，并启用 COMSOL 官方进度窗口 | 长计算、正式扫描、稳定复现 |
| MCP 模式 | Agent 操作 COMSOL live model，并可连接同一 server 的 COMSOL Desktop 查看模型树和三维结果 | 交互建模、快速修改、诊断和可视化 |

首次实际操作时选择一次即可，后续可以直接用自然语言继续，也可以随时要求切换模式。

## Java 模式：官方求解进度

Java Run 默认调用 COMSOL 官方 `ModelUtil.showProgress(true)`。窗口直接显示分层 solver、进度、收敛性、参数和迭代状态，适合观察长时间计算。

![COMSOL 6.3 官方进度窗口](assets/comsol-official-progress-window.png)

无桌面的服务器或 CI 环境可使用 `-NoProgressWindow`，运行日志仍会完整保存。

## MCP 模式：模型树与原生可视化

MCP 将自然语言操作发送到 COMSOL live model。用户可在连接同一 server 的 COMSOL Desktop 中查看和继续编辑几何、材料、物理场、网格、Study、solution 与 Results 树，也可以让 Agent 直接导出图像。

随包原创 `gui_quickstart_3d` 已在 COMSOL 6.3 完成端到端运行，覆盖三维建模、稳态求解、结果树、图像导出和带解 MPH 保存。

![MCP 模式三维温度场](mcp_backend/examples/validation/gui_quickstart_3d_comsol63.png)

## 两种模式，共享同一个交付标准

只要任务创建、修改或求解模型，默认交付一个可直接用 COMSOL 打开的 `.mph`。模型中保留：

- 参数、单位、变量和函数；
- 几何、命名选择和组件耦合；
- 材料和实际采用的物性；
- 物理接口、域条件、边界条件和源项；
- 网格、Study、solver 和当前 solution；
- datasets、plot groups、绘图层、derived values 和 tables。

若模型需要外部 CAD、插值数据或用户函数，这些依赖会与 MPH 一起整理，并采用稳定的相对路径。

## 30 秒开始

准备条件：Windows、PowerShell、已安装并获许可的 COMSOL Multiphysics，以及支持本地 skill 的 AI Agent。

1. 克隆仓库或下载 [最新 Release](https://github.com/isabellayoungbrown52-hash/comsol-research-workflow/releases/latest)。
2. 将完整的 `comsol-research-workflow/` 文件夹放入 Agent 的 skills 目录。
3. 在任务中输入：

```text
使用 $comsol-research-workflow 帮我通过自然语言操作 COMSOL。
```

Agent 会显示：

```text
请选择执行模式：
1. Java 模式——稳定批处理和官方进度窗口
2. MCP 模式——实时交互建模和 COMSOL Desktop 可视化
```

Java 模式安装检查：

```powershell
pwsh -File scripts/java-mode.ps1 -Stage Doctor -ComsolRoot "<COMSOL安装目录>"
```

MCP 模式首次安装：

```powershell
pwsh -File scripts/install-mcp.ps1
```

## 自然语言示例

```text
用 MCP 模式建立一个三维稳态传热模型，材料用铝，底部施加 10 W 热源，
其余外表面对空气自然对流。完成网格检查后求解，生成温度场和热流图，
把参数、材料、物理场、Study、解和 Results 树保存在最终 MPH 中。
```

```text
用 Java 模式读取这个模型，把入口速度扫描为 0.01、0.02 和 0.03 m/s。
运行时显示 COMSOL 官方进度窗口，完成后分别保存三个带解 MPH，
并汇总压降和最大速度。
```

## COMSOL 版本

Java runner 和 MCP 快速案例均已在 COMSOL 6.3 验证。其他版本可通过 `COMSOL_VERSION` 或 `COMSOL_ROOT` 选择；同一任务应使用同一版本的编译器、batch、JVM/server 和 API。

旧模型首次在新版本中打开时建议另存副本。具体规则见[版本兼容指南](references/version-compatibility.md)。

## 更多文档

- [Java 批处理与官方进度窗口](references/java-batch.md)
- [MCP 安装、连接与 Desktop 可视化](references/mcp-interactive.md)
- [COMSOL 版本兼容](references/version-compatibility.md)
- [常见报错与高效恢复](references/troubleshooting-efficiency.md)
- [物理建模判断](references/physics-review.md)
- [验证记录](mcp_backend/examples/validation/README.md)

## 当前版本

`v1.1.0`：Java 官方进度窗口、COMSOL 6.3 MCP 快速可视化、完整 MPH 交付、故障恢复和多版本支持。

COMSOL Multiphysics 是 COMSOL AB 的商业软件及商标。本项目独立开发，与 COMSOL AB 无隶属关系。
