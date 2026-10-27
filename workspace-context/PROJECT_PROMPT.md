> 2026-10-27 最新采集范围：小时巡检只读取 tibo @thsottiaux 并处理 reset、回查投稿；不采集社会 RSS，不读取公司或其他负责人 X。社会 RSS、公司官方 X 和其他负责人仅在视频制作前刷新。每期执行 collect --kind all（社会 RSS + AI 官方来源 + 全部启用 X），不能只复用旧社会缓存。新模型线索在制作阶段采集后按 MODEL_ALERTS 核验，已有授权与去重规则保留。

# 新闻视频项目当前指令

当前执行者Codex，DSH为未来可接手环境。先读[当前完整制作规则](Codex-report-news/News_Video/docs/PRODUCTION_RULES.md)、[工作流](Codex-report-news/News_Video/docs/WORKFLOW.md)、[状态](Codex-report-news/News_Video/docs/STATE.md)。2026-10-27最新用户要求已落实到项目代码，本文链接优先于历史样片和旧提示词。

- 06/12/18早午晚主片，分别05:45/11:45/17:45启动；小时只采tibo，社会RSS和公司/其他负责人X在制作前刷新。
- 新鲜明确tibo reset、新模型正式发布经语义核验后自动临时投稿；主片仍有近24小时重要回顾，不能被普通去重排除。
- 白底黑字蓝色点缀；单行内嵌字幕；来源时间到分钟。概览00、正文01，无概览也正文01。reset紧急稿默认直入。
- Qwen3-TTS0.6B上下文生成，纠正调用diào、模型名短停顿，保留句间0.4秒/新闻间0.6秒。
- 封面不画日期上方多余说明；小日期删去，大日期与“模型发布速报”等类型说明保留。
- 先release，默认科技数码/News/原创禁止转载+AI生成/固定明日方舟终末地创作者应援计划，真实回执与公开核验分开。旧发布视频不改、不重传。
- 按相关skill制作/上传，不泄露或打包凭据、模型或字体。变更详情/接口/测试见完整规则和对应文档。


已授权新闻不得等待人工试听确认再投稿。早报故障恢复、旧日志兼容、已开封面窗口、安全回查后单次恢复与diagnostic_hold约束见docs/PRODUCTION_RULES.md“早报故障后的自动投稿约束”；执行render_sample.py --resume-export或upload_bridge.py recover续接既有成品，禁止重置unknown或盲目二投。


最新：主片AI建议国内3＋国外3（非硬性指标），24小时内有效未用新事件优先，不足记录缺口，不凑旧闻，回顾单列、合格新闻仍无上限。使用candidates.ai_coverage和导入时ai_shortfall_reasons/ai-coverage-audit；GoogleAI、GoogleDeepMind、Kimi_Moonshot、MiniMax_AI均只在视频制作前读取。投稿采用字段级恢复、重复提交守卫和实现指纹；修复统一sync_upload_skill部署并验证，详见PRODUCTION_RULES.md。


后续所有新闻固定活动：明日方舟终末地创作者应援计划，话题ID1325166，strategy=explicit；替换科技猎手，不自动选择其他热门活动。必须核对真实活动标记，不可用则保留release并报告。既往发布稿不修改。


当前补充：AI条数与3＋3比例仅建议，按实际有效素材制作、不生造；少选理由可选不阻塞。选题覆盖腾讯WorkBuddy、混元/HY，以及Codex/Claude Code等官方产品与Agent，读取已核验RSS/X/官网更新日志；产品支持现有模型不当成新模型发布。详见PRODUCTION_RULES.md“建议条数与产品 / Agent 来源”。


新版画面导览：00展示完整主语标题＋一句事实说明，通常3—4项、两列布局，附有主语的板块总述；不用short_title标签凑目录，不放思考过程。仅根据本期实际内容生成。口播仍只说“这是本视频的导览。”并留2秒，不逐条朗读；reset仍默认无导览。细则和代码见PRODUCTION_RULES.md、layout_policy.py、build_film.py。


当前负责人规则：正常、新鲜且有信息价值的推文优先考虑（包括观点/体验）；主片tibo已核实reset在公司前、普通发言在公司后社会新闻前，tibo最多1页，其他负责人每人最多2页。画面强调已核实身份；口播可省职位但必须有姓名主语＋原帖北京时间＋具体内容，不能用采集时间或编造分钟。近24小时未用负责人候选须入选或用tibo_consideration/leader_consideration记录真实skip/defer原因；leader_editorial.py在导入配音前落实身份、主语时间、排序和页数，输出审计到release。规则细节见PRODUCTION_RULES.md和X_PRESENTATION.md；不改已发布稿、不改小时采集范围、不把reset关键词当已核实公告。


背景音乐当前要求：后续主片/临时新闻使用本地assets/music/oshinko.flac《おしんこ》，全片固定低音量循环到片尾；不用播报ducking，不在停顿时抬高。audio_mix.py统一生成soundtrack.wav供预览和渲染复用，原配音独立保留、实测报告随release。目标音乐显著低于播报，必要时全曲统一降低；原曲不进Git/交接ZIP，缺源或哈希错误停止。详见docs/BACKGROUND_MUSIC.md；既往成品不重做。

背景音乐循环：首遍从头，第二遍起每轮从00:03开始，开头3秒只播放一次；config.background_music.repeat_from_seconds=3。

今天（2026-10-27）午间新闻开始使用本次背景音乐流程：首次从头、后续从00:03循环，固定低音量，无播报闪避；新稿背景音乐需求经release门禁核对再上传。

背景音乐可听性修正：以正常播报窗口中位数定固定增益（参考差18dB、目标-32LUFS、音乐峰值-24dBFS），不再用最弱尾字限制整首导致听不到。仍无ducking、后续从00:03循环；原曲本体位于项目assets/music/oshinko.flac。详见BACKGROUND_MUSIC.md，午报使用此新版。
