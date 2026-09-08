---
name: comsol-research-workflow
description: "Operate COMSOL from natural language through Java/Method batch or an MCP session: build, solve, debug, postprocess, interpret, and deliver a complete directly viewable MPH with model and result trees. Use for practical COMSOL modeling, sweeps, result extraction, visualization, and physics-aware interpretation. Choose the lightest workflow that advances the task; reserve full evidence gates for formal reproduction, promotion, or disputed results."
---

# COMSOL Research Workflow

把科研问题推进到可用模型和可解释结果。默认目标是完成工作，而不是先建立审计体系。

## 首次执行：选择后端

当用户第一次要求实际创建、修改、求解或操作 COMSOL，且尚未指定后端时，先显示一次二选一；若客户端支持选择控件就使用控件，否则用一条简短问题：

1. **Java 模式**：Agent 通过本机 COMSOL Java API、`comsolcompile` 和 `comsolbatch` 工作。适合长计算、正式扫描和稳定复现，不需要 MCP 服务。
2. **MCP 模式**：Agent 通过已配置的本地 COMSOL MCP 工具实时建模、查看模型树、求解和导出。适合交互建模与快速诊断。

用户已经点名 Java 或 MCP 时直接采用，不再询问。选择在当前任务中持续有效，除非用户要求切换或当前后端不可用。概念解释、只读文档审查和纯数据绘图不弹出选择。

选定后必须立即使用真实工具推进任务，不要只返回操作指南：

- Java 模式先运行 `scripts/java-mode.ps1 -Stage Doctor`；需要时读取 [references/java-batch.md](references/java-batch.md)。进入 `Run` 时必须启用 COMSOL 官方 `ModelUtil.showProgress(true)` 原生进度窗口；runner 只修改隔离运行副本，不改用户源文件。只有 CI 或明确无桌面的环境才使用 `-NoProgressWindow` 并依靠 batch 日志。
- MCP 模式先调用 `comsol_doctor` 或等价连接检查；工具不存在时读取 [references/mcp-interactive.md](references/mcp-interactive.md)，完成一次性安装或配置后再继续。
- 两种模式都不可用时，准确说明缺少的软件、许可或连接，不编造已经操作 COMSOL。

若电脑安装了多个 COMSOL 版本、模型来自另一版本，或出现未知 feature/property、MPH 无法打开、客户端与服务器不匹配等现象，先读取 [references/version-compatibility.md](references/version-compatibility.md)，锁定本次使用的版本再修改或求解。

## 所见即所得 MPH 交付合同

只要任务实际创建、修改或求解 COMSOL 模型，两种模式默认都要交付一个可直接用 COMSOL 打开的最终 `.mph`。外部 CSV、图片、日志和 Java 源码是补充产物，不能代替最终模型。只有用户明确要求纯诊断、临时数值检查、只导出数据或不保存文件时，才可省略 MPH。

最终 MPH 应在模型树中保留本任务实际使用的完整对象：

- 带单位和说明的参数、变量与函数；
- 几何、命名选择和组件耦合；
- 材料及其实际采用的物性；
- 物理接口、域/边界条件、源项与多物理场耦合；
- 网格、Study、求解器配置和当前有效 solution；
- 与交付结论对应的 dataset、plot group、曲线/表面/切片/箭头等图层、derived values 和 tables；
- 能区分模型与工况的文件名、模型 label、节点 label 和必要说明。

结果节点必须在 COMSOL 模型内部建立，不能只在外部脚本中画图。完成结果树后再做最终保存；后处理节点发生变化时再次保存，避免交付的 MPH 落后于导出的图或数据。

- **Java 模式**：Java 源码负责创建结果节点，并把 `model.save(...)` 或等价保存放在最终阶段；每个独立工况输出到明确路径。
- **MCP 模式**：在当前 live model 内完成结果树，随后调用保存工具生成独立 MPH；交付时报告实际模型名和绝对路径，不能只保留服务器会话状态。

常规任务至少确认 MPH 存在且非空，并在同一会话中检查关键模型节点、当前 solution/dataset 和结果树。正式复现或论文主结果应只读重载已保存 MPH，再核对关键节点、工况和解身份。若模型依赖外部 CAD、插值表、材料库或用户函数，应一并打包可分发文件并改用稳定相对路径；未能内嵌的依赖必须明确列出，不能把它描述成完全自包含模型。

## 默认工作方式

使用最轻量、足以解决当前问题的流程：

1. 明确本次要回答的问题、目标量和现有模型状态；
2. 只读取当前步骤需要的模型、脚本、参数或结果；
3. 选择 Java/Method、MCP、已有 MPH 后处理或混合通道；
4. 建模、修改、运行或提取结果；
5. 查看真实输出，修复阻碍结论的问题并继续迭代；
6. 交付可直接查看的最终 MPH，并按任务需要附数据、图件或判断，简要说明适用边界。

普通参数修改、绘图、结果提取和故障排查不需要先制作 manifest、计算哈希或走完整晋级流程。不要因为低风险的格式问题、命名差异或缺少非必要元数据而停止推进。

## 失败后高效恢复

发生报错、超时、假成功、磁盘暴涨或图件无法复现时，读取 [references/troubleshooting-efficiency.md](references/troubleshooting-efficiency.md)。先判断失败发生在连接、编译、建模、求解、保存还是后处理层，只修复最早失败的一层；已经保存且身份可信的解优先继续后处理，不重复提交长计算。

内部故障记录用于改善操作，不直接进入论文或用户交付。把具体项目路径、历史人名和一次性症状转化为可复用判断，避免把单次事故升级成每个任务都必须执行的繁重门禁。

## 三种工作强度

### 1. 工作模式（默认）

适合探索建模、局部修改、故障排查、参数测试、绘图和结果解释。

- 先做能最快回答科学问题的操作；
- 保留必要的模型或脚本副本，避免覆盖唯一可用结果；
- 验证当前解存在、目标变量有效、单位合理、主要趋势不违背边界条件；
- 用简短记录说明改了什么、得到什么，不额外制造交付负担。

### 2. 正式复现模式

适合长计算、正式参数扫描、论文主结果和需要交给他人重放的任务。

- 使用隔离运行目录和稳定入口；
- 固定关键参数、选择集、Study、时间窗和扫描点；
- 保存包含当前解和结果树、可继续后处理的 MPH，以及运行日志和原始导出；
- 让模型、案例和结果身份能够对应。

正式批处理细节见 [references/java-batch.md](references/java-batch.md)。只有需要机器化交接时才使用 [references/run-manifest.md](references/run-manifest.md)。

### 3. 验收与晋级模式

只在以下情况启用完整证据链：准备晋级正式结果、跨人复现、结果存在争议、模型身份可能混淆，或用户明确要求审计。

此时再使用：

`ReadOnly → StaticOnly → Compile → Smoke → Solve → Save → Export → Canonicalize → QA → Promote`

详细门槛见 [references/evidence-gates.md](references/evidence-gates.md)，机器校验可运行 `scripts/validate_run_evidence.py`。它是正式交付工具，不是日常建模的前置条件。

## 选择合适的执行通道

- **已有可信解**：优先直接后处理，不为补 CSV 或图件重跑求解。
- **MCP 交互会话**：适合快速查看模型树、修改节点、诊断表达式和即时可视化。发行包包含可选的 `mcp_backend/`；需要时读 [references/mcp-interactive.md](references/mcp-interactive.md)。
- **Java/Method 批处理**：适合正式扫描、长计算、稳定重放和隔离运行。发行包包含 `scripts/java-mode.ps1` 通用入口；需要时读 [references/java-batch.md](references/java-batch.md)。
- **混合方式**：可用 MCP 快速探索，再把成熟设置固化到正式入口；不要求探索阶段立即完全可重放。

通道只是工作方式，不预设哪一种更科学。根据速度、模型状态、许可、任务风险和交付要求选择。

## 建模与求解判断

求解前至少知道：

- 目标量是什么，模型中的表达式如何对应它；
- 本次真正改变的参数、边界、物理场或网格是什么；
- 哪个 Study、solution 和 dataset 应产生目标结果；
- 哪些过程是显式求解，哪些是简化、映射或代理量。

只有在用户明确授权本次求解后才进入 Solve。Compile、静态检查和已有结果后处理不能写成“求解完成”。不静默覆盖正式模型、正式数据或已确认图件。

涉及物理接口、质量/电荷守恒、通量定义或模型简化时，按需读取 [references/physics-review.md](references/physics-review.md)。不要因为理论上能增加物理场，就自动扩大模型；复杂度必须服务于当前科学问题。

## 按风险验证，而不是一刀切

- **探索结果**：检查解是否存在、数值是否有限、单位和方向是否基本合理。
- **常规科研结果**：再核对关键参数、边界条件、数据集身份、数量级和主要守恒关系。
- **正式论文结果**：增加网格/时间步或关键假设敏感性、原始数据与图件对应、结论边界。
- **晋级或争议结果**：使用完整 evidence gate、manifest、哈希和独立复现证据。

验证发现真实错误时立即修正或阻断错误结论；只发现低价值形式差异时，记录即可继续。

## 推进优先级

1. 先恢复或建立能工作的模型入口；
2. 再得到与问题直接相关的解和原始结果；
3. 处理影响物理意义、数值稳定性或结果身份的问题；
4. 形成可读图表和科研解释；
5. 只有交付等级需要时，补齐复现和晋级证据。

失败后优先利用已保存 MPH、日志和现有解继续定位；不要为了补一个导出反复提交长计算。对普通小问题自行判断和修复，只有需要新增求解授权、改变关键物理假设、覆盖正式结果或扩大任务范围时才停下来询问。

## 交付

先给可直接使用的产物或明确结论，再简要报告：实际完成了什么、使用了哪个模型/工况、结果是否改变、仍有什么会影响科学判断。

论文图注和结果说明只写客观方法、结果与适用边界，不写内部审计、代理分工、故障历史或工作流免责语言。

准备公开发布工作流本身时，读取 [references/release-hygiene.md](references/release-hygiene.md)。
