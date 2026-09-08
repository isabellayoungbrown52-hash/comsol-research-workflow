# Java batch mode

用户选择 Java 模式后，Agent 直接通过终端、COMSOL Java API、`comsolcompile` 和 `comsolbatch` 执行任务，不需要 MCP 服务。适合新建模型、修改导出的 Java、正式扫描、长计算和稳定复现。

## 随包入口

Windows 通用入口为 `scripts/java-mode.ps1`。

只检查安装，不启动 COMSOL：

```powershell
pwsh -File scripts/java-mode.ps1 -Stage Doctor -ComsolRoot "<COMSOL Multiphysics目录>"
```

电脑安装多个版本时，显式选择目标版本：

```powershell
$env:COMSOL_VERSION = '6.3'
pwsh -File scripts/java-mode.ps1 -Stage Doctor
```

也可以直接传入该版本的 `-ComsolRoot`。`COMSOL_ROOT` 优先于自动发现；编译和 batch 必须来自同一个安装根。

只编译 Agent 生成或用户提供的 Java：

```powershell
pwsh -File scripts/java-mode.ps1 -Stage Compile -JavaSource "<模型.java>" -ComsolRoot "<COMSOL Multiphysics目录>"
```

用户明确授权本次求解后：

```powershell
pwsh -File scripts/java-mode.ps1 -Stage Run -JavaSource "<模型.java>" -ComsolRoot "<COMSOL Multiphysics目录>" -ConfirmSolve
```

入口为每次运行创建独立目录，保留源码副本与编译/批处理日志。交互式 `Run` 会在隔离的 Java 副本中检查并注入 `ModelUtil.showProgress(true)`，调用 COMSOL 官方原生进度窗口；用户源文件不被修改。Java 源必须包含 `ModelUtil.initStandalone(true)`，否则 runner 会在启动前明确报错。CI 或没有桌面会话时才显式加 `-NoProgressWindow`，改由 batch 日志跟踪。官方窗口显示 100% 或进程退出为零仍不能替具体模型的完成标记和产物检查。

![COMSOL 6.3 官方进度窗口示例](../assets/comsol-official-progress-window.png)

该窗口由 COMSOL 自己呈现分层 solver、收敛性、参数和迭代状态。2026-09-09 已在 COMSOL 6.3 batch Java 探针中确认 `ModelUtil.showProgress(true)` 返回 `true`。不同操作系统或无图形会话是否能显示窗口，以目标版本返回值和运行环境为准。

## 入口设计

- 从项目配置文件读取 COMSOL 安装、编译器、批处理器和工作根；路径不一致时 fail closed。
- 把源码复制/物化到独立 `runtime`，再注入 run ID 和输出根；不在正式源码中硬编码临时目录。
- 源程序包含确定的建模、Study、保存和导出步骤；runner 负责目录、授权开关、进程调用、日志、哨兵和 QA。
- 需要写文件时优先使用 COMSOL 的保存/导出 API；普通 Java 文件写入是否允许取决于 COMSOL 安全策略，必须实测而非假定。

## Agent 的实际工作

1. 根据自然语言任务读取现有 MPH/Java 或生成一个最小 Java 入口；
2. 用 `Doctor` 和 `Compile` 尽早暴露安装、版本和 API 错误；
3. 用户授权后运行，读取真实日志和产物；
4. 遇到编译或求解错误时直接修改 Java 并迭代；
5. 得到目标 MPH、CSV 或图件后解释结果；
6. 只有正式交付才增加完整 manifest 和晋级 QA。

## 最终 MPH：在 COMSOL 内所见即所得

Java 模式的主交付不是一组散落的 PNG/CSV，而是打开后即可查看和继续后处理的 `.mph`。Java 入口应先创建或更新与结论对应的 dataset、plot group、具体绘图层、derived values 和 tables，再执行最终 `model.save(...)`。参数及单位、几何、选择集、材料、物理场、网格、Study、求解器配置和当前 solution 也应保存在模型树中。

推荐顺序：

```text
Build/Load → Configure → Mesh → Study/Solve → Build Results → Export → Final Save
```

- 外部绘图可以改善论文排版，但不能成为结果树的唯一载体。
- 若补做 postprocess-only，应在补建结果节点和导出后把模型另存或再次保存。
- 每个独立工况使用明确的 MPH 文件名和 model label，避免只有目录名能说明身份。
- 常规交付检查最终文件非空，并确认当前 solution、dataset 与主要结果节点存在；正式结果再只读重载最终 MPH 核对一次。
- 外部 CAD、插值表、材料数据或用户函数不能内嵌时，应随模型打包并使用稳定相对路径，同时列出依赖。

## 关键检查

- 不用 `exit_code=0` 单独判定成功。
- 对 Windows 日志先检测编码，不假定 UTF-8。
- 只用目标 COMSOL 版本自带的 `comsolcompile` 管理 Java API classpath；不要猜测单个 JAR 便足够。
- `comsolbatch -inputfile` 接收编译后的 `.class`，不是 `.java`。
- 把异常堆栈送入被实际保存的日志流。
- 参数扫描明确是 COMSOL 内部 parametric sweep 还是 runner 外层多案例；不要重复嵌套扫描。
- 修改几何或选择集后重新生成网格并检查各物理特征的 selection。
- 瞬态模型记录实际求解到的最后时间点，不用目标 `tlist` 代替完成证据。
- 图片导出后检查数据曲线/场是否存在、范围是否合理、选择集是否为空。

## Postprocess-only

若 MPH 已保存且解身份可信，导出失败时优先写独立后处理入口：只加载目标 MPH、核对解/数据集身份、补建结果节点并导出，然后再次保存包含新结果树的 MPH。不要重新运行 Study，除非已有解损坏或缺少目标变量；哈希核对只在正式身份管理需要时启用。

常见错误指纹和最低成本恢复路径见 [troubleshooting-efficiency.md](troubleshooting-efficiency.md)。跨版本编译和模型文件兼容规则见 [version-compatibility.md](version-compatibility.md)。
