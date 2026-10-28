> 2026-10-28 当前内容升级：新主片仅AI动态＋游戏资讯，移除社会新闻。游戏只看明日方舟国服/英文国际服与明日方舟：终末地，推荐2＋2但无上限、无最低配额；更新优先，其次活动，官方RSS/官网优先、官方X补充。所有正式MP4实际时长必须>30.0秒（目标≥31秒），release和上传前实际ffprobe核验；不足修内容，不靠空白/重复/降速凑时长。tibo reset完整原文保留并分页，详细中文播报，必要时超过2页；仍无导览、正文01、单一事件。新片固定标签“明日方舟”“终末地”，预留活动名额。已发布视频不重做不重传。完整接口与验收见docs/AI_GAMES_PRODUCTION.md。

当前项目版本：**V_0**。先读 [项目手册](docs/V_0/README.md) 和 [当前制作规则](docs/PRODUCTION_RULES.md)。

# 新闻视频项目

常规运行先读 [当前执行入口](docs/CURRENT_RUNBOOK.md)；详细规则和历史状态按需展开。

先读根目录 PROJECT_PROMPT.md，以及 docs/REQUIREMENTS.md、WORKFLOW.md、STATE.md。当前由 Codex 制作和协助发布，DSH 的交接入口在 ../../handoff/START_HERE.md。

最新流程为：制作与检查 → 先准备 release 成品包 → 从 release 上传 → 发布确认后清理。当前已发布示例在 ../../release/2026_10_26_night/2026_10_26_night_晚间新闻.mp4。

常用入口：

- news_video.py：doctor、collect、candidates、import-editorial、voice。
- production_flow.py：plan/status/advance/resume，给出紧凑阶段并复用现有确定性命令；编辑与视觉判断仍由制作会话完成。
- leader_sources.py：每小时通过 Agent Reach 只读读取白名单负责人推文；tibo 先于 OpenAI 官方，其他负责人先于对应公司，支持仅有负责人新消息的选题。详见 docs/X_SOURCES.md。
- cover_generator.py <episode>：读取每期 cover.json 生成双比例事实封面。
- build_film.py <episode>：可编辑 HTML、单行字幕及两大模块导航。
- render_sample.py <episode>：渲染、实际校验、写已用日志并准备 release，返回命名成品路径。
- release_manager.py prepare <episode> --slot night：仅准备成品包，不发布。
- uploader_plan.py <release-dir>：只产出上传元数据与核对清单，拒绝已发布包，不联网。
- finalize_release.py <episode> --slot night --published：发布确认后收尾；--dry-run 列清理计划。
- build_handoff.py：构建无凭据/模型/依赖的 DSH 交接 ZIP。

使用说明与全部 PowerShell 步骤在 docs/WORKFLOW.md；本机路径及换机限制在 DEPENDENCIES.md。固定日期的 make_sample_editorial.py、prepare_publish_20261026.py、make_daily_cover.py、upgrade_v5.py 仅为历史样例，不能当成每日实时内容生成器。

早晚主片及小时巡检自动任务已启用，当前仍由代理承担编辑核验而非另配选题API。独立codex-upload已完成Chrome真实新稿投稿及公开核验；新的小时事件触发全链、Edge仍待实际验证。GitHub 调研在 docs/BILIBILI_UPLOAD_RESEARCH.md；不把存在上传仓库当作已验证可用。

小时巡检入口 hourly_monitor.py；tibo reset 紧急队列和独立临时稿用 reset_alerts.py，详见 docs/RESET_ALERTS.md。临时新闻不占早晚两期，上传后端未验收时先完成 release 并通知。

自动投稿入口与成品契约：docs/CODEX_UPLOAD.md；upload_bridge.py 负责 prepare/publish/verify/pending，render 默认调用。
