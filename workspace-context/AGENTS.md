> 2026-10-27 最新主片安排：取消午间新闻，只制作北京时间06:00开始的morning早报和18:00开始的night晚报；不提前15分钟，质检通过后沿用默认设置自动投稿。不再制作、补做或投稿新的noon午报。tibo reset临时新闻及每小时30分巡检保留。历史午报成品与记录保留。

> 2026-10-27 最新采集范围：小时巡检只读取 tibo @thsottiaux 并处理 reset、回查投稿；不采集社会 RSS，不读取公司或其他负责人 X。社会 RSS、公司官方 X 和其他负责人仅在视频制作前刷新。每期执行 collect --kind all（社会 RSS + AI 官方来源 + 全部启用 X），不能只复用旧社会缓存。新模型线索在制作阶段采集后按 MODEL_ALERTS 核验，已有授权与去重规则保留。

# 新闻视频项目入口

本项目当前由 Codex 制作并协助发布，DSH 仅是未来可接手的执行环境。先读 `PROJECT_PROMPT.md`，再读 `Codex-report-news/News_Video/docs/WORKFLOW.md` 与 `Codex-report-news/News_Video/docs/STATE.md`。这些文档包含用户今天确认的最新规则，优先于旧样片、旧提示词和历史记录。

制作遵循 `Codex-report-news/News_Video/skills/news-video-production/SKILL.md`；文稿遵循项目内 `help-me-speech`。不要把内部计划、核验措辞、提示词或思考过程写进公开画面和口播。

制作完成先准备 `release/YYYY_MM_DD_{morning|night}/`，上传只使用其中带日期和时段的 MP4。发布确认后才清理工作残留。不要覆盖已发布成品，不重复上传 2026-10-26 晚间版。

`Voice_Generate`、`admin_retrain`、`admin_voice_study` 为既有语音项目：只调用必要入口，不擅自修改模型、训练或清理这些目录。账号、Cookie、浏览器 profile、API key、模型权重和微软字体不进入交接包或 Git。

每小时只采集tibo；社会RSS、公司官方X及其他负责人在视频制作前读取；先读Codex-report-news/News_Video/docs/PRODUCTION_RULES.md。新模型正式发布按MODEL_ALERTS.md核实后自动临时投稿，主片仍包含重要回顾。tibo 明确宣布额度 reset 时按 Codex-report-news/News_Video/docs/RESET_ALERTS.md 优先制作“临时新闻”，不占早晚两期。临时稿另用 release/YYYY_MM_DD_temporary_HHmmss_alertid/，只呈现重置推文信息。同一重置去重，先核验语义，先 release 再上传；未取得发布回执不记成功。

自动投稿使用 Codex-report-news/News_Video/skills/codex-upload/SKILL.md 与 docs/CODEX_UPLOAD.md；当前用户已授权新一期按默认设置自动最终提交。Chrome 优先，Edge 后续兼容。提交和审核发布分开，未知回执先回查，不能重投；今天已发布版有哈希防重记录。


## Multiplane视觉扩展

新增可选multiplane/editorial（A清爽编辑版）与multiplane/graphic（B强图形版），实际验收通过，用户选定后新期默认B（multiplane/graphic）；hyperframes/legacy保留。每期render-plan锁定后端/版本/模板；未指定但已在制的旧期保留旧引擎。两侧满幅蓝黑图形，不留白侧条；右侧为贯穿全高的64px完整亮蓝矩形，右下角不得留白或斜切缺口，正文安全边距保留。采集、配音、固定BGM及00:03循环、早晚安排、逐事件回顾去重、release与投稿流程不变。按对应后端使用renderer_backends.py check，技术样片强制preview/diagnostic_hold不投稿；新引擎实际截图、确定性、DOM边界、解码/导航与离线上传契约通过才启用。详情见docs/MULTIPLANE.md和RENDERER_ACCEPTANCE.md。
