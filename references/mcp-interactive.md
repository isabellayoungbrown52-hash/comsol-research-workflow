# MCP interactive mode

用户选择 MCP 模式后，Agent 通过本地 MCP 工具把自然语言转换为真实 COMSOL 操作。适合交互建模、模型树检查、逐步修改、求解诊断和即时结果提取。

## 随包后端

可选后端位于 `mcp_backend/`，包含本地服务适配器、安装脚本、案例目录和保留许可证的上游 MCP 源码快照。它不包含 COMSOL、商业许可证或官方模型。

Windows 一次性安装。该入口会把运行时部署到 ASCII 路径，避免中文用户名或目录导致 JVM 库路径被截断：

```powershell
pwsh -File scripts/install-mcp.ps1
```

安装后先做不启动 COMSOL 的自检：

```powershell
<安装目录>/.venv/Scripts/python.exe -m server.main doctor
```

安装器会输出当前电脑的准确连接器 JSON。推荐为桌面 Agent 配置 stdio，其结构如下：

```json
{
  "command": "<安装目录>/.venv/Scripts/python.exe",
  "args": ["-m", "server.main", "serve", "--transport", "stdio"],
  "cwd": "<安装目录>"
}
```

若客户端只支持本地 HTTP，可运行：

```powershell
pwsh -File <安装目录>/scripts/start-mcp.ps1 -Transport streamable-http -Port 8765 -CopyHeader
```

地址为 `http://127.0.0.1:8765/mcp`。Bearer Token 只保存在本机安装目录的 `.mcp-token`；不要把它发到对话、issue 或仓库。

## 连接后的自然语言执行

1. 调用 `comsol_doctor`，确认 Python、COMSOL 安装和依赖；安装发现不等于许可证已验证。
2. 调用 `comsol_status`；需要时调用 `comsol_start` 或连接已有 server。
3. 根据用户目标创建或加载模型，读取真实模型名和节点身份。
4. 设置参数、几何、材料、物理场、网格和 Study；高层工具不足时使用 `comsol_model_code` 调用 Java API。
5. 获得用户对本次求解的授权后调用同步或异步 Study 工具。
6. 查询真实任务状态，完成后提取数值、生成结果节点、导出数据并保存 MPH。
7. 直接给出结果和物理解读，不把工具调用清单当成主要交付。

如果 Agent 看不到 `comsol_doctor` 或其他 COMSOL MCP 工具，说明客户端尚未加载连接器。此时完成安装和客户端配置；不要伪装已连接，也不要在用户未选择的情况下静默切到 Java 模式。

## 能力和边界

- `comsol_model_code` 是受信本机代码执行能力，不是沙盒；默认关闭，需要用户在本地设置 `COMSOL_ALLOW_CODE=1` 后重启后端。
- MCP 会话会保留模型状态，重试创建节点前先检查 tag，避免重复。
- 长求解使用 job 并查询状态，不因客户端调用超时而重复提交。
- 用户已有模型不得被全局清空；保存到新路径，除非用户明确要求覆盖。
- 不同 COMSOL 版本的接口类型和属性可能变化，遇到 API 错误时检查目标版本而不是反复猜测。

## 随包案例

`comsol_list_cases` 可查看中文案例目录。`heat_sink_3d` 是随包的原创三维传热示例，可用于首次连接后的端到端验证；运行它仍会占用 COMSOL 许可并执行求解，必须先得到用户授权。
