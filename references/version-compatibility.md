# COMSOL 版本兼容与选择

本 Skill 不把 COMSOL 6.3 硬编码为唯一版本。Java 模式使用目标安装自带的 `comsolcompile`/`comsolbatch`，MCP 模式通过 `COMSOL_VERSION` 选择 MPh 客户端版本；但模型、API 和物理功能仍受实际 COMSOL 版本及许可证约束。

## 先锁定一个版本

同一任务的编译器、batch、JVM/server、API 文档和最终 MPH 应属于同一 COMSOL 主版本。电脑有多个安装时：

```powershell
$env:COMSOL_VERSION = '6.3'
$env:COMSOL_ROOT = '<COMSOL63/Multiphysics>'
```

Java 模式也可直接传 `-ComsolVersion '6.3'` 或 `-ComsolRoot`。MCP 切换版本后必须重启后端，因为 JVM 初始化后不能在同一进程中更换 COMSOL 安装。

## MPH 文件方向

- 较新 COMSOL 通常可以打开较旧版本保存的 MPH，但打开后要阅读转换、弃用和兼容警告。
- 用较新版本保存旧模型会升级文件格式；COMSOL 6.3 官方文档明确说明，升级保存后的文件只能由 6.3 或更高版本打开。因此第一次打开旧模型时先另存副本，不覆盖唯一原件。
- 较旧 COMSOL 不能打开由较新版本保存的 MPH。需要面向旧版本交付时，最可靠的方法是在目标旧版本中重建或验证模型；Java/MATLAB 文本导出有时可迁移，但新版本独有 feature/property 在旧版本仍会失败。

## Java/API 与物理节点

Java 语法本身不等于 API 兼容。不同版本可能新增、重命名、弃用或改变 feature type、property、默认值和求解器节点。处理方式：

1. 用目标版本的 `comsolcompile` 尽早编译；
2. 以目标版本官方 API 和 Release Notes 为准；
3. 遇到未知 feature/property 时检查版本，不反复猜字符串；
4. 对自动转换或弃用警告，核对方程、选择集和默认值是否仍符合原意；
5. 重新求解后比较关键标量、守恒量和代表性场，而不是假设跨版本数值逐位相同。

## 可复用程度

当前公开包的 Java runner 已在 COMSOL 6.3 做过 Doctor/Compile 级验证；`gui_quickstart_3d` 已通过真实 MCP stdio 在 COMSOL 6.3 完成建模、求解、结果树、图片和带解 MPH，较长的 `heat_sink_3d` 验证记录来自 COMSOL 6.2。它说明双通道设计能够覆盖多个 6.x 安装，但不等于每个物理模块、每个 5.x/6.x 小版本都已验证。

普通模型在相邻版本间通常可迁移，风险主要集中于新功能、已弃用节点、CAD/LiveLink 接口、求解器默认值、表达式名称和附加模块许可。正式复现最好使用原求解版本；必须换版本时保留原 MPH，并把版本变化当作一次受控迁移。

## 官方依据

- [COMSOL 6.3：Saving COMSOL Files](https://doc.comsol.com/6.3/doc/com.comsol.help.comsol/comsol_ref_environment.18.16.html)
- [COMSOL 6.3：Backward Compatibility with Version 6.2 and Earlier](https://doc.comsol.com/6.3/doc/com.comsol.help.comsol/comsol_release_text.06.083.html)
- [COMSOL 6.3：Model File for Java](https://doc.comsol.com/6.3/doc/com.comsol.help.comsol/comsol_api_intro.46.08.html)
- [COMSOL 6.3 Release Notes](https://doc.comsol.com/6.3/doc/com.comsol.help.comsol/COMSOL_ReleaseNotes.pdf)
