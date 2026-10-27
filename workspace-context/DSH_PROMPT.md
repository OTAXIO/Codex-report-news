> 当前有效规则：`Codex-report-news/News_Video/docs/PRODUCTION_RULES.md`（2026-10-27）。每小时tibo+官方X，核实新模型也发临时新闻；三期主片仍有重要回顾。概览/封面/语音以该文及Voice_Generate/docs/SPEECH_POLICY.md为准。下文冲突条目为历史。

# 可直接发给 DeepSeek Harness

请接手已有新闻视频项目。先不要生成或上传样例，依次读取工作目录中的 AGENTS.md、PROJECT_PROMPT.md、Codex-report-news/News_Video/docs/WORKFLOW.md、REQUIREMENTS.md、DEPENDENCIES.md、STATE.md 和 BILIBILI_UPLOAD_RESEARCH.md，再读 Codex-report-news/News_Video/skills/news-video-production/SKILL.md 以及其中的 help-me-speech。

目标是沿用用户今天确认的新闻视频格式：白底黑字、亮蓝点缀、中央清爽、边缘花纹、大公司 logo；事实与要点解释为主；清晰自然的本地用户配音、Open AI 连读、千问中文而 DeepSeek 英文；单行内嵌字幕按语义切换；AI 与国内外重点新闻双模块和逐条导航。导览只说“这是本视频的导览。”，静音 2 秒进入正文。AI 结束后说“接下来是国内外重点新闻，先来看……”自然接第一条国内消息。

AI 公司消息每期前读官方 RSS/网页，Agent Reach 只读 X 渠道的负责人白名单改为每小时读取；tibo (@thsottiaux) 在 OpenAI/GPT 官方消息之前，其他已核实负责人在对应公司之前。官网没有新消息时，负责人新鲜推文可独立入选。推文区分个人体验、观点、预告和正式公告，保留作者/时间/原链接，检查上下文并与官网同事件合并。不要沿用旧的禁用 X 限制，详见 docs/X_SOURCES.md。社会 RSS 每小时零模型采集和本地去重。制作阶段再由当前会话选题。热门 AI 主体优先、合格 AI 消息无条数上限，国内 3 条＋国际 3 条，敏感跳过、审核后 P2。严格查已用新闻日志，不重复今天的 9 条；不同来源的同一事件也要判断，不能伪称全网热度或把旧闻写成今日新发。

下一次真正制作时，producer 写 DeepSeek Harness，按用户指定日期及时段新建 episode ID。06/12/18 点分别早间/morning、午间/noon、晚间/night。先 doctor，再采集、候选、核验、help-me-speech 文稿、导入、配音、cover.json 封面、build/check/截图、render。具体命令在 WORKFLOW.md。旧日期的 make_sample_editorial、prepare_publish_20261026、upgrade_v5 等仅为历史，不是实时流水线。

视频制作并检查通过后，先进入 release/YYYY_MM_DD_slot，文件名应含日期、时段和栏目，例如 2026_10_27_morning_早间新闻.mp4。之后只从这里上传。标题封面突出本期一条具体真实新闻，有公司 logo 或真实图片，不能泛泛写“又升级了”。双封面均不能裁掉重点。

发布需求为科技数码区、News 分类/合集核对、创作声明多选 AI 生成＋自制原创，标签优先 AI/OpenAI 等相关词条，逐个输入回车，选择相关热门活动。News 已核实为既有合集，ID 在私有 profile。现使用 codex-upload 独立自动投稿，必须阅读 CODEX_UPLOAD.md；render 生成 upload.codex.json 后按配置最终提交。Chrome 已认证及只读核验、离线全字段流程已通过，新稿完整实投仍需真实平台回执；故障保留成品并报告，不扫描或导出浏览器 Cookie，不绕过第三方 skill 的最终提交守卫。

发布成功回执或用户确认之后再 finalize 清理本期残留；保留源码、模型、数据库、日志和其他期次。2026-10-26 晚间版已经发布，不要重复上传。当前 Codex 仍在负责；只有用户真正让你开始接手时，才执行新的制作/发布任务。

先向用户简要报告：你读到的当前状态、依赖探测结果和仍缺的实际配置。如果信息足够直接工作，不重复询问已经明确的颜色、语速、字幕、时段和标签规则。缺模型/运行时/凭据时说清具体缺口，不能编造执行成功。

X 路径补充：专用 Agent Reach 读取优先；允许公开镜像 Sotwe（安装时已用来发现 tibo）作为文字与来源核查备用。镜像必须核实原作者、status 链接、正文和时间；相对时间/片段只能当线索，不冒充最新完整原帖。不默认收费，不自动轮换镜像绕过登录/验证/限流。当前专用 tibo 已读通。

## tibo reset 临时新闻（最新新增）

负责人推文每小时读取。发现 tibo 新的明确额度 reset 通知时，核验后优先制作并按授权紧急发布“临时新闻”；不占北京时间 06/12/18 点三期次数。只展示该 reset 推文的作者、时间、原链接、原文及忠实中文概括；无导览、无其他新闻，保留本地语音与单行字幕。先 release，按日期＋temporary＋时分秒＋事件 ID 命名，不覆盖主片。已读历史不追发，同次重置去重，玩笑/否定/询问不触发发布。具体命令、语义核验和上传边界见 Codex-report-news/News_Video/docs/RESET_ALERTS.md（项目 docs 内同名文件）。当前使用 codex-upload 自动提交；真实新稿完整平台链路尚未实测，失败保留 release 并报告真实阻塞，不谎报已发布。


## 来源时间与负责人 X 画面（2026-10-27 最新要求）

- 所有新闻画面的“数据来源/来源”区展示信息原始发布时间，尽可能具体到分钟；有可靠时区的时间统一为北京时间，格式 YYYY.MM.DD HH:mm 北京时间。不能把采集时间、视频制作时间或转载时间冒充原发布时间。来源只有日期则只标日期，缺分钟/时区如实说明，不补造 00:00；编辑数据用 published_precision=date 标记仅日期来源，并保留原始时间证据。
- 视频可以展示 tibo 及其他已核实负责人发布的 X 消息，包括额度 reset 消息。每位负责人在同一期视频中合计最多占 2 页画面，跨不同话题也累计；这里是 2 页视频画面，不是最多 2 条推文。临时新闻按其独立期次计算。
- 同一人的多条相关推文可合并到 1–2 页，由当前 AI 提炼“他表达了什么、意味着什么”；区分原文事实、个人观点、预告和 AI 的解释，不添造公告、重置范围或到账承诺。英文原文与中文概括明确区分，需要时标“要点概括”。
- 2 页仍容纳不下时，精选最重要且相关的信息、压缩总结或舍弃次要消息；不增加第 3 页，不缩小字号硬塞，不限制为 2 条推文，不删除关键上下文导致误解。
- 可附原始 X 推文截图或负责人头像，保留作者/账号/发布时间等必要归属，记录图片出处。截图只裁取相关推文，排除广告、无关推荐和不适宜画面；头像不冒充公司 logo。截图不能替代清晰正文、概括和单行字幕，避免用过长原文堆满两页。
- reset 紧急规则保留：明确、新鲜的 tibo 额度重置声明先核验、去重再制作临时新闻，只展示该重置相关消息及忠实解释，不混入其他话题、不占早午晚三期、不追发旧重置。主片选题仍查已用记录，避免再播同一临时消息。
- 检查时逐页核对时间精度与时区、每人总页数、总结是否忠实、配图归属、文字溢出。需要多页时在编辑 JSON 中标 author_handle、person_page_index（1/2）、person_page_count（≤2），同人的全部页统一计数，不以拆分 scene 或话题规避上限。


## 2026-10-27 Qwen3-TTS 与后台窗口更新

用户已选择 Qwen3-TTS。新闻默认后端现为 config.voice.backend=qwen3，0.6B Base + 现有“帝江号，我已就位，该出发了”参考音频；GPT-SoVITS 原权重、profile 和运行时保留，改 backend=gpt-sovits 可回退。Qwen 接口通过独立 Python 环境和 tools/qwen_generate_job.py，使用逐句映射以保留字幕/导览停顿；Qwen 的 cleanup 强制 off，不做尾字压缩/淡出或机械拉伸语速。旧 GPT-SoVITS speed/cleanup 等参数不是 Qwen 的已实现控制参数，不能混淆。

官方约 2.5GB 权重已下载并逐文件校验 SHA-256；本地克隆样音成功（8.4 秒），新闻入口真实隔离烟测通过逐句输出、2 秒导览停顿和时间映射，无视频生成/上传。安装版本冲突已解决，pip check 通过。自然度与音色仍待用户试听，不能宣称优于旧模型或已完成 Qwen 微调。新方法和训练路线见 VOICE_UPGRADE.md。28 条训练＋4 条验证已导出，尚未训练。

截图命令框属于 Agent Reach 专用 Python 辅助进程。项目采集器现使用 Windows 隐藏启动并仅隐藏标题完全匹配用户 .agent-reach/tools 下 Python 的辅助控制台，不关闭进程，不隐藏 X 登录/验证页面，不影响其他终端。改后真实 tibo 读取成功、reset 无新队列。


## 2026-10-27 最新模型取舍（覆盖 1.7B 试验意向）

用户确认 Qwen3-TTS 更好，若 1.7B 显存不足则放弃，0.6B 已足够。当前继续使用用户认可的 0.6B Base 参考音频克隆，不在 8GB 显存设备强行启动 1.7B 全参数训练；增加轮数不能解决显存不足。1.7B 下载目录已清理，没有 1.7B 训练结果，也没有完成 Qwen 微调。未来训练 0.6B 需先做 24kHz 数据/参考归一化、音频码准备和显存试跑，按验证与试听选模型，不仅增加轮数。

旧 GPT-SoVITS 的 17 个非当前运行依赖检查点已可恢复移至根目录 .retired-models/20261027-gpt-sovits-checkpoints（约 5.30GiB），SHA-256 已验证，原始音频/标注/参考保留；归档没有释放其磁盘占用。原 GPT-SoVITS 外部运行时与历史代码暂保留，不整库删除；历史训练 profile 如引用归档文件需先恢复。更新后的 Voice_Generate/README.md 为当前语音项目入口。


tibo 发音：仅口播输入替换为 `ti bo`，按用户指定的两音节连读；不要读成 table。画面、字幕、作者名与原始来源保持 `tibo`，不可改成 ti bo。规则在 config.voice.pronunciations 中。


最新发音与听感要求（覆盖旧 ti bo 规则）：tibo 口播读 tī bo，梯一声、啵轻声（短而轻、无独立升降调），中间不停顿；TTS 输入使用“梯啵”，画面/字幕/来源仍保留 tibo。中文替换是发音引导，不是已验证的强制音素接口。语气平稳、克制，避免活泼上扬。整段统一参考音频、采样设置和逐单元种子，重新生成全部语句，不局部拼接不同听感的句子。低采样温度用于减小变化，不能等同于模型原生情绪控制；最终听感仍需试听。


时间口播规范：13点48分 / 13:48 读“十三点四十八分”，48 不逐位读“四八”。仅转换语音稿，画面/字幕保留原有阿拉伯数字；分钟小于10时读“零五”等，整点读“点整”。tibo 目标为梯一声、啵轻声、两音节连读；语气平稳克制，整段统一生成。


用户最新语速要求：在当前基准上仅将说话部分加快约3%（speech_rate=1.03），每句处理后再插入原长停顿，pause仍为0.20秒，不将整段含停顿音频一起加速。FFmpeg atempo保持音高，禁止额外吞尾或压缩句尾。导览2秒静音另按原规则保留。发音目标为梯一声/啵轻声；时间为十三点四十八分，字幕仍用数字。采样设置是稳定性调整，不是已验证的情绪控制，最终听感待试听。


## 当前生效：连贯语音与停顿（2026-10-27 最新）

- 主模型仍为用户认可的 Qwen3-TTS 0.6B Base，未重新训练或替换权重。
- 改为同一条新闻/场景连续生成，再用本地 FunASR 文本对齐和波形低能量句界恢复逐句时间。避免每句话单独重新采样导致的语气变化；字幕仍单行，tibo 与数字的显示稿不改。
- 取消额外 3% 加速，speech_rate=1.0。句间目标静音约 0.40 秒，场景/新闻切换约 0.60 秒；导览后的 2 秒留时仍按场景规则执行。只调整检测到的低能量间隙，不对发音尾字压缩或淡出；找不到可靠间隙就报错，不盲切活动语音。
- 保留发音目标：tibo 为梯一声、啵轻声（语音稿梯啵），13点48分为十三点四十八分，画面和字幕仍用 tibo/数字。
- 正式新闻入口根据 config.voice.qwen3.contextual_generation 调用 Voice_Generate/tools/qwen_generate_context.py；底层单句接口仍为 qwen_generate_job.py。对齐模型在 Voice_Generate/models/fa-zh，Python 在 config 的 alignment_python；只复用旧环境里的本地 ASR 依赖，不读取旧 GPT-SoVITS 音色 profile/权重。新机器需准备运行时及官方对齐模型，模型不进 Git/ZIP。
- 技术验证：18 项语音测试、54 项新闻测试通过；实际正式入口的 3 句隔离烟测通过，包含 2 秒导览留时、逐句时间映射且移除旧 GPT profile/engine 字段仍可运行。新样片为两段新闻上下文、8 句对齐输出；辅助 ASR 为十三点四十八分，识别不能替代轻声/自然度试听。
- 若新流程仍达不到用户听感要求，再训练独立的 0.6B 候选，使用留出验证与同文稿试听选模型，通过后切换 model_path；不直接覆盖可用 Base，不单纯堆轮数。当前尚未执行 Qwen 微调。


## 2026-10-27 最新：公司官方 X 与临时快讯

每小时通过 Agent Reach 顺序读取已核实的负责人和公司官方 X 白名单；制作每期前再刷新一次，不只读 RSS。沿用同一采集器 leader_sources.py、48 小时窗口、每账号最多 10 条、本地去重与 0 模型 API 调用；不是秒级实时、不保证完整历史。负责人 leader_x，官方账号 official_x，都保留作者、原发布时间、原帖与正文；负责人优先于对应公司，tibo 优先于 OpenAI，RSS/网页继续交叉核查。

已通过官方站点/组织主页反链确认并启用：OpenAI @OpenAI；Anthropic @AnthropicAI；DeepSeek @deepseek_ai；千问 @Alibaba_Qwen；智谱 @Zai_org；MiniMax @MiniMax__AI（两个下划线）。身份依据在 leader_sources.json；不猜个人账号。登录、验证码、限流仍停止本轮，不轮换后端。

公司新帖先作为候选，不自动把每条新帖制作成临时新闻；小时巡检的自动紧急发布规则仍仅为核实后的 tibo reset。用户直接指定的其他新闻可独立制作 temporary 临时新闻并按本次授权发布，不占 06/12/18 三期。此类用 temporary_kind=user_requested、temporary_event_id（原始事件稳定哈希）、event_key、authorization_evidence 和 publication_authorized_by_user=true，经 temporary_editions.py 校验；不伪造 reset 审核或挤入 reset 队列。每个事件最多两页，无导览、无不相关消息。reset 原校验保持不变。


## 2026-10-27 新稿真实自动提交验收

已从 release 正式上传本次用户指定 OpenAI GPT-6.1 Terra 临时新闻，平台 add 回执 code=0，aid=117508761717851，bvid=BV1WLnf6fEgM，提交北京时间03:05。表单读回确认科技数码、News合集9420660、AI生成/自制原创/禁止转载、公开可见、科技猎手免费活动及8个相关标签。双封面以分槽画布像素读回确认保存，不能比较随保存变化的图片URL。新稿空封面入口、Vue渲染时序、自动分类重绘、封面制作等待和折叠可见范围已完成实际兼容。

只有结构化同步字段错误、submit_started=false且经过创作中心回查，才能判定未进入提交并安全恢复；超时、未记录提交标志或submit_started=true继续unknown，不盲目重投。实际最终提交只点击一次并获平台回执。本期submitted不自动等于审核发布，公开状态以后续verify结果为准。


2026-10-27 北京时间03:05 已实际提交并经公开 view 核验发布成功：BV1WLnf6fEgM（aid117508761717851），标题与已绑定账号一致；release/2026_10_27_temporary_023452_f1be03b5b60ff10d0a33。51.27秒，1080p30，单行字幕、双封面、科技数码、News、AI生成＋原创禁止转载、科技猎手活动。已写新闻使用日志，发布后按工作流恢复归档并清理116项可再生残留约25.6MiB。不得再次上传本期。真实新稿自动投稿已验证；Edge未验证，tibo reset整条触发链不据此宣称已实发。


已授权新闻不得等待人工试听确认再投稿。早报故障恢复、旧日志兼容、已开封面窗口、安全回查后单次恢复与diagnostic_hold约束见docs/PRODUCTION_RULES.md“早报故障后的自动投稿约束”；执行render_sample.py --resume-export或upload_bridge.py recover续接既有成品，禁止重置unknown或盲目二投。

已发布防重：2026-10-27早报BV1yqHF6YEug（Anthropic 提交上市注册文件｜10.27 早间新闻）已公开核验、finalize；禁止再次投稿。


最新：主片AI建议国内3＋国外3（非硬性指标），24小时内有效未用新事件优先，不足记录缺口，不凑旧闻，回顾单列、合格新闻仍无上限。使用candidates.ai_coverage和导入时ai_shortfall_reasons/ai-coverage-audit；GoogleAI、GoogleDeepMind、Kimi_Moonshot、MiniMax_AI均只在视频制作前读取。投稿采用字段级恢复、重复提交守卫和实现指纹；修复统一sync_upload_skill部署并验证，详见PRODUCTION_RULES.md。


后续所有新闻固定活动：明日方舟终末地创作者应援计划，话题ID1325166，strategy=explicit；替换科技猎手，不自动选择其他热门活动。必须核对真实活动标记，不可用则保留release并报告。既往发布稿不修改。


当前补充：AI条数与3＋3比例仅建议，按实际有效素材制作、不生造；少选理由可选不阻塞。选题覆盖腾讯WorkBuddy、混元/HY，以及Codex/Claude Code等官方产品与Agent，读取已核验RSS/X/官网更新日志；产品支持现有模型不当成新模型发布。详见PRODUCTION_RULES.md“建议条数与产品 / Agent 来源”。


新版画面导览：00展示完整主语标题＋一句事实说明，通常3—4项、两列布局，附有主语的板块总述；不用short_title标签凑目录，不放思考过程。仅根据本期实际内容生成。口播仍只说“这是本视频的导览。”并留2秒，不逐条朗读；reset仍默认无导览。细则和代码见PRODUCTION_RULES.md、layout_policy.py、build_film.py。


当前负责人规则：正常、新鲜且有信息价值的推文优先考虑（包括观点/体验）；主片tibo已核实reset在公司前、普通发言在公司后社会新闻前，tibo最多1页，其他负责人每人最多2页。画面强调已核实身份；口播可省职位但必须有姓名主语＋原帖北京时间＋具体内容，不能用采集时间或编造分钟。近24小时未用负责人候选须入选或用tibo_consideration/leader_consideration记录真实skip/defer原因；leader_editorial.py在导入配音前落实身份、主语时间、排序和页数，输出审计到release。规则细节见PRODUCTION_RULES.md和X_PRESENTATION.md；不改已发布稿、不改小时采集范围、不把reset关键词当已核实公告。


背景音乐当前要求：后续主片/临时新闻使用本地assets/music/oshinko.flac《おしんこ》，全片固定低音量循环到片尾；不用播报ducking，不在停顿时抬高。audio_mix.py统一生成soundtrack.wav供预览和渲染复用，原配音独立保留、实测报告随release。目标音乐显著低于播报，必要时全曲统一降低；原曲不进Git/交接ZIP，缺源或哈希错误停止。详见docs/BACKGROUND_MUSIC.md；既往成品不重做。

背景音乐循环：首遍从头，第二遍起每轮从00:03开始，开头3秒只播放一次；config.background_music.repeat_from_seconds=3。

今天（2026-10-27）午间新闻开始使用本次背景音乐流程：首次从头、后续从00:03循环，固定低音量，无播报闪避；新稿背景音乐需求经release门禁核对再上传。

背景音乐可听性修正：以正常播报窗口中位数定固定增益（参考差18dB、目标-32LUFS、音乐峰值-24dBFS），不再用最弱尾字限制整首导致听不到。仍无ducking、后续从00:03循环；原曲本体位于项目assets/music/oshinko.flac。详见BACKGROUND_MUSIC.md，午报使用此新版。
