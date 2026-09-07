# Release hygiene

公开仓库前执行一次最小发布审查：

1. 只发布通用 skill、必要参考和真正可复用脚本；不发布运行现场、失败日志、缓存、虚拟环境或大型 MPH。
2. 移除用户目录、许可证路径、端口、用户名、令牌、内部项目名和绝对路径。
3. 不分发 COMSOL 商业文件、官方 Application Library 模型、PDF 手册或未经许可的数据。
4. 若复制或修改第三方代码，保留其许可证与版权声明；仅借鉴方法时仍在 NOTICE 中给出来源和边界。
5. README 中说明 COMSOL 是商业软件，需要用户自行安装并持有相应许可；本项目不受 COMSOL AB 背书。
6. 不把“在某台机器测试通过”扩大为跨版本保证。记录测试版本、操作系统、通道和证据范围。
7. 对可执行脚本做静态检查和实际最小运行；对纯说明 skill 至少运行 skill validator，并人工检查引用路径。
8. 发布包内不得包含临时目录、`test/runs`、`__pycache__`、`.venv`、生成图件或未脱敏会话 transcript。

建议发布清单：

```text
comsol-research-workflow/
├── SKILL.md
├── agents/openai.yaml
├── references/
├── README.md
├── LICENSE
└── NOTICE.md
```

只有用户明确授权远程发布后，才创建仓库、提交、推送或创建 release。
