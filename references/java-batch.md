# Java batch mode

用户选择 Java 模式后，Agent 直接通过终端、COMSOL Java API、`comsolcompile` 和 `comsolbatch` 执行任务，不需要 MCP 服务。适合新建模型、修改导出的 Java、正式扫描、长计算和稳定复现。

## 随包入口

Windows 通用入口为 `scripts/java-mode.ps1`。

只检查安装，不启动 COMSOL：

```powershell
pwsh -File scripts/java-mode.ps1 -Stage Doctor -ComsolRoot "<COMSOL Multiphysics目录>"
```

只编译 Agent 生成或用户提供的 Java：

```powershell
pwsh -File scripts/java-mode.ps1 -Stage Compile -JavaSource "<模型.java>" -ComsolRoot "<COMSOL Multiphysics目录>"
```

用户明确授权本次求解后：

```powershell
pwsh -File scripts/java-mode.ps1 -Stage Run -JavaSource "<模型.java>" -ComsolRoot "<COMSOL Multiphysics目录>" -ConfirmSolve
```

入口为每次运行创建独立目录，保留源码副本与编译/批处理日志。进程退出为零后仍要读取模型代码约定的完成标记和目标产物；通用 runner 不可能替具体模型猜测成功条件。

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

## 关键检查

- 不用 `exit_code=0` 单独判定成功。
- 对 Windows 日志先检测编码，不假定 UTF-8。
- 把异常堆栈送入被实际保存的日志流。
- 参数扫描明确是 COMSOL 内部 parametric sweep 还是 runner 外层多案例；不要重复嵌套扫描。
- 修改几何或选择集后重新生成网格并检查各物理特征的 selection。
- 瞬态模型记录实际求解到的最后时间点，不用目标 `tlist` 代替完成证据。
- 图片导出后检查数据曲线/场是否存在、范围是否合理、选择集是否为空。

## Postprocess-only

若 MPH 已保存且解身份可信，导出失败时优先写独立后处理入口：只加载目标 MPH、核对哈希和解/数据集身份、补建结果节点并导出。不要重新运行 Study，除非已有解损坏或缺少目标变量。
