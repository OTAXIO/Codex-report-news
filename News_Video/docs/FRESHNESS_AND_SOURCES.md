# 48小时、来源和导览政策（2026-10-29）

此规则覆盖旧文档中更宽的选题窗口，适用于后续新正式期次；已发布作品不修改。常规入口仍是CURRENT_RUNBOOK。

## 时效

freshness.py统一使用带时区的原始发布时间，满足reference_time−48h ≤ 原时间 ≤ reference_time。48h边界包含；未来、缺失、无时区和边界无法确认的日期精度消息排除。日期保留全天可能区间，必须整个区间落入窗口。原始文本、标准化时间、时区、精度、原URL保存data/time-evidence；已归档X/游戏原文及既有采集DB可作为历史时间证据，不能使用编辑稿自填时间。Atom只有updated没有published时不视为原发布时间。

候选cursor=0生成固定快照，后续cursor读取同一窗口；--hours仅允许1—48，较短窗口可用。重新采集后从cursor=0开始。导入在负责人/回顾合并后、排序和导览前重新校验并绑定原时间。release生成freshness-audit.json，首次提交前重新核验，失败保留成品及freshness-blocked.json，不启动投稿器。submitted/unknown/published先按原状态恢复，不因过期重投。临时稿6h、回顾24h继续采用更短限制。真实素材不足不扩大窗口，也不靠填充凑>30s。

旧公告今天生效不等于新公告；转载、翻译、重新发布、无新事实的提醒不刷新原事件。必要历史背景仅用于说明当期新事实；有实质进展需说明新增事实、原事件关联及新原始公告证据，继续执行跨语言事件去重。代码能够校验时间及已知重复，是否具有新事实仍需编辑对照原文，不能宣称模型语义已经由时间检查证明。

## 森空岛

默认停用skland_browser来源，保留明确opt-in的BrowserReader，不自动回退启动浏览器。每期采集报告source_gaps记录停用原因。其他已核验官方网页和X继续工作，游戏不按数量硬补。

本次HTTP实探：官方游戏页和文章页只返回约4KB脚本外壳，无正文或RSS声明；公开home接口请求返回400，未取得完整文章；RSSHub官方路由目录未发现skland命名空间，文档routes.json访问403。没有认证重放、签名逆向、Cookie提取或浏览器替代爬取，也没有把失败称作无新闻。以上不能证明全网不存在第三方RSS，只表示尚无经实测可用的替代源，因此本次不声称森空岛已迁移成功。

后续接入先验证原作者稳定ID+官方身份、完整原文/时间/图片和48h必要分页。第三方RSS要核对许可证、底层认证及延迟；摘要仅作为发现入口。遇401/403/429、验证码或登录要求停止对应渠道，不能换身份/后端绕过。网页/API转RSS不是官方原生RSS。不要为未实证需求新增庞大服务。

## 读音

Voice_Generate/tools/speech_text.py词组READINGS增加干员→赣员（gàn yuán；干四声，用户明确指定），与已有调用→掉用同属TTS输入同音替换。原文、画面和字幕继续写干员，不全局替换干。Qwen不支持的音素标签不编造；模型/参数未变。实际试听与声调主观验收必须区分，ASR识字正确不能证明声调正确。

## 导览

新导入设置overview_subject_policy=1。layout_policy根据游戏地区、公司、产品、人物和来源元数据生成subject，标题缺主体时只补主体，不编造动作。具体标题/事实说明缺失或只剩API额度、模型更新等泛称则要求补稿。Codex、ChatGPT、GPT/API不得混写。游戏明确国服/英文国际服/终末地。validate_overview在生成和封面/release/上传的lead契约中校验：标题+主体+说明+对应scene_id+首项对应正文01。正文是否确实支持动作/范围仍需语义核验。

主片00口播和2s保留，3—4项重点；导航可以缩短但主体仍可辨识；reset临时稿无00不变。统一story_order和lead_event_id不变。

## 2026-11-02内容增强（用户确认，当前有效）

背景：10-29至11-02各期只有2—6条。原因是来源断裂而非选题过严：森空岛停用、Anthropic/MiniMax列表无日期、DeepMind RSS被gzip、X引用帖与线程正文未保存，以及国服版本公告在活动上线时已超48h。

### 森空岛（内置浏览器捕获）

- 制作者在Claude内置浏览器打开`https://www.skland.com/game/arknights?cateId=1`与`https://www.skland.com/game/endfield?cateId=12`，等页面渲染后用javascript_tool运行`skland_capture.js`全文，把返回的JSON原样保存为`data/skland-captures/<source>-<UTC时间>.json`，再`python -B skland_sources.py import <文件...>`。
- 脚本只读取页面已渲染的条目（React props里的item/user），不发请求、不读Cookie、不签名、不重放；只保留72h内identity=2官方号，裁掉法律声明/FAQ等套话，正文上限1500字。导入时再核对官方作者白名单（明日方舟Arknights/明日方舟终末地/森空岛泰拉信使公署）、游戏与分区，按publishedAtTs定原始时间。
- 正文完整的条目直接生成`data/articles/<id>.json`；正文为空（视频帖）或被截断时，打开文章页再运行同一脚本导入详情。`collect`报告里skland来源显示最近一次导入时间，超过3小时记CAPTURE_REQUIRED，不能写成“无新闻”。
- 用户Chrome的BrowserSkill路径（skland_browser）仍为显式opt-in，不自动使用。B站、微博未登录被风控，默认不用；社区wiki不作新闻来源。

### 游戏生效时间与活动日程【决策】

- 官方游戏公告（官网、森空岛、官方X）原发布超过48h，但其生效时间落在核验时刻前24h至后24h内，可设`freshness_basis:"effective_time"`，并填`effective_at`（带时区ISO时间，按服务器时区）与`effective_quote`（官方原文中含该日期的原句）。freshness会核对原句确在归档原文中、包含该日期、公告不超过14天。口播写明公告发布日与生效日。
- 每期最多1页`freshness_basis:"schedule"`活动日程，`schedule_items`每项含item_id、source_type、effective_at、effective_quote，只收核验时刻起72h内开始或结束的活动（公告≤30天）。没有就不出。
- `python -B news_video.py game-schedule --days 14`列出近14天官方游戏条目及文中时间，供查找今日生效的旧公告。
- 回顾、临时稿及AI新闻不适用；AI仍为原发布48h。

### AI来源与X

- Anthropic、MiniMax及registry中带`link_pattern`的列表页（xAI、Cursor）读取文章页结构化日期并缓存于`data/article-dates.json`（每次最多新读12篇）。新增RSS：Mistral、Gemini产品博客、GitHub Copilot changelog、NVIDIA博客（只取AI产品/模型）。字节Seed、智谱、阶跃官网为前端壳，暂未启用。
- X新增已核验官方号MistralAI、AIatMeta、GeminiApp、cursor_ai；xai账号已迁至@SpaceXAI、ChatGPTapp不存在，未启用。游戏官方号每次读取20条。
- 引用帖正文随采集写入leader-posts的`quoted`并进入summary；线程用`python -B leader_sources.py thread <item_id>`补作者本人后续帖。帖子只有链接时读链接官方原文，引用原句写入evidence。

### 选题深度与复盘

- 素材充足时每期6—10条、约3—5分钟（AI 3—5，游戏3—6）；不足时如实变短。每条读完整官方原文，口播150—250字、facts 3—4条，补原文中的背景、时间、适用范围和影响对象，不加原文没有的评价。
- 游戏按“国服方舟/国际服方舟/终末地”三块检查：新版本或SideStory、新干员与卡池、活动规则、维护闪断、联动、直播前瞻、制作组通讯、创作活动。同一事件跨来源合并（如X只有标题、森空岛有全文），取最全官方原文。
- editorial可写`rejections:{item_id:原因}`；import自动生成`selection-report.json`（期次data目录与episode目录各一份），列出全部候选的入选/落选原因、来源条数和失败来源，unreviewed越少越好。

## 2026-11-09内容改版（用户确认，当前有效）

覆盖本页及旧文档中的“传闻不报”和“qbitai-leads为lead_only线索源”。各栏目都是有合格素材才做；补充栏目（传闻、GitHub、玩家热议）采集失败只跳过该栏目并记缺口，不中断collect或正片。编辑字段见workspace-context/DSH_PROMPT.md第3a节。

### 来源

- 媒体（`tier:"media"`，segment=media）：量子位qbitai-leads、TechCrunch AI、The Verge AI、IT之家（`include_pattern`只收AI相关标题）。媒体页口播前两句须有“据+媒体名”（MEDIA_ATTRIBUTION_REQUIRED），只转述报道，不当官方确认。
- 传闻（`rumor_sources.json`，`rumor_sources.py`，config.rumors）：X账号btibor91、testingcatalog（A），legit_api、chetaslua、apples_jimmy（B），kimmonismus（C），2026-11-09经agent-reach profile核验存在；分级是编辑默认值，按日后准确率调整。另按12个模型家族轮换OR搜索（每轮≤8次、间隔10秒），搜索所得C级帖须≥20赞；Reddit r/singularity为C级。全部只读，48h窗口，过滤词见`content_filter.json`。RATE_LIMITED/PLATFORM_BLOCKED/NEED_LOGIN时整轮停止并冷却（`data/rumor-collection-state.json`），不换账号或后端。原帖与时间证据分别存`data/rumors/`与`data/time-evidence/`。
- GitHub今日热门（`github_trending.py`，config.github_trending）：每次collect读github.com/trending，`judge`只留AI或开发者工具，跳过人肉/开盒/盗号/外挂/破解/deepfake/成人等用途（如sherlock类账号搜索），保留≤3个，记录仓库卡片到`assets/github/`（不入Git）。快照时间即发布时间。
- 玩家热议（`community_sources.py`＋`community_reader.mjs`，config.community）：独立阅读profile `../../.community-reader-private/chrome-profile`，与上传profile分开（代码拒绝复用）。由用户本人`python -B community_sources.py login`用小号登录一次，程序不代登。只读渲染后的页面：近48h按播放最多5个＋最新3个视频（最新的需≥200播放、≥10评论），每视频读最热、最新评论及弹幕，页面间隔3–5秒；不导出Cookie、不直接调用评论/搜索API、不逆向WBI、不重放请求、不读用户名。快照存`data/community/`。

### 门槛

- 传闻：evidence_type三选一（tierA_source／two_independent／artifact），credibility（较可信/待观察/存疑；两条C级不能较可信），unknowns，official_status（未回应/已否认/已部分确认），rumor_safety_checked。口播首句点名来源＋转述词，末句官方状态，未部分确认时不得出现确认/证实/实锤/官宣等定论词（否定句如“尚未确认”允许）。标题带曝/传/疑似；传闻做头条时封面也要带。`data/rumor-ledger.jsonl`7天内同一传闻需新来源；官方证实或否认后用resolves_rumor回扣。
- GitHub：scene_type=github_trending，repo与stars_today须与采集一致，口播90–280字含仓库短名和“GitHub”，7天内同仓库不重复（`data/github-trending/featured.jsonl`），固定在AI早报最后，不能当头条（LEAD_SEGMENT）。
- 活动（2026-11-10起一页一个）：scene_type=activity，`freshness_basis:"active_window"`，activity_items恰好1项（ACTIVITY_ONE_PER_PAGE；旧activity_overview仅供已导入期次复核，新导入拒绝）；window_quote须含起止日期，公告≤30天，活动窗口与[本期, 本期+7天]重叠。kind=online/offline/collab，offline须location、collab须partner且见于官方原文；scale=main/minor。facts 1–2条、detail≤54字（ACTIVITY_FACTS）；口播须念出截止（或开启）日期（ACTIVITY_DEADLINE_NOT_SPOKEN）。导入时`activities.arrange`自动排序：main在前、minor在后，各自按即将结束→进行中→即将开始；每期≤active_window.max_pages（6）页，同一活动不重复、不与新闻页重复。倒计时由freshness绑定时写入scene.activity（release/upload复核不重算）。活动页不进used-news去重与记录，改记`data/activity-ledger.json`，供`activities.py list`在后续期次继续报到结束。
- 玩家热议：scene_type=community_pulse，每期≤3页。讨论对象须是`game_glossary.json`本游戏`reviewed:true`的词且类型一致（两游戏共用的词要求视频标题含本游戏名）；所引视频须在快照中且标题属于本游戏；去重后样本≥30、提及≥5；sample_count与口播数字一致；口播须标明“玩家…认为/觉得”等；引语≤3条、每条≤20字且原样出现在样本中；过滤粗口、血腥、辱骂、群体攻击、引战、剧透。未审核词用`glossary-candidates`列出交用户确认。

### 排序、标题与简介

- import在新鲜度审计后、排序前自动分栏（assign_segments）并加角标：传闻·未经官方证实、媒体报道、GitHub 今日热门、进行中活动、玩家热议。头条仍放最前，其余AI：传闻→媒体→官方→GitHub；游戏：官方→活动→热议。
- 标题可加`title_hook`（≤16字）与`title_hook_evidence`（须同时出现在hook和所选正文）；标题封面禁用震惊/炸裂/惊呆/速看/必看/绝了/吊打/跪了。
- publication.json未写description时，release自动生成章节时间点、来源链接和免责声明（传闻、玩家热议）；超过2000字或为空时报DESCRIPTION_REQUIRED。

## 2026-11-10 活动页与活动台账

用户要求：说明最近有哪些活动在进行、每个多久截止，每个活动一页，含线上、线下和联动；热度低的网页小活动放后面。实现在`activities.py`：

- `python -B activities.py list --series <game> [--at ISO]`：台账中仍在进行（或7天内开始）的活动。
- `python -B activities.py scan --series <game>`：在`data/game-items`近30天官方条目的标题/摘要/正文里找“起–止”日期窗口，给出kind/scale猜测。仅为线索，不能代替读原文。
- 来源缺口：目前没有专门的线下活动/联动来源（官方B站、微博、线下展会页未接入），线下和联动只能来自已接入的森空岛官方帖、官网公告和官方X；没采到就不报，不凑数。

## 2026-11-11 资讯量、候选排序与X连接（用户要求“全部修复”，当前有效）

起因：2026-11-11 AI早报候选 339 条只审了 17 条、成片 7 条；同期同行 8.5 分钟讲 18 条，并以 Claude 额度重置开场（该消息在我们的候选里未被看到）。06:00 的 X 采集连续多日因专用浏览器冷启动超时而整轮放弃。

- **X 连接**（`x_reach.py`，`leader_sources.py`、`rumor_sources.py` 共用）：参数在 `config.json` 的 `x_collection`。首次读取 150 秒，其后 60 秒；临时错误（TIMEOUT/UPSTREAM_BROKEN/BUSY）按阅读器给出的 `retry_after_seconds` 暂停（上限 180 秒）后重试 1 次，仍失败则跳过并在本轮末尾补读一次；连续 3 个账号失败判 X_UNREACHABLE 并冷却 2 分钟。NEED_LOGIN/PLATFORM_BLOCKED/RATE_LIMITED/NEED_SETUP 立即停止，不重试、不换账号或后端。“Could not resolve @x” 记为 NOT_FOUND（账号改名或不存在），不再触发全局暂停。被杀进程留下的锁（PID 已不存在）自动清除。每轮结果追加到 `data/x-health.jsonl`；`x_reach.py probe` 预热并实测，`x_reach.py doctor` 汇总各账号近期结果；`leader_sources.py --retry-failed` 只补读上一轮 `pending_handles`。传闻搜索失败只跳过该搜索。
- **候选排序与审阅覆盖**（`candidate_rank.py`）：AI 候选按信号加分——额度重置/限额 30、封号/政策 30、新发布 25、价格/免费 22、大厂模型 15、预览/泄露 12、公司大事 10，周边/招聘/教程 −25，来源层级与 12/24 小时内新鲜度另加分。标题里的模型版本（如“Claude Fable 5.2”与“Fable 5.2”视为同一）和专有名词相同、或标题词重合度 ≥0.5 的归为同一事件；平台名与人名（Claude Code、ChatGPT、Sam Altman 等）不作为归组依据。组得分 = 组内最高分 + 每多一个来源 8 分（上限 32）。`editorial.review_coverage.top_n`（40）组在导入时每组须有选用或落选理由，否则 REVIEW_COVERAGE；selection-report 中同组其余候选记为 `same_event_as:<id>`。分数只决定审阅顺序，不替代 48h 门禁和来源规则。
- **快讯页**（`briefs.py`，`scene_type:"briefs"`）：一页 2–3 条，每条须为已采集、48h 内、未播过的候选，source_url 与采集记录一致；传闻、lead_only、GitHub、玩家热议、需上下文的 X 帖不能进入。标题 ≤22 字、说明 ≤40 字，`spoken_key` 须在标题中并按画面顺序在口播中念到；媒体条目口播须“据+媒体名”，负责人 X 须点名本人。facts 由各条自动生成并附出处，底部出处条列出全部来源；每条均记入已用新闻。栏目顺序：传闻 → 媒体 → 官方 → 快讯 → GitHub；快讯不能当头条，也不能进 title_groups（TITLE_BRIEFS_PAGE）。自动简介的时间轴列出快讯各条标题，来源链接列出每条（总长保持在 2000 字内）。
- **新增来源**：媒体 404 Media（只收 AI 相关）、Ars Technica AI；官方 ElevenLabs 博客 RSS；X 账号 ElevenLabs（官方）、OfficialLoganK（谷歌）、elonmusk（xAI，只采信他本人关于 xAI/Grok 的第一手说法）。身份均于 2026-11-11 实测核对；@xai（2026 年新建、0 关注者）疑似仿冒未收录，@elevenlabsio 不存在。
- **停用**：MiniMax 官网与 Kimi 论坛在本机 TLS 握手失败（直连与代理均为 UNEXPECTED_EOF），已 `enabled:false` 并写明原因；由 X @MiniMax_AI、@Kimi_Moonshot、IT之家与 kimi-blog 覆盖。

## 2026-11-15 活动日历（用户要求，当前有效）

问题：游戏情报只报单独做成页的活动；版本日历里的阶段节点（方舟SS「时间啊，向前！」第三段11/15 16:00、终末地「百趣演武」11/11内容更新、「密境行者」11/19后续开放）和几天后结束的活动都没被提醒。原因：采集只存约100字摘要，起止时间写在公告正文里；旧`data/activity-ledger.json`只记录做过页的活动。

实现（`activities.py`，取代上节的台账与`scan`）：
- `python -B activities.py sync --series <game>`：读近60天该游戏官方公告全文（官网页面首次读取时归档到`data/articles/`；arknights.global这类脚本渲染页归档为空壳时改用采集到的全文；森空岛、官方X用采集正文），解析每个活动的起止（日期/“「X」版本更新后”/“版本更新维护前”）、阶段（<第N段>、第N阶段/期、Phase N、内容更新、开放后续）和官方原句，写入`data/activity-calendar.json`（schema 2：versions、activities、synced_at）。每次sync按原文重建；同名活动官网优先、森空岛只补阶段；礼包类（category=pack）不进日历；编者`fix`/`hide`的条目保留。旧台账在首次读取时并入（origin=reported_page）。
- `list`：仍在进行或3天内开启的活动，含还剩N天、“版本更新前结束”（版本结束时间未公布时）、“长期开放”（无结束时间、但有后续开放节点）以及昨天/今天/3天内的阶段。`fix`（须带官方原句）、`hide`、`version`（版本结束时间，原句须见于该item官方正文）。
- 页面：`scene_type:"activity_calendar"`，不引用单一item；`freshness.audit_episode`经`bind_calendar`绑定：日历须12小时内sync过（ACTIVITY_CALENDAR_STALE），3天内结束/开启或今明两天开下一阶段的活动必须在`spoken`里映射并在口播中同句说出时间（ACTIVITY_CALENDAR_SPOKEN / ACTIVITY_CALENDAR_DAY）。最多12行（rows_per_page），必须点名的排在前面，其余由`publication_policy`写进简介“活动日历”段；简介来源列出该页用到的所有公告链接。
- 门禁：明日方舟情报/终末地情报（edition_series=arknights/endfield）正片，只要该游戏有进行中活动，缺这一页导入即拒绝（ACTIVITY_CALENDAR_REQUIRED）。该页不能当标题故事（TITLE_CALENDAR_PAGE），排在活动段最后（单活动页、补页之后）。
- 维护（用户要求：由制作agent每期维护，增添进行中的活动、删除过期的活动）：`sync`结束时删除本游戏已结束的条目（含编者补录、隐藏条目），报告`expired`；`added`/`updated`按同步前的文件对比。跟版本走的活动（end_rule=version_end）未写入版本结束时间时，以下一个版本的“更新维护时间”开始为结束（end_basis=next_version_start）；无结束时间的条目在最后一个阶段开启一天后删除；版本结束未知的保留。`add`补录解析漏掉的活动：须是已采集的本游戏官方item，官方原句逐字见于其正文（ACTIVITY_QUOTE），结束方式三选一（`--end-at`/`--version`/`--open`），已结束拒绝（ACTIVITY_ENDED），已存在用fix（ACTIVITY_EXISTS）；条目origin=editor_added、fixed_by_editor=true，之后sync保留至到期。`prune`单独删除过期项。
- 补页（用户要求：当期新消息少于五条时，用日历最要紧的几条单独成页凑够五条，之后再一页活动日历包含所有活动；玩家热议不计）：消息页=除00导览、活动日历页、玩家热议（segment=community）和补页外的正文页，快讯页算1页、普通单活动页算1页。少于`min_body_pages`（5）时，按`list`顺序取**有截止时间**（固定日期或下个版本开始）且未单独成页、未在同公告新闻页口播中点名的活动，补到5页。补页写`scene_type:"activity"`＋`calendar_key`，导入（`fill_from_calendar`，在freshness审核前）从日历填入activity_items、item_id、source_url、来源类型与freshness_basis=active_window；新鲜度由`calendar_check`判定（仍在进行、官方原句忽略空白后见于正文），不受单活动页30天公告期限制；倒计时、1–2条facts与口播说出截止日期沿用单活动页规则。补页集合与顺序必须正好等于计划（ACTIVITY_FILL，错误信息给出正确key与顺序），消息页已满5页时不得加补页；导入自动把补页排在活动日历页之前。补页不记为已用新闻，只在日历条目`reported`里记一笔。`python -B activities.py fill --series <game> --pages N`预览。
- 配置：`config.json` → `activity_calendar`（regions：方舟cn+global、终末地cn；max_source_age_days 60；max_sync_age_hours 12；rows_per_page 12；upcoming_days 3；min_body_pages 5）。
- 2026-11-15补全：终末地「丹青渡」期间15项、明日方舟国服/国际服23项已同步并人工校正名称、去重（误拆的森空岛子项、卡池重复、说明句、资源预载、X帖首句均已hide）。「丹青渡」版本结束时间国服官方未公布，暂显示“版本更新前结束”。
