# MIT Relicensing, Exact OpenMinion 0.1.21 Pin, and English-Only Demo Video

- **Status**: accepted (supersedes Apache-2.0 choice in Spec #7 / Ticket #8)

我们决定将本仓库开源许可证由 `Apache-2.0` 切换为 `MIT` 并补齐 `PROJECTS.yml`、`STATUS.md` 与 `RELEASE.md`，在 `pyproject.toml` 中精确锁定 `openminion==0.1.21`，并将 `1080p` 演示视频全面改为全英文且嵌入真实 CLI 输出流。

## Considered Options

- **保留 `Apache-2.0` 许可证**：无法满足上游 `cortensor/community-projects` 仓库对合入 `apps/*` 项目强制采用共享 `MIT License` 及标准元数据文件的要求。
- **维持 `openminion>=0.1.21,<0.2.0` 宽松版本区间**：由于 `openminion` 处于高频 `0.1.x` Alpha 迭代期且本项目的隔离工厂、策略授权与环回测试深度依赖其内部模块签名，评委在截赛评审期安装新版极易触发非预期兼容断裂。
- **保留中英双语视频字幕**：在未预装中文字体的 Linux/macOS 评委环境中重新渲染 MP4 时会导致中文字符退化为方框乱码。

## Consequences

- 单一代码库同时兼容 DoraHacks `#2418` BUIDL 通道与 `cortensor/community-projects` 上游 PR 通道，评委在任意操作系统均可 100% 确定性复现测试与高清无乱码演示视频。
