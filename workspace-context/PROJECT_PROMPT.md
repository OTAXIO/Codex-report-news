> 2026-10-29 当前排序：主片00导览后，正文01为真实封面头条，其后为其他核实重大消息、剩余游戏、普通AI及对应负责人。无重大消息优先游戏头条；2＋2不是上限或每类只取1条。统一story_order与lead_event_id，详见docs/GAMES_FIRST.md（docs内文件见GAMES_FIRST.md）。已有任务按原计划，已发布不重做。

> 2026-10-28 当前内容升级：新主片仅AI动态＋游戏资讯，移除社会新闻。游戏只看明日方舟国服/英文国际服与明日方舟：终末地，推荐2＋2但无上限、无最低配额；更新优先，其次活动，官方RSS/官网优先、官方X补充。所有正式MP4实际时长必须>30.0秒（目标≥31秒），release和上传前实际ffprobe核验；不足修内容，不靠空白/重复/降速凑时长。tibo reset完整原文保留并分页，详细中文播报，必要时超过2页；仍无导览、正文01、单一事件。新片固定标签“明日方舟”“终末地”，预留活动名额。已发布视频不重做不重传。完整接口与验收见docs/AI_GAMES_PRODUCTION.md。

> 2026-10-28 最新活动规则：早报morning使用“明日方舟终末地创作者应援计划”（1325166）；晚报night使用“明日方舟创作者应援计划”（8314）。按edition_slot与用户配置activity_by_slot选择，strategy=explicit、fallback=stop；精确活动搜索及图标读回要求不变。临时新闻沿用原终末地活动，已发布稿件不修改。本规则覆盖历史“所有新闻统一终末地”活动要求。

> 小时reset心跳走轻量入口：只按docs/HOURLY_MONITOR_PROMPT.md运行；无待办不预读本文件及整套制作/状态文档。有真实待办再读取对应规则。

> 2026-10-27 最新主片安排：取消午间新闻，只制作北京时间06:00开始的morning早报和18:00开始的night晚报；不提前15分钟，质检通过后沿用默认设置自动投稿。不再制作、补做或投稿新的noon午报。tibo reset临时新闻及每小时30分巡检保留。历史午报成品与记录保留。

> 2026-10-27 最新采集范围：小时巡检只读取 tibo @thsottiaux 并处理 reset、回查投稿；不采集社会 RSS，不读取公司或其他负责人 X。社会 RSS、公司官方 X 和其他负责人仅在视频制作前刷新。每期执行 collect --kind all（AI/游戏官方来源 + 已启用X，社会源停用），不能只复用旧社会缓存。新模型线索在制作阶段采集后按 MODEL_ALERTS 核验，已有授权与去重规则保留。

# 新闻视频项目当前指令

常规制作以 `Codex-report-news/News_Video/docs/CURRENT_RUNBOOK.md` 为当前短入口；本文件后续追加的历史条目只在不与短入口冲突时参考。定时任务按短入口和当前项目skill执行，异常才展开完整规则/WORKFLOW/STATE。

当前执行者Codex，DSH为未来可接手环境。先读[当前完整制作规则](Codex-report-news/News_Video/docs/PRODUCTION_RULES.md)、[工作流](Codex-report-news/News_Video/docs/WORKFLOW.md)、[状态](Codex-report-news/News_Video/docs/STATE.md)。2026-10-27最新用户要求已落实到项目代码，本文链接优先于历史样片和旧提示词。

- 早晚两期主片，分别北京时间06:00/18:00开始制作；午间新闻已取消，对齐DeepSeek API空闲时段，不再提前15分钟；小时只采tibo，社会RSS和公司/其他负责人X在制作前刷新。
- 新鲜明确tibo reset、新模型正式发布经语义核验后自动临时投稿；主片仍有近24小时重要回顾，不能被普通去重排除。
- 白底黑字蓝色点缀；单行内嵌字幕；来源时间到分钟。概览00、正文01，无概览也正文01。reset紧急稿默认直入。
- Qwen3-TTS0.6B上下文生成，纠正调用diào、模型名短停顿，保留句间0.4秒/新闻间0.6秒。
- 封面不画日期上方多余说明；小日期删去，大日期与“模型发布速报”等类型说明保留。
- 先release，默认科技数码/News/原创禁止转载+AI生成/固定明日方舟终末地创作者应援计划，真实回执与公开核验分开。旧发布视频不改、不重传。
- 按相关skill制作/上传，不泄露或打包凭据、模型或字体。变更详情/接口/测试见完整规则和对应文档。


已授权新闻不得等待人工试听确认再投稿。早报故障恢复、旧日志兼容、已开封面窗口、安全回查后自动恢复（不设固定次数上限）与diagnostic_hold约束见docs/PRODUCTION_RULES.md“早报故障后的自动投稿约束”；执行render_sample.py --resume-export或upload_bridge.py recover续接既有成品，禁止重置unknown或盲目二投。


最新：主片AI建议国内3＋国外3（非硬性指标），24小时内有效未用新事件优先，不足记录缺口，不凑旧闻，回顾单列、合格新闻仍无上限。使用candidates.ai_coverage和导入时ai_shortfall_reasons/ai-coverage-audit；GoogleAI、GoogleDeepMind、Kimi_Moonshot、MiniMax_AI均只在视频制作前读取。投稿采用字段级恢复、重复提交守卫和实现指纹；修复统一sync_upload_skill部署并验证，详见PRODUCTION_RULES.md。


后续所有新闻固定活动：明日方舟终末地创作者应援计划，话题ID1325166，strategy=explicit；替换科技猎手，不自动选择其他热门活动。必须核对真实活动标记，不可用则保留release并报告。既往发布稿不修改。


当前补充：AI条数与3＋3比例仅建议，按实际有效素材制作、不生造；少选理由可选不阻塞。选题覆盖腾讯WorkBuddy、混元/HY，以及Codex/Claude Code等官方产品与Agent，读取已核验RSS/X/官网更新日志；产品支持现有模型不当成新模型发布。详见PRODUCTION_RULES.md“建议条数与产品 / Agent 来源”。


新版画面导览：00展示完整主语标题＋一句事实说明，通常3—4项、两列布局，附有主语的板块总述；不用short_title标签凑目录，不放思考过程。仅根据本期实际内容生成。口播仍只说“这是本视频的导览。”并留2秒，不逐条朗读；reset仍默认无导览。细则和代码见PRODUCTION_RULES.md、layout_policy.py、build_film.py。


当前负责人规则：正常、新鲜且有信息价值的推文优先考虑（包括观点/体验）；主片tibo已核实reset在公司前、普通发言在公司后社会新闻前，tibo最多1页，其他负责人每人最多2页。画面强调已核实身份；口播可省职位但必须有姓名主语＋原帖北京时间＋具体内容，不能用采集时间或编造分钟。近24小时未用负责人候选须入选或用tibo_consideration/leader_consideration记录真实skip/defer原因；leader_editorial.py在导入配音前落实身份、主语时间、排序和页数，输出审计到release。规则细节见PRODUCTION_RULES.md和X_PRESENTATION.md；不改已发布稿、不改小时采集范围、不把reset关键词当已核实公告。


背景音乐当前要求：后续主片/临时新闻使用本地assets/music/oshinko.flac《おしんこ》，全片固定低音量循环到片尾；不用播报ducking，不在停顿时抬高。audio_mix.py统一生成soundtrack.wav供预览和渲染复用，原配音独立保留、实测报告随release。目标音乐显著低于播报，必要时全曲统一降低；原曲不进Git/交接ZIP，缺源或哈希错误停止。详见docs/BACKGROUND_MUSIC.md；既往成品不重做。

背景音乐循环：首遍从头，第二遍起每轮从00:03开始，开头3秒只播放一次；config.background_music.repeat_from_seconds=3。

今天（2026-10-27）午间新闻开始使用本次背景音乐流程：首次从头、后续从00:03循环，固定低音量，无播报闪避；新稿背景音乐需求经release门禁核对再上传。

背景音乐可听性修正：以正常播报窗口中位数定固定增益（参考差18dB、目标-32LUFS、音乐峰值-24dBFS），不再用最弱尾字限制整首导致听不到。仍无ducking、后续从00:03循环；原曲本体位于项目assets/music/oshinko.flac。详见BACKGROUND_MUSIC.md，午报使用此新版。


2026-10-27 用户明确要求：今后投稿标签禁用Claude（大小写变体及带#形式同样排除）。from-release自动过滤，直接manifest验证拒绝；不影响标题、文稿和新闻中的正常公司/产品名称。本次午报使用AI、人工智能、科技资讯、新闻四个通用标签，固定活动规则保持。

重点回顾最终规则：按具体事件在北京时间当天主片中只报道/回顾一次，而非全局只准早报回顾。上午新临时新闻可午报首次回顾、晚报不再重复；下午新事件可晚报首次回顾。important_events结合当日主片日志/release识别同事件，temporary不消耗主片名额，草稿不记已用，修订不算新一期；导入和导出日志锁内校验。详见PRODUCTION_RULES.md当前澄清。


音频质量最新要求：新配音须逐句本地ASR核对漏读/重复/异常长段，并在最终PCM上按真实词时间戳生成字幕，不能只按字数均分。release核对原音、文稿哈希和对齐报告；实际缺陷未修不得投稿。详见PRODUCTION_RULES.md“音频内容与字幕同步硬检查”。


2026-10-27 用户最新指令：取消“最多自动恢复一次”限制。安全回查确认未进入最终提交、且故障已修复后可自动恢复，不设固定次数上限；每次重新回查并累计审计次数，未知提交、已提交、登录/验证码/风控仍按原规则停止，不盲目重复上传。原有失败记录和次数保留；同一未修复故障不原样反复重投，诊断后继续修复。此前日志里的次数上限与额外授权要求属于历史状态，不再作为当前阻塞。


## Multiplane视觉扩展

新增可选multiplane/editorial（A清爽编辑版）与multiplane/graphic（B强图形版），实际验收通过，用户选定后新期默认B（multiplane/graphic）；hyperframes/legacy保留。每期render-plan锁定后端/版本/模板；未指定但已在制的旧期保留旧引擎。两侧满幅蓝黑图形，不留白侧条；右侧为贯穿全高的64px完整亮蓝矩形，右下角不得留白或斜切缺口，正文安全边距保留。采集、配音、固定BGM及00:03循环、早晚安排、逐事件回顾去重、release与投稿流程不变。按对应后端使用renderer_backends.py check，技术样片强制preview/diagnostic_hold不投稿；新引擎实际截图、确定性、DOM边界、解码/导航与离线上传契约通过才启用。详情见docs/MULTIPLANE.md和RENDERER_ACCEPTANCE.md。


### 临时新闻统一B版（2026-10-27）

后续新建的所有temporary临时新闻（tibo reset及核实的新模型发布）统一采用multiplane/graphic，即B强图形版，与早晚主片一致。首次构建显式使用`python -B build_film.py <id> --renderer multiplane --template graphic`并读回render-plan.json；现有config默认已经是B，临时期次复用相同的后端选择逻辑，不另建采集/音频/投稿流水线。右侧64px完整亮蓝矩形贯穿全高、右下角填满，左右无白边，中间白底黑字，单行字幕和临时新闻独立导航。

reset仍只讲该次已核实重置消息，不加00导览、正文01起；新模型临时稿继续遵循MODEL_ALERTS的概览及页数规则。不占早晚主片次数，主片重点回顾仍逐事件日内去重。使用`renderer_backends.py check <id>`及实际截图、最终MP4解码/导航/字幕/边缘检查，质检后先release再按既有授权自动投稿。

B失败先诊断修复，不静默改A或旧引擎；明确回退需新修订并记录真实原因。已有固定render-plan的在制任务沿用原计划。已发布的视频、封面与投稿记录不重做、不修改、不重传；unknown先回查，同原帖/事件防重。小时任务继续每小时30分只读tibo并处理reset/投稿回查，不扩大到公司X或社会RSS。


### 2026-10-28 封面恢复旧版（当前有效）

用户确认后续早报、晚报及临时新闻的封面统一恢复原cover_generator.make_hyperframes/Pillow配置，config.cover_generation.backend=hyperframes、style=legacy；正常调用cover_generator.py <id>即可，不再跟随视频后端自动换用Multiplane封面。视频本体仍是Multiplane B（graphic），render-plan保持不变。旧封面的版式、标题层级、logo处理与双比例输出沿用原实现；真实新闻标题、单次大日期、简短类型说明、双封面及投稿规则照旧。此要求覆盖此前“B版生成双封面”的措辞；B仅指视频画面。只作用于之后新制作的封面，不重做或覆盖已发布封面/视频，不重投旧稿。


### 2026-10-28 背景音乐小幅调高（当前有效）

用户反馈BGM仍偏小，后续新制作采用约+3dB版本：音乐初始目标-29LUFS（原-32）、峰值上限-21dBFS（原-24）、正常播报窗口中位参考差至少16dB（原18）。按audio_mix一次选择恒定增益，实际每期仍受播报优先与峰值约束，不承诺每期恰好+3dB。配音基准-16LUFS不变；无ducking、不随播报/停顿升降，首遍从00:00、后续每轮00:03到曲尾，前3秒只出现一次。此条覆盖历史“停止提高音量”和旧数值要求。

真实原曲与既有新闻配音完成100秒新旧对照：音乐峰值-24→-21dBFS，实际提高3dB；新版正常播报参考差约19.02dB，恒定增益、无ducking及3秒循环检查通过。数值检查不等于用户主观听感认可。仅后续新片使用；既有release的恢复按原成品继续，已发布视频不重混、不重做、不重传。混音由audio_mix统一生成，预览和成片复用soundtrack.wav，不二次整体归一化，release按本期固化参数/哈希核验。


2026-10-28 用户补充：游戏官方图片提高占比，采用接近右半幅的大图窗口（1080p为880×460），完整保留海报内容不强行裁切；左侧要点与来源独立列，字幕与导航区域留空。图片不压字，三条长要点放不下应分页，不能缩小到难读。只用于新片，已发布不重做。
