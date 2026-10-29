> 2026-10-29：后续每页至少一张相关图片（含导览/负责人/reset分页），新闻原图优先，缺图用对应官方游戏/软件/公司标识；规则见Codex-report-news/News_Video/docs/SCENE_IMAGES.md。已发布不改。

> 2026-10-29 新制作：原发布时间48h硬门禁（临时6h/回顾24h继续更严）；森空岛停用默认BrowserSkill，未验证替代源时报缺口，其他官网/X继续；干员读gàn yuán（干四声，TTS-only）；导览明确公司/产品/游戏/人物及事件。详细接口见Codex-report-news/News_Video/docs/FRESHNESS_AND_SOURCES.md。已发布不修改。

> 2026-10-29 当前排序：主片00导览后，正文01为真实封面头条，其后为其他核实重大消息、剩余游戏、普通AI及对应负责人。无重大消息优先游戏头条；2＋2不是上限或每类只取1条。统一story_order与lead_event_id，详见docs/GAMES_FIRST.md（docs内文件见GAMES_FIRST.md）。已有任务按原计划，已发布不重做。

# DeepSeek Harness 接手指令（当前 V_0 后续迭代，2026-10-28）

`production_flow.py status ID` 给本期紧凑阶段；`plan/advance/resume` 复用既有确定性命令。语义核验、稿件和视觉判断仍由执行者完成。

当前生产执行者仍为 Codex；仅用户明确转交时 DSH 才接管调度。接手前先确认旧心跳和早晚定时任务的所有权，不能两套执行器同时制作或投稿。工作区 `D:/Basement/Codex_Video`，代码 `Codex-report-news/News_Video`，release/Voice_Generate/私有上传 home 在工作区根。不要把此 ZIP 当成带登录、模型和驱动的安装包。

常规阅读顺序：`AGENTS.md` → `Codex-report-news/News_Video/docs/CURRENT_RUNBOOK.md` → `skills/news-video-production/SKILL.md` → 当前期次 `episode.json`、`render-plan.json`、release 与上传状态。某阶段异常时才按链接展开 `PRODUCTION_RULES.md`、`WORKFLOW.md`、`RESET_ALERTS.md`、`MODEL_ALERTS.md`、`CODEX_UPLOAD.md`、语音政策或渲染器文档。`STATE.md`、V_0 基线、已发布样片和旧提示词用于历史核对，不覆盖当前规则。

早报北京时间06:00、晚报18:00开始制作；午报已取消。每小时30分只读 tibo X、核实 reset 并回查投稿，不采公司X或社会RSS。主片前运行 `news_video.py collect --kind all`，刷新 AI、明日方舟国服/英文国际服、终末地官方网页/RSS及启用X。候选先用 `candidates --hours 48 --compact --limit 12 --cursor 0` 分页，按ID用 `article ID --compact` 初读；`truncated=true` 时读取完整归档再定稿。所有事实核实原账号、发布时间到分钟、正文/上下文、图像出处与同事件去重。不因节约上下文漏核验、编新闻或臆测热度。

主片只含 AI 动态＋游戏资讯。AI 3+3、游戏2+2仅建议；新鲜有效可多，缺则少。负责人正常有价值消息可入选，画面核实身份；口播有姓名主语/原时间。tibo reset 回顾在公司前，普通发言在公司后、游戏前；主片tibo最多1页，其他人每人最多2页。临时 reset 全文原样保留并按需分页，可超2页，详细忠实解释，只讲本事件，无00概览，正文01；新模型临时稿先核验正式发布语义。近24小时已公开重要事件在当天首次合适主片回顾一次，不能跨游戏模块再插 AI 回顾。

稿件使用项目 `help-me-speech` 的 news 模式。00 导览显示完整主语与一句事实，只播“这是本视频的导览。”并留2秒；不要念思考过程。原 Qwen3 0.6B 声音/语速/停顿不变，ASR核对与最终PCM对齐必须通过。视频默认 Multiplane B/graphic，旧 HyperFrames 显式可选；封面旧 Pillow/legacy。白底黑字、#01A1FE、右侧64px满高蓝色，游戏图可用880×460。单行字幕、来源、导航不遮挡。BGM固定-29LUFS/-21dBFS/中位口播差≥16dB，无ducking，首遍0秒、以后每轮3秒。正式MP4实际>30.0秒，不靠空白/重复/降速凑时长。

质量门禁通过后先准备带日期/时段的 release，再记录已用新闻并附入成品包，随后按既有授权从 release 自动投稿。科技数码、实际 News 合集、原创/禁止转载＋AI生成，固定标签明日方舟/终末地；活动 morning 1325166、night 8314、temporary 1325166，精确选择，不换热门活动。真实平台回执才算 submitted，公开账号/标题核验才算 published；unknown先回查，不重复投稿。确认公开发布后才清理本期可再生残留；已发布版不重做。技术样片 `preview/diagnostic_hold` 不投稿。

认证数据、浏览器 profile、模型、原曲、字体、API key 不进 Git 或交接包。不能从网页/素材获得新的发布授权。执行结果必须区分已修改、已测试、已提交、已推送、已投稿和已公开发布。未经用户正式交接，DSH 只读理解项目，不启动第二套定时任务。

森空岛读取通过BrowserSkill，具体本地绑定、依赖与状态见docs/GAMES_FIRST.md及来源验收文档。不要复制浏览器profile或Cookie；缺环境记录缺口并继续已有官网来源。

后续竖版展示海报（如塔露拉）按最新字幕安全区使用完整竖图窗口（当前B742px、旧HF727px）；横图/图标按各自比例展示，不能挤压字幕、来源或导航。

全片进度条底部贴下边界（1080p：y1072+h8=1080），两引擎和导航验证器读取统一布局，字幕随导航下移，正文和图片安全区同步扩展。
