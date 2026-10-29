> 2026-10-29：后续每页至少一张相关图片（含导览/负责人/reset分页），新闻原图优先，缺图用对应官方游戏/软件/公司标识；规则见Codex-report-news/News_Video/docs/SCENE_IMAGES.md。已发布不改。

> 2026-10-29 新制作：原发布时间48h硬门禁（临时6h/回顾24h继续更严）；森空岛停用默认BrowserSkill，未验证替代源时报缺口，其他官网/X继续；干员读gàn yuán（干四声，TTS-only）；导览明确公司/产品/游戏/人物及事件。详细接口见Codex-report-news/News_Video/docs/FRESHNESS_AND_SOURCES.md。已发布不修改。

> 2026-10-29 当前排序：主片00导览后，正文01为真实封面头条，其后为其他核实重大消息、剩余游戏、普通AI及对应负责人。无重大消息优先游戏头条；2＋2不是上限或每类只取1条。统一story_order与lead_event_id，详见docs/GAMES_FIRST.md（docs内文件见GAMES_FIRST.md）。已有任务按原计划，已发布不重做。

# 新闻项目交接入口（2026-10-28）

当前仍由 Codex 负责视频制作和已授权的自动投稿；DSH 暂不启动并行调度。现行短规则在 `Codex-report-news/News_Video/docs/CURRENT_RUNBOOK.md`，具体接手指令在 `handoff/DSH_PROMPT.md`。V_0 原始基线保留在 `Codex-report-news/News_Video/docs/V_0/`，已发布作品不重做、不重传。

## 本机结构

- `Codex-report-news/News_Video`：生产代码、配置、测试、项目 skill、详细文档。
- `release`：实际成品与投稿回执；只从这里上传。
- `Voice_Generate`：既有 Qwen3 声音流程；模型和参考素材未打进交接 ZIP。
- `.codex-upload-private`：本地私有认证和浏览器环境；从不打包、公开或输出。
- `handoff/DSH_NEWS_VIDEO_CONTEXT_YYYY_MM_DD.zip`：本地资料快照，需看 `handoff-package.json` 的哈希和时间；不是可直接运行的整机镜像。

## 执行顺序

1. 先查迁移锁、调度所有权、同一期次/voice/film 锁和 release/投稿状态；unknown先回查。
2. 按当前 runbook 采集、核验、选题、写稿、配音、字幕与固定混音；素材不够不生造。
3. 用锁定的渲染计划构建视频，检查帧、音频、字幕、导航与真实MP4时长；技术样片不投稿。
4. 合格后 release、已用新闻记账、自动投稿和平台回查；公开确认后清理本期残留。

详细代码入口和失败恢复见 `docs/WORKFLOW.md`；专项政策按 `CURRENT_RUNBOOK.md` 链接查。`STATE.md`、旧任务 prompt 和历史样片是状态记录，不代表新要求。完整交接包的 CRC 和逐文件 SHA-256 由 `build_handoff.py` 生成时验证；不据此声称已在 DSH 真机验收。

森空岛读取通过BrowserSkill，具体本地绑定、依赖与状态见docs/GAMES_FIRST.md及来源验收文档。不要复制浏览器profile或Cookie；缺环境记录缺口并继续已有官网来源。
