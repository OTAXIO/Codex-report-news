> 每个新视频页面至少1张相关图片，含00、负责人和reset分页；新闻原图优先，缺图用对应游戏/软件/公司官方图标，本地保存来源与hash；无相关素材先补图，不能空白或用无关图凑数。详见docs/SCENE_IMAGES.md。


后续新正式片按 [48小时、来源与导览规则](docs/FRESHNESS_AND_SOURCES.md) 执行：仅原始发布48h内（临时6h/回顾24h更严），导入/release/首次提交共用门禁；森空岛默认非浏览器模式，暂无验收替代源时记录缺口；干员读gàn yuán，仅TTS词组替换；00标题有公司/产品/游戏或人物主体及具体事件。已发布不改。

> 2026-10-30 当前排序：早报morning默认AI动态→游戏资讯，晚报night默认游戏资讯→AI动态。00导览后正文01仍为真实封面头条，其他核实重大消息随后置顶，再按本期时段排列剩余栏目；无重大消息从该时段首栏目选头条，素材不足可由另一栏目开场。统一story_order与lead_event_id，详见GAMES_FIRST.md。已有任务按固化顺序恢复，已发布不重做。

> 2026-10-28 当前内容升级：新主片仅AI动态＋游戏资讯，移除社会新闻。游戏只看明日方舟国服/英文国际服与明日方舟：终末地，推荐2＋2但无上限、无最低配额；更新优先，其次活动，官方RSS/官网优先、官方X补充。所有正式MP4实际时长必须>30.0秒（目标≥31秒），release和上传前实际ffprobe核验；不足修内容，不靠空白/重复/降速凑时长。tibo reset完整原文保留并分页，详细中文播报，必要时超过2页；仍无导览、正文01、单一事件。新片固定标签“明日方舟”“终末地”，预留活动名额。已发布视频不重做不重传。完整接口与验收见docs/AI_GAMES_PRODUCTION.md。

历史基线：**V_0**，保留在 [V_0 手册](docs/V_0/README.md)。当前运行见下方短入口。

# 新闻视频项目

常规运行先读 [当前执行入口](docs/CURRENT_RUNBOOK.md)；详细规则和历史状态按需展开。

当前由 Codex 制作和协助发布，DSH 的交接入口在 ../../handoff/START_HERE.md。完整规则、工作流和 STATE 按当前阶段或异常需要再读。

最新流程为：制作与检查 → 先准备 release 成品包 → 从 release 上传 → 发布确认后清理。当前已发布示例在 ../../release/2026_10_26_night/2026_10_26_night_晚间新闻.mp4。

常用入口：

- news_video.py：doctor、collect、candidates、import-editorial、voice。
- production_flow.py：plan/status/advance/resume，给出紧凑阶段并复用现有确定性命令；编辑与视觉判断仍由制作会话完成。
- leader_sources.py：每小时仅通过 Agent Reach 只读读取 tibo；其他负责人和公司X在主片制作前刷新。详见 docs/X_SOURCES.md。
- cover_generator.py <episode>：读取每期 cover.json 生成双比例事实封面。
- build_film.py <episode>：可编辑 HTML、单行字幕及两大模块导航。
- render_sample.py <episode>：渲染与实际校验，先准备合格 release，再写已用日志并附入成品包，然后调用已授权投稿。
- release_manager.py prepare <episode> --slot night：仅准备成品包，不发布。
- uploader_plan.py <release-dir>：只产出上传元数据与核对清单，拒绝已发布包，不联网。
- finalize_release.py <episode> --slot night --published：发布确认后收尾；--dry-run 列清理计划。
- audience_metrics.py <CSV>：只读导入后台24/72小时观看数据；缺分母不反推。
- build_handoff.py：构建无凭据/模型/依赖的 DSH 交接 ZIP。

使用说明与全部 PowerShell 步骤在 docs/WORKFLOW.md；本机路径及换机限制在 DEPENDENCIES.md。固定日期的 make_sample_editorial.py、prepare_publish_20261026.py、make_daily_cover.py、upgrade_v5.py 仅为历史样例，不能当成每日实时内容生成器。

早晚主片及小时巡检自动任务已启用，当前仍由代理承担编辑核验而非另配选题API。独立codex-upload已完成Chrome真实新稿投稿及公开核验；新的小时事件触发全链、Edge仍待实际验证。GitHub 调研在 docs/BILIBILI_UPLOAD_RESEARCH.md；不把存在上传仓库当作已验证可用。

小时巡检入口 hourly_monitor.py；tibo reset 紧急队列和独立临时稿用 reset_alerts.py，详见 docs/RESET_ALERTS.md。临时新闻不占早晚两期；真实新稿完整平台链路曾验证，未来平台变化仍须以每期实际回执判断。

自动投稿入口与成品契约：docs/CODEX_UPLOAD.md；upload_bridge.py 负责 prepare/publish/verify/pending，render 默认调用。
