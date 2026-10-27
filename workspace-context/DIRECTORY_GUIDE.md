# 目录说明（2026-10-27）

新闻视频代码只有一份，实际运行和 Git 保存统一在 `Codex-report-news/News_Video/`。

| 目录 | 用途 |
| --- | --- |
| `Codex-report-news/` | GitHub 仓库工作目录 |
| `Codex-report-news/News_Video/` | 唯一运行项目：代码、数据、素材、项目技能、依赖和工作文件 |
| `Voice_Generate/` | 独立语音工具仓库；通过配置引用，不在视频仓库重复复制 |
| `admin_retrain/`、`admin_voice_study/` | 原语音模型、训练和实验项目，保持原位 |
| `release/` | 原成品包位置不变，已发布文件不改写 |
| `.codex-upload-private/` | 本机投稿认证与账本，保持原位且不进入 Git |
| `codex-upload-video/` | 独立投稿器源码项目 |
| `handoff/` | 本地交接资料；历史 ZIP 是归档，不是第二个运行目录 |
| `.news-layout-migration-20261027/` | 迁移文件清单、哈希和核验记录，不保留重复源码 |

运行命令先切换到 `D:/Basement/Codex_Video/Codex-report-news/News_Video`。原根目录 `News_Video` 已移除，不保留旧路径兼容链接。小时巡检已改用新目录。成品路径由 config.json 的 release.directory 决定；投稿私有目录和原语音项目通过配置引用。

本机数据、依赖、技能、内部规则和交接资料保留于本地，通过 Git 忽略规则与公开源码分开。后续直接在仓库内编辑、测试和提交，不再执行源码复制备份。
