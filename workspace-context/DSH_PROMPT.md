# DeepSeek Harness 接手指令（2026-11-09 版，替代 2026-11-07 版）

> **2026-11-09 内容改版（用户确认）**：AI早报加入“传闻”“媒体报道”“GitHub 今日热门”三个栏目，两条游戏情报加入“活动一览”和“玩家热议”（B站评论归纳）。**覆盖旧规则“传闻不报”**：传闻可以报，但只能按第 3a 节的门槛和措辞报。量子位改为普通媒体源，不再是线索源。规则细节见第 3a 节与 `News_Video/docs/FRESHNESS_AND_SOURCES.md` 的“2026-11-09 内容改版”节。

用户已决定：早报、晚报从 2026-11-05 晚报起交回 DSH 制作，并按既有授权自动投稿。Claude Code 已停止制作，它的桌面定时任务 news-morning/news-night 已停用。全程用中文汇报。

**2026-11-07 起拆成三个系列（用户确认，覆盖下文及旧文档里“一期混合 AI＋游戏”的写法）**：

| 系列 `edition_series` | 时段 | 期次 ID | 编辑目录 | release 目录 | 内容 | 投稿分区 | 活动 | 固定标签 |
|---|---|---|---|---|---|---|---|---|
| `ai`「AI早报」 | morning 06:00 | `daily-YYYYMMDD-morning` | `data/morning-YYYYMMDD/` | `release/YYYY_MM_DD_morning` | 只做 AI（含 tibo/负责人、临时新闻回顾） | 科技数码 | 可参加的免费活动里热度最高的（`most_popular_free`，不限题材，没有就不挂） | AI |
| `arknights`「明日方舟情报」 | night 18:00 | `daily-YYYYMMDD-night-arknights` | `data/night-arknights-YYYYMMDD/` | `release/YYYY_MM_DD_night_arknights` | 只做明日方舟（国服＋英文国际服） | 游戏 | 8314 明日方舟创作者应援计划（精确） | 明日方舟 |
| `endfield`「终末地情报」 | night 18:00 | `daily-YYYYMMDD-night-endfield` | `data/night-endfield-YYYYMMDD/` | `release/YYYY_MM_DD_night_endfield` | 只做明日方舟：终末地 | 游戏 | 1325166 明日方舟终末地创作者应援计划（精确） | 明日方舟终末地、终末地 |

- 晚上的两条各自独立制作、配音、release、投稿，先做完一条再做另一条（配音锁只允许一个）。
- 某个系列 48h 内没有合格新消息，本期就不出这一条，在汇报里说明，不凑数、不拿另一系列的内容补。
- 活动、分区、固定标签由上传器按 `edition_series` 自动选择，不要手动改；分区名“游戏”若与平台界面不一致，上传器会在提交前以 PARTITION_MISMATCH 停下，此时停止并汇报，不换分区重试。
- 代码会拦截：系列和时段不符（SERIES_SLOT_MISMATCH）、ID 不符（SERIES_ID_MISMATCH）、混入别的系列的新闻（SERIES_SCENE_MISMATCH）、缺 hook（HOOK_REQUIRED）。按报错修 editorial，不要绕过。
- 2026-11-05 版之前的已发布期次（混合版 morning/night）保持原样，不重做、不重传。

## 0. 接手核对（第一次执行时做一次）
- 工作区 `D:/Basement/Codex_Video`，代码 `Codex-report-news/News_Video`（以下命令都在这里执行，Python 用 `python -B`）。release/、Voice_Generate/、media-library/、私有上传 home 在工作区根。
- 读工作区根 `AGENTS.md`（顶部带日期的通知优先于下文旧规则）→ `News_Video/docs/CURRENT_RUNBOOK.md` → `skills/news-video-production/SKILL.md` → `docs/FRESHNESS_AND_SOURCES.md` 的“2026-11-02内容增强”节。其余文档（PRODUCTION_RULES、GAMES_FIRST、SCENE_IMAGES、MULTIPLANE、CODEX_UPLOAD、RESET_ALERTS、MODEL_ALERTS）按需查。STATE.md、V_0、旧提示词只作历史参考。
- 交接时的状态：2026-11-02 早报至 2026-11-05 早报都已由 Claude 制作并提交（最后一期 BV1PRxd6PEKN，平台审核中），回执都在 `release/2026_11_0X_{morning|night}/upload.receipt.json`。下一期是 2026-11-05 晚报。
- 只能有一套执行器：DSH 定时任务启用前，确认 Claude 的 news-morning/news-night 仍为停用。每小时 tibo/reset 巡检已被用户关闭，保持暂停，不自行恢复。
- 不在生产目录执行 git restore/reset/clean 或镜像覆盖；保留已有未提交改动。

## 1. 调度与防重（每次执行）
1. 用北京时间（UTC+8）判定期次：05:30–17:29 为 morning，17:30–次日05:29 为 night（凌晨属前一天晚报）。本机系统时区是 Mountain Time（当前 UTC-7），不要用本机本地时间判断。早报北京 06:00 开始，晚报 18:00 开始；午报已取消。
2. morning 只做 `ai` 一条；night 依次做 `arknights` 和 `endfield` 两条。ID、编辑目录、release 目录见上方表格。
3. 对本时段的每条 ID 都先运行 `python -B production_flow.py status <ID>` 和 `python -B upload_bridge.py pending`。已 complete/published 的期次只汇报不重做；submitted/reviewing/unknown 只运行 `python -B upload_bridge.py recover <release目录>` 回查，绝不重新上传。已有在制期次按当前阶段续接，已固定的 render-plan 不改模板。

## 2. 采集
- `python -B news_video.py collect --kind all`。看报告里每个来源的 ok 和条数：失败或 48h 内 0 条的来源写进 source_gaps，并在汇报里点名。skland 显示 CAPTURE_REQUIRED 属正常，下一步补。
- 2026-11-02 起新增来源：xAI、Mistral、Gemini 博客、GitHub Copilot changelog、Cursor changelog、NVIDIA 博客；X 官方号 MistralAI、AIatMeta、GeminiApp、cursor_ai；ArknightsEN/AKEndfield 每次读 20 条。fetch 已处理 gzip（DeepMind RSS），Anthropic/MiniMax 文章日期会从正文补抓并缓存在 data/article-dates.json。
- **森空岛（国服两款游戏的主力来源）**：
  - 用一个隔离、未登录的浏览器依次打开 `https://www.skland.com/game/arknights?cateId=1` 和 `https://www.skland.com/game/endfield?cateId=12`。可以用项目本地 `.cache/playwright` 的 Chromium 配一个全新的临时 profile。
  - 等页面渲染约 3 秒，向下滚动几次加载更多帖子。然后在页面里执行 `News_Video/skland_capture.js` 全文，把返回的 JSON 原样存为 `data/skland-captures/<skland-arknights|skland-endfield>-<UTC时间>.json`。
  - 再运行 `python -B skland_sources.py import <两个文件>`。可能入选的帖子如果正文为空或被截断，打开它的文章页（`/article?id=N`）再执行同一脚本并导入。
  - **只有长图、没有文字的官方帖**（如「卫戍协议：规程」玩法介绍）不要直接放弃：运行 `python -B skland_sources.py ocr <item_id或森空岛文章数字id>`，用本机 Windows 中文 OCR 把官方长图读成正文（记录 text_source=image_ocr，图存在 assets/game-news/）。OCR 会认错数字、日期和名字：写进口播和 facts 的每一项都要打开对应图片核对，对不上就不用；配图用该帖 related_images。OCR 报“too little readable text”就记为缺口。
  - 用户的限制：不登录，不读取或提取 Cookie，不逆向签名，不重放或伪造 API 请求，不用用户的 Chrome、BrowserSkill 或任何已登录的 profile。没有符合条件的浏览器就记 skland 缺口，继续用官网/RSS/X。
  - 导入有 3 小时新鲜度检查，超时要重新采集。
- 采集每个时段都跑一次 `collect --kind all`（AI 和游戏都采，供去重与回顾使用）。
- 2026-11-07 新增：X 官方号 XiaomiMiMo、StepFun_ai、Baidu_Inc（百度是公司号，只选 AI 模型与产品）。
- 2026-11-09 新增（都由 `collect --kind all` 自动采集，失败只记缺口、不中断）：
  - **媒体源**：量子位 `qbitai-leads`（不再是 lead_only）、TechCrunch AI、The Verge AI、IT之家（只收 AI 相关标题）。候选里带 `media:true, segment:"media"`。
  - **传闻**：X 爆料账号 btibor91、testingcatalog（A 级），legit_api、chetaslua、apples_jimmy（B 级），kimmonismus（C 级），以及按 12 个模型家族轮换的关键词搜索（每次最多 8 次搜索、间隔 10 秒；搜索来的 C 级帖要 ≥20 赞）；Reddit r/singularity（C 级）。原帖存 `data/rumors/<ID>.json`，候选里带 `rumor:true, rumor_tier, likes`。遇到 RATE_LIMITED/PLATFORM_BLOCKED/NEED_LOGIN 会自动停掉本轮并冷却，不要换账号或后端重试。
  - **GitHub 今日热门**：读 github.com/trending，自动跳过与 AI/开发工具无关或用途有害（人肉、开盒、盗号、外挂、破解、deepfake 等）的仓库，保留至多 3 个候选，item 存 `data/github-trending/items/<ID>.json`。
- **玩家热议（仅两条游戏情报，各自采集）**：`python -B community_sources.py collect --series <arknights|endfield>`。
  - 用独立的阅读 profile（`../../.community-reader-private/chrome-profile`，与上传器 profile 分开）只读 B站页面：近 48h 播放最多的 5 个视频＋最新的 3 个（有播放/评论下限），每个读最热和最新评论，另读弹幕。不导出 Cookie、不直接调评论或搜索 API、不逆向 WBI、不重放请求，不读用户名。
  - 首次使用或报 COMMUNITY_LOGIN_REQUIRED：停下这一栏目，请用户本人运行 `python -B community_sources.py login` 用小号登录一次（程序不代登），本期照常出片、不做玩家热议。报 PLATFORM_BLOCKED 同样跳过并汇报，不重试。
  - 采集后运行 `python -B community_sources.py topics <快照ID>` 看各讨论对象的提及数；对象必须是 `game_glossary.json` 里本游戏 `reviewed:true` 的词。`python -B community_sources.py glossary-candidates` 列出常被提到但没收录的词，只汇报给用户，不要自己把 reviewed 改成 true。
- 然后按系列列候选：`python -B news_video.py candidates --hours 48 --compact --limit 12 --cursor 0 --series <ai|arknights|endfield>`，按 next_cursor 翻完所有页。逐条用 `python -B news_video.py article <ID> --compact` 读原文，truncated=true 时读完整归档。
- X 帖：原文和真实链接在 `data/leader-posts/<ID>.json`，source_url 必须与采集记录完全一致，不要自己拼。summary 里已附引用帖正文（[引用 @…]）。是线程或明显有后续时运行 `python -B leader_sources.py thread <ID>`。帖子只有标题加链接时读链接里的官方原文；openai.com 对脚本返回 403 时，用浏览器读原文并把原句写进 evidence。
- 运行 `python -B news_video.py game-schedule --days 14`，找当天生效的旧公告（见第 3 节生效时间规则）。

## 3. 选题规则
- 每条视频只讲本系列：ai 只选 kind=ai；arknights 只选明日方舟（国服、英文国际服）；endfield 只选终末地。游戏按这些逐项检查：新版本或 SideStory、新玩法（如卫戍协议规程）、新干员与卡池、活动开启与规则、福利兑换补偿、维护闪断、联动、直播前瞻、制作组通讯、创作活动。“维护结束”“服饰上架”“音乐上架”“创作集锦”这类小消息默认不单独成条。
- 游戏新闻写清玩家要做什么：开始/截止时间、能领什么、需要准备什么、是否限时；只从官方原文推导，不评价强度，不建议抽不抽。
- **48h 门禁**：只选原始发布 48 小时内、事实完整的新消息。离边界不足约 12 小时的不选，避免制作中途过期。
- **生效时间例外**（用户确认，只适用于游戏）：公告原发布超过 48h，但开服/活动/卡池/维护的生效时间落在本期前后 24h 内时可以入选。做法：
  - 设 `freshness_basis:"effective_time"`，填 `effective_at`（带时区）和 `effective_quote`（含该日期的官方原句）；
  - 口播说明哪天发的公告、哪天生效；
  - 离窗口边界不足约 2 小时的不用。
- **活动日程页**：每期最多 1 页 `freshness_basis:"schedule"`，收录 72h 内开始或结束的活动，schedule_items 每项都引用原句；没有就不做。AI 的 48h 门禁不变。
- 不凑数。不用预告、营销、转帖截断、只有标题链接或缺上下文的内容；负责人只有一两个词的短句记为 defer。与已播事件去重，包括引用同一公告的负责人帖。
- **终末地森空岛帖**：末尾固定的“————————▼ 当前版本已开启…”是宣传语，不是该帖新闻。skland_capture.js 已裁掉这段，仍要只按帖子自身正文和配图判断；正文只剩标题的不报。
- 选配图前看一眼图片内容，确认和该页事件一致（曾出现过把下一期预告图当本期配图）。每页至少一张相关图，新闻原图优先，`image`/`image_source_url` 取自该文章的 related_images；缺图才用官方游戏/公司标识。
- **篇幅**：AI早报素材充足时 6–12 条、3–5 分钟；游戏情报 3–8 条，宁缺毋滥；不足就如实变短（成片仍须 >30 秒）。在 editorial 写 `rejections:{item_id:落选原因}`，覆盖本系列所有看过但没选的候选。import 会生成本系列的 selection-report.json，unreviewed 应接近 0。
- **头条**：按影响力选正文01——新模型/大版本/新玩法 > 价格、额度、可用性变化 > 卡池与新干员 > 福利活动 > 其他；同分时国内厂商、国服优先。正文01 = 封面头条 = lead_event_id。当天已公开的 temporary 临时新闻由导入自动作为回顾插入（仅 AI早报）。

## 3a. 新栏目（2026-11-09）
import 会按来源给每页自动分栏（`segment`）并加角标，再按栏目排序。头条（lead_event_id）仍按第 3 节影响力手选，放在最前；其余按下面顺序：
- AI早报：传闻 → 媒体报道 → 官方动态 → GitHub 今日热门（固定最后，每期最多 1 条，不能当头条）。
- 游戏情报：官方消息 → 活动一览 → 玩家热议。
栏目都是“有合格素材才做”，没有就不做，不凑数。

**传闻**（`scene_type:"rumor"`，item_id 为某条传闻帖）：
- 门槛（`evidence_type` 三选一）：`tierA_source`（引用里有 A 级账号）；`two_independent`（≥2 个不同作者，用 `rumor_sources:[其他传闻ID]` 补充）；`artifact`（代码/API 列表/页面截图等实物，填 `artifact:{kind, quote}`，quote 必须是原帖里的原文）。
- 还要填：`claim`（一句话说传的是什么）、`credibility`（较可信/待观察/存疑；两条都是 C 级时不能写较可信）、`unknowns`（还不知道的事，至少一项）、`official_status`（未回应/已否认/已部分确认）、`rumor_safety_checked:true`（确认不涉及私生活、未成年人和人身攻击）。
- 口播：第一句点名来源并用“称/爆料/透露/发现”等转述词（如“X 上爆料账号 btibor91 称……”）；最后一句写官方状态（如“目前 OpenAI 官方尚未回应。”）；除非已部分确认，不得出现“确认、证实、实锤、官宣”等定论词。
- 标题：传闻页的 title 要带“曝/传/疑似”；传闻当头条时，封面 headline_main 或 headline_top 也要带。
- 可选 `quote_card:{account, time_label, excerpt, translation}`：画面上的原帖卡片，excerpt ≤90 字且必须从原帖照抄。
- 去重：`data/rumor-ledger.jsonl` 记录已播传闻（`python -B rumor_sources.py ledger` 查看未结案的）。7 天内同一传闻没有新来源会被 RUMOR_REPEATED 拒绝。后来官方证实或否认时，在官方/媒体那页加 `resolves_rumor:{key, status:"confirmed"|"denied"}`，口播要回扣（如“此前传闻的……今天官宣了”）。

**媒体报道**（媒体源条目）：口播前两句里必须有“据＋媒体名”（如“据 TechCrunch 报道”），只转述报道内容，不当作官方确认。

**GitHub 今日热门**（`scene_type:"github_trending"`）：填 `repo`（owner/name）、`stars_today`（与采集一致）；口播 90–280 字，含仓库短名和“GitHub”，讲清它是做什么的、谁做的、今天涨了多少星。配图自动用仓库卡片。同一仓库 7 天内不重复。

**活动一览**（`scene_type:"activity_overview"`，`freshness_basis:"active_window"`）：一页列 1–3 个正在进行或 7 天内开始的官方活动，`activity_items` 每项填 `item_id、name、start_at、end_at（带时区）、window_quote（含起止日期的官方原句）、source_type`。公告发布超过 30 天的不用；顺序必须是即将结束 → 进行中 → 即将开始。

**玩家热议**（`scene_type:"community_pulse"`，每期最多 3 页）：
- 填 `item_id`（快照ID）、`game`、`subject:{game, entity_type, entity_name}`（entity_type 取 glossary 的 character/event/mode/banner/item/place）、`videos:[bvid]`（来自快照且标题属于本游戏）、`sample_count`（所引视频去重后的评论＋弹幕总条数，须 ≥30 且其中提到该对象的 ≥5 条；填错时报错信息会给出正确数字，口播里用阿拉伯数字原样写出）、可选 `quotes`（≤3 条、每条 ≤20 字，从样本原样照抄）。
- 口播必须说明是玩家看法（“玩家……认为/觉得/吐槽/期待”），并念出样本条数；不点名用户、不带 @，不放粗口、引战和剧透。

## 4. 写稿与导入
- 参照最近一期 editorial.json 的格式，在本系列的编辑目录写 editorial.json，producer 填 `"DeepSeek Harness"`。顶层必须有：
  - `"id"`（见表格）、`"edition_date"`、`"edition_slot"`（ai 填 morning，两款游戏填 night）、`"edition_series"`（ai / arknights / endfield）；
  - `"hook"`：一句 8–45 字、以句号/叹号/问号结尾的头条句，直接说当天最重要的事，例如“卫戍协议改为赛季制常驻，每周期两个序列。”。它替代过去的“这是本视频的导览。”，作为开场口播；不能含“导览”二字，内容必须来自正文01的原文事实。
- X 来源要有 author_handle、claim_type、attribution_checked、author_spoken_aliases、context_evidence、evidence。事实只写原文有的。
- 每条都读完整官方原文。口播 150–250 字，facts 3–4 条；补原文里的背景、时间、适用范围和影响对象，不加原文没有的评价。文风按项目 help-me-speech 的 news 模式，X 消息写明主体和北京时间原分钟。三个系列的 00 页开场口播都由 hook 生成，不再播“这是本视频的导览。”；系列内只有一个栏目，正文不再加“先来看/接下来是”的栏目过渡。
- 运行 `python -B news_video.py import-editorial <editorial路径>`。
- 在期次目录写两个文件：
  - publication.json：title_groups 只能有一组，kind 为本系列的类别（ai 填 `ai`，两款游戏填 `games`），event_ids 放 1–2 条（第一条是头条），lead_event_id 一致，auto_publish 为 true。生成的标题形如“头条事件标题、次要事件标题｜明日方舟情报 11.7”（直接取正文页 title），不带“AI：/游戏：”前缀，超过 60 字会报 TITLE_TOO_LONG，请把正文标题写短。tags 只填本期事实相关的词，系列固定标签由代码自动放在最前面。标签不要带感叹号等符号，平台会以 TAG_REJECTED 拒收。
    - 2026-11-09：可加 `title_hook`（≤16 字，放在标题最前）和 `title_hook_evidence:[短语]`。每个短语必须同时出现在 hook 和所选正文里，否则报 TITLE_HOOK_UNSUPPORTED。标题和封面不得使用“震惊、炸裂、惊呆、速看、必看、绝了、吊打、跪了”（PUBLIC_WORD_BANNED）。
    - 简介：publication.json 写了 `description` 就用它；没写时 release 会自动生成（章节时间点、来源链接，有传闻或玩家热议时附免责声明）。
  - cover.json：headline_top、headline_main、highlight 必须是头条标题、口播或 facts 里原样出现的文字，并且要短。
- 再运行 `python -B publication_policy.py title episodes/<ID> --write`。所有 JSON 用无 BOM 的 UTF-8。

## 5. 配音（本地 Qwen3-TTS，不改 Voice_Generate）
- 运行 `python -B news_video.py voice <ID>`。若提示 data/voice.lock 已存在：读锁内的 PID，确认该进程已不存在才删锁，否则等待。
- **按段缓存**（voice_units.py，缓存在 `.cache/voice-units/`）：
  - 同一文字输出完全相同，原样重跑没有用。
  - 出错时只改出错那一段的措辞再跑 voice：没改的段直接复用，只重做对齐，几十秒完成。不要为了一句话改动其他段落，更不要整期重配。
  - 报“Voice unit hit the generation cap”时，错误信息会点名是哪一段。
- **口播避坑**：
  - 书名号或引号内不放句末标点。例如写成「时间啊，向前」，不写「时间啊，向前！」，否则断句会切出碎句，导致对齐失败。官方全名留在 facts。
  - 口播汉字必须都在 `Voice_Generate/models/fa-zh/tokens.json` 里（只读）。生僻字（如罗比菈塔的“菈”）会导致 Group alignment token mismatch，口播换个说法，名字留在 facts。
  - 少念英文：英文产品名、地图名、活动名放在 facts，口播用中文描述；OpenAI、Anthropic、谷歌 DeepMind 这类公司名可以念。必须念的英文不放在句末。连串英文容易让某组卡在约 81.8 秒的生成上限，出现静音或漏念。
- **失败排查**：
  - 先看 `episodes/<ID>/narration.align-group-*.wav` 各组时长与字数之比（正常约每秒 3–5 字）。某组异常偏长，就对该段做不改事实的措辞微调。
  - 报 "No reliable quiet sentence boundary" 时调整句末英文词的语序。
  - ASR 不通过（audio-content-review.json 的 ok 为 false）时，看各句的 problems、expected 与 heard，定位漏念、跑偏或重复的句子再改写。
- 改 editorial 后要依次重新 import、title --write、再配音。通过标准：audio-content-review.json 的 ok 为 true。读音规则（干员读 gàn yuán、祀、都尉等）已写在 config 的 pronunciations 里。

## 6. 封面、渲染、检查
- 运行 `python -B cover_generator.py <ID>`（默认 P3 蓝白 persona 版，16:9 与 4:3 两张），看图确认文字不压配图框、日期只出现一次。
- 运行 `python -B render_sample.py <ID> --no-upload`（默认 multiplane/persona 模板）。
  - 布局审计失败时按报错修版式，不得放宽审计。
  - 渲染已有停滞保护：连续 300 秒无进度会结束整个进程树并自动重渲 1 次，记录在 episodes/<ID>/render-stalls.json。重试仍失败就停下报告。
  - 已完成的渲染会锁定输入；改内容后报 “Completed render inputs/output changed” 时，新建修订期次 `<ID>-v2`，release 会进 revisions/。
- 从 episodes/<ID>/sample.mp4 用 ffmpeg 抽几帧，实际看画面、字幕、导航和图片是否对应。确认后运行 `python -B publication_policy.py seal episodes/<ID>`。
- 成片实际时长必须大于 30.0 秒（ffprobe），不靠空白、重复或降速凑时长。

## 7. 投稿
- 运行 `python -B render_sample.py <ID> --resume-export`。它会准备 release、写已用新闻记录，并按已授权的默认设置自动投稿：
  - 合集按题材自动选择：AI早报进 AI-News，两条游戏情报进 Game-News；原创/禁止转载＋AI 生成声明。找不到合集时上传器会停下，不要自己新建合集；
  - 分区与活动按系列自动选择（见文首表格）：ai 投科技数码、挂当时热度最高的可参加活动；arknights 投游戏、精确挂 8314；endfield 投游戏、精确挂 1325166。游戏两条找不到指定活动就停止，不换别的活动。
- 读 release 目录的 release.json、upload-attempt.json 和 upload.receipt.json，核对回执中的 bvid、标题、分区、合集、声明和活动标签读回。
- 然后运行一次 `python -B upload_bridge.py recover <release目录>`。审核中就如实记为已提交、未公开，不要重投。

## 停止条件与汇报
- 遇到登录/验证码/平台故障、素材不足、质检失败或状态未知时，停在当前阶段，保留证据，说明实际状态，不靠绕过门禁完成。
- 例外：传闻、GitHub、玩家热议这些补充栏目的采集失败（含 COMMUNITY_LOGIN_REQUIRED、PLATFORM_BLOCKED、冷却中）只让该栏目本期不做，正片照常制作，汇报里写明原因。
- 已发布的视频、封面和投稿记录不重做、不修改、不重传。
- Cookie、浏览器 profile、API key、模型权重、原曲和字体不进 Git 或交接包。
- 汇报时区分已修改、已测试、已提交、已推送、已投稿和已公开发布。
- 每期最后汇报：
  - 期次（北京时间）；
  - 各来源条数与失败来源；
  - 候选数、入选数和时长；
  - 选题列表；
  - 关键问题与处理；
  - 验证结果；
  - 投稿回执与公开状态。
