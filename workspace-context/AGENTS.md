> 2026-11-11 资讯量与X连接（用户要求“全部修复”）：采集前先`python -B x_reach.py probe`预热X阅读器（首次读取给150秒）；单个账号超时/上游出错按阅读器暂停时间重试1次，仍失败跳过并在末尾补读一轮，连续3个账号失败才判X_UNREACHABLE（冷却2分钟），NEED_LOGIN/PLATFORM_BLOCKED/RATE_LIMITED立即停止不重试；报告`pending_handles`非空时冷却后`python -B leader_sources.py --retry-failed`只补读这些账号；`python -B x_reach.py doctor`看各账号近期成功率（data/x-health.jsonl）。AI候选按观众相关度排序（rank_score）、同一事件归组（cluster），data/candidates.json的must_review列前40组，导入时每组须有选用或落选理由（REVIEW_COVERAGE，一条理由覆盖整组）。新增“快讯”页（scene_type=briefs，每页2–3条已采集、48h内、未播过的次要消息，不当头条、不进标题），每条记入已用新闻，简介时间轴列出各条与链接。新增来源404 Media、Ars Technica AI、ElevenLabs博客及X账号ElevenLabs/OfficialLoganK/elonmusk（只采信xAI/Grok第一手说法）；MiniMax官网与Kimi论坛本机TLS失败已停用，由X官方号与IT之家、kimi.com/blog覆盖。标题在60字内放2–3个最热事件。详见workspace-context/DSH_PROMPT.md（2026-11-11版）第2、3、3a、4节与FRESHNESS_AND_SOURCES.md“2026-11-11”节。已发布视频不重做。

> 2026-11-10 活动与版式（用户确认）：游戏情报的活动改为一页只讲一个活动（scene_type=activity，activity_items恰好1项，取代activity_overview），画面自动显示截止倒计时；分线上/线下/联动（kind，线下须location、联动须partner），主要活动在前、热度低的网页/社区小活动（scale=minor）在后，各自按即将结束→进行中→即将开始，由导入自动排序，每期最多6页；口播须念出截止日期；`python -B activities.py list|scan --series <game>`查看仍在进行和新发现的活动，进行中的活动可每期续报至结束（data/activity-ledger.json）。正文页图片框贴合图片、字号按版面自适应放大；配图加质量筛选（presentation.image_quality），过小或近乎空白的图不用，游戏页可自动换用同一公告内更好的图，`python -B scene_media.py rank <item_id>`辅助挑图。覆盖下文“活动一览每页1–3个”的表述。详见workspace-context/DSH_PROMPT.md第3a节、News_Video/docs/FRESHNESS_AND_SOURCES.md、SCENE_IMAGES.md、MULTIPLANE.md的2026-11-10节。已有render-plan的在制期次与已发布视频不变。

> 2026-11-09 内容改版（用户确认）：AI早报加入传闻（X爆料账号分A/B/C级＋模型家族关键词搜索；门槛tierA_source/two_independent/artifact三选一；口播首句点名来源并用“称/爆料”，末句写官方状态，不得写成定论；标题带曝/传/疑似；data/rumor-ledger.jsonl 7天去重）、媒体报道（量子位改为普通媒体源，新增TechCrunch/The Verge/IT之家，口播须“据+媒体名”）、GitHub今日热门（自动过滤有害/无关仓库，固定最后、不当头条）；游戏情报加入活动一览（freshness_basis=active_window，1–3个官方活动）和玩家热议（独立B站阅读profile只读最热/最新评论与弹幕，由用户本人小号登录一次，程序不代登、不导出Cookie、不调评论API；对象须为game_glossary.json已审核词，样本≥30）。标题可加≤16字title_hook，禁用“震惊/炸裂”等夸张词；简介未写时release自动生成；合集按题材AI-News/Game-News。补充栏目采集失败只跳过该栏目，正片照常。覆盖下文“传闻不报”“量子位qbitai-leads为lead_only线索源”。完整字段见workspace-context/DSH_PROMPT.md（2026-11-09版）第2、3a节。

> 2026-11-07 系列拆分（用户确认）：早报改为只讲AI的「AI早报」（edition_series=ai，ID daily-YYYYMMDD-morning，科技数码，活动取可参加的免费活动中热度最高的most_popular_free，没有就不挂）；晚报拆成两条独立视频「明日方舟情报」（arknights，ID daily-YYYYMMDD-night-arknights，游戏分区，活动8314）和「终末地情报」（endfield，ID daily-YYYYMMDD-night-endfield，游戏分区，活动1325166）。每条只讲本系列，无合格消息则当期不出；editorial顶层须填edition_series与hook（开场头条句，替代“这是本视频的导览”）；candidates加`--series`。森空岛纯长图官方帖用`python -B skland_sources.py ocr <id>`本机OCR补正文，事实须对图核对。量子位qbitai-leads为lead_only线索源，不能直接引用。新增X官方号XiaomiMiMo/StepFun_ai/Baidu_Inc。覆盖下文“早报AI→游戏、晚报游戏→AI”“活动morning=1325166/night=8314”及“固定标签明日方舟/终末地”的表述（混合版旧期次保持兼容，已发布不重做）。完整流程见workspace-context/DSH_PROMPT.md（2026-11-07版）。官方PV片段未获确认，不做；传闻不报。

> 2026-11-05 制作方：用户决定早晚报交回DSH（DeepSeek Harness）制作并按既有授权自动投稿（producer填"DeepSeek Harness"），Claude Code停止制作；Claude桌面任务news-morning/news-night已停用，不得自行恢复，除非用户再明确授权。作废2026-11-02“Claude Code制作”条目。DSH按Codex-report-news/workspace-context/DSH_PROMPT.md（2026-11-05版）接手，自行调度北京06:00早报/18:00晚报，每次按北京时间判定期次并防重，unknown先回查。交接时最后一期为2026-11-05早报BV1PRxd6PEKN（Claude制作，已提交待审）。

> 2026-11-02 内容增强（用户确认）：森空岛改由制作者在Claude内置浏览器打开官方区，运行News_Video/skland_capture.js读取页面已渲染数据，保存data/skland-captures/后`python -B skland_sources.py import <文件>`导入；不登录、不提取Cookie、不逆向签名、不重放请求、不用用户Chrome/BrowserSkill。X引用帖正文随采集保存，线程用`python -B leader_sources.py thread <item_id>`补全；帖内官方链接读原文（openai.com 403时用内置浏览器）。新增AI来源xAI/Mistral/Gemini博客/GitHub Copilot/Cursor/NVIDIA及X官方号MistralAI/AIatMeta/GeminiApp/cursor_ai。【决策】游戏公告超48h但生效时间（开服/活动/卡池/维护）在本期前后24h内，可用freshness_basis=effective_time并原文引用生效时间入选；每期最多1页72h活动日程（freshness_basis=schedule）。AI的48h门禁不变。每期import自动生成selection-report.json。详见Codex-report-news/News_Video/docs/FRESHNESS_AND_SOURCES.md“2026-11-02内容增强”。

> 2026-10-31 视觉默认：用户确认样片后，新早晚主片及temporary临时新闻默认multiplane/persona（P3蓝白版：#01A1FE与白主色、斜切页眉、白色斜切编号标签、换页斜向擦屏），config.rendering.default_template=persona；临时稿首次构建显式`--renderer multiplane --template persona`。覆盖下文及历史文档中“默认B/graphic”“临时新闻统一graphic”的表述；右侧64px满高蓝块、阅读区、单行字幕、导航与MP4验收不变。已有render-plan的在制期次沿用原模板，已发布不重做。封面同日改为P3蓝白版：config.cover_generation.style=persona（仍由cover_generator.py <id>的Pillow路径生成，16:9与4:3分别排版，日期只出现一次，文字仍取自cover.json并须见于头条），覆盖“2026-10-28封面恢复旧版/legacy”的表述；`--style legacy`可显式出旧版。详见Codex-report-news/News_Video/docs/MULTIPLANE.md。

> 2026-10-30 运行保护：用户已关闭每小时tibo/reset巡检，保持暂停，不因历史提示词自动恢复。早晚制作继续。接管或迁移先备份并核对运行目录、未提交改动和已用日志，不在生产目录直接执行git restore/reset/clean或镜像覆盖来代替环境修复。原曲和配音参考属于生产源素材，当前存于工作区media-library（代码仓库外），按config及哈希读取；不能当缓存删除。恢复记录见docs/RECOVERY_20261030.md（News_Video内）。

> 2026-10-29：后续每页至少一张相关图片（含导览/负责人/reset分页），新闻原图优先，缺图用对应官方游戏/软件/公司标识；规则见Codex-report-news/News_Video/docs/SCENE_IMAGES.md。已发布不改。

> 2026-10-29 新制作：原发布时间48h硬门禁（临时6h/回顾24h继续更严）；森空岛停用默认BrowserSkill，未验证替代源时报缺口，其他官网/X继续；干员读gàn yuán（干四声，TTS-only）；导览明确公司/产品/游戏/人物及事件。详细接口见Codex-report-news/News_Video/docs/FRESHNESS_AND_SOURCES.md。已发布不修改。

> 2026-10-30 当前排序：早报morning默认AI动态→游戏资讯，晚报night默认游戏资讯→AI动态。00导览后正文01仍为真实封面头条，其他核实重大消息随后置顶，再按本期时段排列剩余栏目；无重大消息从该时段首栏目选头条，素材不足可由另一栏目开场。统一story_order与lead_event_id，详见GAMES_FIRST.md。已有任务按固化顺序恢复，已发布不重做。

> 2026-10-28 当前内容升级：新主片仅AI动态＋游戏资讯，移除社会新闻。游戏只看明日方舟国服/英文国际服与明日方舟：终末地，推荐2＋2但无上限、无最低配额；更新优先，其次活动，官方RSS/官网优先、官方X补充。所有正式MP4实际时长必须>30.0秒（目标≥31秒），release和上传前实际ffprobe核验；不足修内容，不靠空白/重复/降速凑时长。tibo reset完整原文保留并分页，详细中文播报，必要时超过2页；仍无导览、正文01、单一事件。新片固定标签“明日方舟”“终末地”，预留活动名额。已发布视频不重做不重传。完整接口与验收见docs/AI_GAMES_PRODUCTION.md。

> 2026-10-28 最新活动规则：早报morning使用“明日方舟终末地创作者应援计划”（1325166）；晚报night使用“明日方舟创作者应援计划”（8314）。按edition_slot与用户配置activity_by_slot选择，strategy=explicit、fallback=stop；精确活动搜索及图标读回要求不变。临时新闻沿用原终末地活动，已发布稿件不修改。本规则覆盖历史“所有新闻统一终末地”活动要求。

## 小时巡检轻量入口

reset心跳按`Codex-report-news/News_Video/docs/HOURLY_MONITOR_PROMPT.md`执行，日常只运行采集/队列检测及投稿回查。无待办时不预读PROJECT_PROMPT、制作规则、WORKFLOW、STATE或skill，不检查源码及已完成成品。本分支覆盖下文通用预读要求；有待核验reset、待制任务或投稿异常时，才按需读取相应规则，功能和核验/防重约束不变。

> 2026-10-27 最新主片安排：取消午间新闻，只制作北京时间06:00开始的morning早报和18:00开始的night晚报；不提前15分钟，质检通过后沿用默认设置自动投稿。不再制作、补做或投稿新的noon午报。tibo reset临时新闻及每小时30分巡检保留。历史午报成品与记录保留。

> 2026-10-27 最新采集范围：小时巡检只读取 tibo @thsottiaux 并处理 reset、回查投稿；不采集社会 RSS，不读取公司或其他负责人 X。社会 RSS、公司官方 X 和其他负责人仅在视频制作前刷新。每期执行 collect --kind all（AI/游戏官方来源 + 已启用X，社会源停用），不能只复用旧社会缓存。新模型线索在制作阶段采集后按 MODEL_ALERTS 核验，已有授权与去重规则保留。

# 新闻视频项目入口

常规制作先读 `Codex-report-news/News_Video/docs/CURRENT_RUNBOOK.md`；详细制作、上传、语音及历史状态按需查对应文档。小时巡检仍只用 `docs/HOURLY_MONITOR_PROMPT.md` 轻量入口。本段覆盖下文“每次都预读完整 PROJECT_PROMPT/WORKFLOW/STATE”的旧要求。

本项目当前由 Codex 制作并协助发布，DSH 仅是未来可接手的执行环境。先读 `PROJECT_PROMPT.md`，再读 `Codex-report-news/News_Video/docs/WORKFLOW.md` 与 `Codex-report-news/News_Video/docs/STATE.md`。这些文档包含用户今天确认的最新规则，优先于旧样片、旧提示词和历史记录。

制作遵循 `Codex-report-news/News_Video/skills/news-video-production/SKILL.md`；文稿遵循项目内 `help-me-speech`。不要把内部计划、核验措辞、提示词或思考过程写进公开画面和口播。

制作完成先准备 `release/YYYY_MM_DD_{morning|night}/`，上传只使用其中带日期和时段的 MP4。发布确认后才清理工作残留。不要覆盖已发布成品，不重复上传 2026-10-26 晚间版。

`Voice_Generate`、`admin_retrain`、`admin_voice_study` 为既有语音项目：只调用必要入口，不擅自修改模型、训练或清理这些目录。账号、Cookie、浏览器 profile、API key、模型权重和微软字体不进入交接包或 Git。

每小时只采集tibo；AI/游戏官方来源、公司官方X及其他负责人在视频制作前读取；先读Codex-report-news/News_Video/docs/PRODUCTION_RULES.md。新模型正式发布按MODEL_ALERTS.md核实后自动临时投稿，主片仍包含重要回顾。tibo 明确宣布额度 reset 时按 Codex-report-news/News_Video/docs/RESET_ALERTS.md 优先制作“临时新闻”，不占早晚两期。临时稿另用 release/YYYY_MM_DD_temporary_HHmmss_alertid/，只呈现重置推文信息。同一重置去重，先核验语义，先 release 再上传；未取得发布回执不记成功。

自动投稿使用 Codex-report-news/News_Video/skills/codex-upload/SKILL.md 与 docs/CODEX_UPLOAD.md；当前用户已授权新一期按默认设置自动最终提交。Chrome 优先，Edge 后续兼容。提交和审核发布分开，未知回执先回查，不能重投；今天已发布版有哈希防重记录。


## Multiplane视觉扩展

新增可选multiplane/editorial（A清爽编辑版）与multiplane/graphic（B强图形版），实际验收通过，用户选定后新期默认B（multiplane/graphic）；hyperframes/legacy保留。每期render-plan锁定后端/版本/模板；未指定但已在制的旧期保留旧引擎。两侧满幅蓝黑图形，不留白侧条；右侧为贯穿全高的64px完整亮蓝矩形，右下角不得留白或斜切缺口，正文安全边距保留。采集、配音、固定BGM及00:03循环、早晚安排、逐事件回顾去重、release与投稿流程不变。按对应后端使用renderer_backends.py check，技术样片强制preview/diagnostic_hold不投稿；新引擎实际截图、确定性、DOM边界、解码/导航与离线上传契约通过才启用。详情见docs/MULTIPLANE.md和RENDERER_ACCEPTANCE.md。


### 临时新闻统一B版（2026-10-27）

后续新建的所有temporary临时新闻（tibo reset及核实的新模型发布）统一采用multiplane/graphic，即B强图形版，与早晚主片一致。首次构建显式使用`python -B build_film.py <id> --renderer multiplane --template persona`并读回render-plan.json；现有config默认已经是B，临时期次复用相同的后端选择逻辑，不另建采集/音频/投稿流水线。右侧64px完整亮蓝矩形贯穿全高、右下角填满，左右无白边，中间白底黑字，单行字幕和临时新闻独立导航。

reset仍只讲该次已核实重置消息，不加00导览、正文01起；新模型临时稿继续遵循MODEL_ALERTS的概览及页数规则。不占早晚主片次数，主片重点回顾仍逐事件日内去重。使用`renderer_backends.py check <id>`及实际截图、最终MP4解码/导航/字幕/边缘检查，质检后先release再按既有授权自动投稿。

B失败先诊断修复，不静默改A或旧引擎；明确回退需新修订并记录真实原因。已有固定render-plan的在制任务沿用原计划。已发布的视频、封面与投稿记录不重做、不修改、不重传；unknown先回查，同原帖/事件防重。小时任务继续每小时30分只读tibo并处理reset/投稿回查，不扩大到公司X或社会RSS。


### 2026-10-28 封面恢复旧版（当前有效）

用户确认后续早报、晚报及临时新闻的封面统一恢复原cover_generator.make_hyperframes/Pillow配置，config.cover_generation.backend=hyperframes、style=legacy；正常调用cover_generator.py <id>即可，不再跟随视频后端自动换用Multiplane封面。视频本体仍是Multiplane B（graphic），render-plan保持不变。旧封面的版式、标题层级、logo处理与双比例输出沿用原实现；真实新闻标题、单次大日期、简短类型说明、双封面及投稿规则照旧。此要求覆盖此前“B版生成双封面”的措辞；B仅指视频画面。只作用于之后新制作的封面，不重做或覆盖已发布封面/视频，不重投旧稿。


### 2026-10-28 背景音乐小幅调高（当前有效）

用户反馈BGM仍偏小，后续新制作采用约+3dB版本：音乐初始目标-29LUFS（原-32）、峰值上限-21dBFS（原-24）、正常播报窗口中位参考差至少16dB（原18）。按audio_mix一次选择恒定增益，实际每期仍受播报优先与峰值约束，不承诺每期恰好+3dB。配音基准-16LUFS不变；无ducking、不随播报/停顿升降，首遍从00:00、后续每轮00:03到曲尾，前3秒只出现一次。此条覆盖历史“停止提高音量”和旧数值要求。

真实原曲与既有新闻配音完成100秒新旧对照：音乐峰值-24→-21dBFS，实际提高3dB；新版正常播报参考差约19.02dB，恒定增益、无ducking及3秒循环检查通过。数值检查不等于用户主观听感认可。仅后续新片使用；既有release的恢复按原成品继续，已发布视频不重混、不重做、不重传。混音由audio_mix统一生成，预览和成片复用soundtrack.wav，不二次整体归一化，release按本期固化参数/哈希核验。
