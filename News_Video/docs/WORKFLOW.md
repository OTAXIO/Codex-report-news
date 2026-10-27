> 2026-10-27 最新采集范围：小时巡检只读取 tibo @thsottiaux 并处理 reset、回查投稿；不采集社会 RSS，不读取公司或其他负责人 X。社会 RSS、公司官方 X 和其他负责人仅在视频制作前刷新。每期执行 collect --kind all（社会 RSS + AI 官方来源 + 全部启用 X），不能只复用旧社会缓存。新模型线索在制作阶段采集后按 MODEL_ALERTS 核验，已有授权与去重规则保留。

# 制作与上传执行流程

完整约束以[PRODUCTION_RULES.md](PRODUCTION_RULES.md)为准；先读STATE与config解析当前路径。

1. 以require_escalated运行 `python -B news_video.py collect --kind all`：刷新社会RSS、AI RSS/官方网页和全部启用X。`candidates --hours 48`含新事件和important_recaps。
2. 核实原作者、原分钟时间、上下文、状态及已用日志。常规国内3+国际3，AI不限；敏感跳过。
3. help-me-speech写editorial。`import-editorial <json>`会先补主片重要回顾（只有已公开核验temporary、近24小时），再默认补00概览，最后核验来源/授权/去重。回顾与新事件分开，不从普通去重接口放行任意重复内容。
4. `news_video.py voice <id>`：Qwen3连续上下文+规范化读音+本地对齐；模型名静音上限约.12秒，句间.4/切页.6。标准导览口播后2秒。
5. 填cover.json：headline_top/headline_main/highlight/image，footnote仅短类型说明如模型发布速报，无日期；不再使用subtitle。`cover_generator.py <id>`生成双封面。
6. `build_film.py <id>`：概览00/正文01，未带概览也正文01。检查来源时间、完整单行字幕、大logo和分段导航。
7. HyperFrames check --json、两页以上实际截图检查后`render_sample.py <id>`，自动解码/导航校验、日志、release和已授权上传。必要时--no-upload仅用于诊断，不冒充已投稿。
8. `upload_bridge.py pending`查submitted/unknown。公开归属、标题核验成功才finalize，不重复调用publish。

## 小时巡检与临时新闻

`hourly_monitor.py`基线→仅tibo X→reset扫描，不请求社会RSS和公司X，不扫描新模型队列。0模型API、无大范围搜索。关键词只入needs_review队列，不直接发视频。小时任务指令保存在HOURLY_MONITOR_PROMPT.md并同步应用自动化。

- reset：按RESET_ALERTS.md核实；`reset_alerts.py draft <id> <review.json>`。
- 新模型：按MODEL_ALERTS.md核实；`model_alerts.py draft <id> <review.json>`。
- 模型draft默认00概览+01正文，reset默认01正文；单一事件不占主片。忙则保持draft队列，不覆盖在制film/voice。
- 确认新模型发布和reset后已获自动最终提交授权，不重复询问；身份/时间/上下文不完整或验证要求需真实处理，不绕过。

## 投稿实操

project skills/codex-upload是生产实现。先doctor核对登录/账号；迁移后校验Node、Chrome、Puppeteer绝对路径是否存在。新稿空白封面也可打开编辑器，等待真实制作完成，双比例分槽画布像素读回；AI与原创分开多选。设置/标签/活动/合集/可见范围读回后只提交一次。字段失败在同一表单有限重设，未知不可盲目再次选视频；状态守卫与reconcile规则见CODEX_UPLOAD.md。

测试只用隔离fixtures与本地样例，不拿已发布视频做上传或编辑回归。所有本次变更只用于未来生成，不重做旧成品。


## 2026-10-27 早报故障后的自动投稿约束

- 已授权的正式早午晚/临时新闻，技术质量检查通过后立即投稿；“尚未人工试听/等用户确认音色”不是额外授权关卡，不得因此停在release。明确的音频缺失、时序/解码/内容错误仍必须修复，用户明确要求暂停/审核时以用户指令为准。
- 用旧日志也必须可完成导出：used_news读取时补齐缺失edition_key，兼容无episode_id/video_sha256的来源关联行，不覆盖原JSONL；同片同哈希写日志幂等。日志失败保留MP4，通过render_sample.py <id> --resume-export续接，不重配音/重渲染，不跳过去重记账。
- 已有upload-attempt的release不能重新prepare并把unknown清成ready。resume-export沿用成品与回执，交upload_bridge.py recover <release目录>；已有submitted/reviewing只核验，published直接跳过。
- 封面制作是受支持的窗口：标题、双比例槽与图片输入同时匹配才安全关闭自动打开/残留窗口，随后加载本期定稿封面并像素读回。未知弹窗、认证/验证码仍停止，不盲点完成。
- unknown必须先创作中心回查。只有回查成功、结构化同步字段失败、明确submit_started=false才转failed并保存safe_retry_evidence；仅“没搜到稿件”不足以重试。超时/缺提交标志/已经开始提交保持unknown，不重投。
- 项目recover连接回查与恢复：安全确认的提交前故障最多自动恢复1次，超过上限保留release并报错；不无限循环。pending恢复submitted/reviewing/unknown，以及明确upload_policy=automatic的ready/failed；diagnostic_hold不自动上传。
- 技术检查、成品就绪、提交、公开发布分开记录。最终按钮一次；code0+平台ID才submitted；公开账号/标题一致才published/finalize。不能以口头“继续尝试”替代调用，不能报告无回执的成功。
- 定时目标仍06/12/18；记录实际延迟，不承诺平台审核时刻。失败先修复同一成品，不重做旧片，不因错过目标时间自动取消投稿。


## 当前补充：AI 选题与投稿部署

AI主片尽量国内3＋国外3，优先24小时未用有效事件；不足则记录实际缺口，回顾单列，合格新闻无上限。candidates.json的ai_coverage提供地区候选；import-editorial生成ai-coverage-audit.json，ai_shortfall_reasons（国内domestic、国外international）可选，不作为条数门槛。Google AI/DeepMind、Kimi、MiniMax的X与官方RSS/网页进入统一采集；具体来源和边界见PRODUCTION_RULES.md。

投稿修复后运行 `python -B sync_upload_skill.py --apply --installed` 统一部署，随后 `--check --installed` 只读验证。配置的implementation_sha256与实际实现不符会在调用浏览器前阻止操作。表单只修失败字段，不重填整张表；已开始提交禁止二次点击。更新不等于未来平台永不变化，隔离回归与真实公开回执分别记录。


## 2026-10-27 最新固定活动

用户指定：之后所有新闻（早/午/晚及临时新闻）固定参与“明日方舟终末地创作者应援计划”，话题ID1325166；替换“科技猎手”，不再按热门度或相关性自动挑其他活动。活动名称依据官方公告，ID来自官方跳转B站活动页https://www.bilibili.com/blackboard/era/hProYF7NSH5CPvi7.html。

默认profile及本机有效profile采用strategy=explicit、精确ID＋名称、fallback=stop。from-release剔除旧科技猎手标签，保留平台活动标签所需容量；未在六个推荐中出现时输入精确活动标签并回车，必须读回平台topic-icon活动标记，普通同名文字标签不算参加成功。不可用/未识别/旧活动未移除时保留release并报错，不改投其他活动。活动奖励或内容资格由平台判断，不把选中话题等同获得奖励。

本要求只用于之后新稿，不修改已发布视频/历史回执；其他分区、News合集、原创/AI生成、标题封面规则保留。


当前补充：AI条数与3＋3比例仅建议，按实际有效素材制作、不生造；少选理由可选不阻塞。选题覆盖腾讯WorkBuddy、混元/HY，以及Codex/Claude Code等官方产品与Agent，读取已核验RSS/X/官网更新日志；产品支持现有模型不当成新模型发布。详见PRODUCTION_RULES.md“建议条数与产品 / Agent 来源”。


## 2026-10-27：充实的画面导览

导览画面不再直接复制底部导航的short_title，禁止只写“拟上市申请”“远古化石”“模型发布”等缺少主体的标签。每项使用完整新闻标题，写清公司、人物、机构或具体事件主体，并配一句有主语的事实概括；优先复用已核验正文/口播，保留“计划、可能、据官方测试、回顾”等限制，不增添新结论或内部思考。

画面00以“本期新闻导览”为标题，附一条完整、有主语的总述，说明本期实际包含哪些板块以及介绍顺序。通常展示3—4项重点（最多4项），每项“板块名称＋完整标题＋一句事实说明”，采用白底黑字、蓝色点缀的两列布局；有国内/国际内容时兼顾板块，不让全部格子被同类AI消息占满。只有1—2条就展示实际数量，不虚构板块或凑满4格。剩余新闻仍由底部导航承载，导览不是整期目录的缩写堆砌。

保留用户此前“不朗读导览”的要求：口播仍只说“这是本视频的导览。”，不逐条念标题或解释，随后保留2秒；正文01起。此次丰富针对画面内容，不借机增加长开场配音、改语速或重训音色。reset紧急稿仍默认直入01、无导览。

layout_policy.prepare_overview在配音前生成：完整title代替short_title；overview_detail优先取scene.overview_detail或正文第一条有事实内容的完整句，跳过纯转场/回顾提示句；保留概括所需的主体、原归属与条件。支持scene.overview_title/overview_detail由写稿代理提供更精练的忠实表述，禁止截半个单词或机械拼凑主题标签。自动选取实际板块代表后按正文顺序排列，同一事件不重复占格。

旧的自动空白说明导览在下次导入未发布稿时升级，人工写好的完整导览保留。build_film对overview使用独立字号与两列卡片样式；已发布成品保持不动。在隔离目录对新版导览做HyperFrames检查与真实截图验证，不覆盖正在制作的共享film。


## 2026-10-27：负责人发言、身份与口播主语（当前规则）

负责人有新鲜、正常且有信息价值的推文时优先考虑展示，不限于正式产品公告，也可展示有趣的观点或体验；明确这是个人观点、预告还是已发生事实。无公司公告也可独立入选。敏感、不完整、缺必要上下文或重复已用的内容跳过/暂缓，改选其他新闻，不硬凑数量。

主片顺序：经语义核实的tibo额度reset放在公司AI新闻之前，普通tibo发言放在公司AI新闻之后、社会新闻之前。tibo每期最多1页新闻画面，可精选合并多帖；其他已核实负责人同样在公司板块后展示，每人最多2页画面（不是2条推文），放不下就精选总结。重要reset/新模型回顾继续按important_events规则保留，不因临时稿已播而漏掉主片重点；已发布成品不重做。

画面突出姓名和已核实身份，例如“tibo｜OpenAI · Codex / ChatGPT 团队”“Sam Altman｜OpenAI CEO”“Boris Cherny｜Anthropic · Claude Code 负责人”。身份只取leader_sources.json中有依据的identity_label，不猜职位，不将团队成员写成CEO。必要时配有来源的头像或原帖截图。观点、预告、转发要标清，不把个人观点冒充公司公告。

口播可以不念职位，但必须有主语、原始发布时间和具体内容，例如“tibo 于北京时间10月27日13点48分发表推文，提到……”。这只是格式示例，不是一条真实新闻。分钟取原帖published转换北京时间，不用采集时间替代；跨日及回顾说清日期。缺精确时间不编造几点几分，保留可核实日期和主语；缺必要时间证据的时效快讯暂缓。显示和字幕可用数字，配音经现有pronunciation转换为“十三点四十八分”；tibo读音规则保留。避免无主语的“表示了……”“提到……”，也不机械重复一长串身份。

代码入口：leader_editorial.py生成负责人候选审核清单、屏幕身份和口播原时间引导，并在主片导入时执行页数/顺序/遗漏审核；news_video.py在概览、分句和配音之前调用。每个近24小时未用负责人候选要么入选，要么记录真实skip/defer原因，防止采到却无声漏掉；这是编辑核查记录，不是强制播出配额。tibo_consideration与leader_consideration按候选item_id记录decision/reason，审核输出tibo-audit.json、leader-audit.json并保留到release。reset关键词不等于重置宣布，仍需原文、上下文及真实语义核验，不允许伪造审核字段。

每小时只采tibo，社会RSS、公司/产品官方X及其他负责人均在视频制作前读取，不额外扩大小时搜索；身份/账号未经核实的不凭名字加入。导览仍只播固定提示并留2秒，正文负责人场景适用上述主语规则。模型、语速、句间停顿与既有发布成品不在此次调整范围。


## 2026-10-27：固定低音量循环背景音乐

后续制作所有主片和临时新闻使用用户提供的《おしんこ》FLAC作为背景音乐。原文件已复制至本地assets/music/oshinko.flac（94.366667秒），config.background_music记录SHA256与混音参数；不依赖Downloads原文件继续存在。原始音乐及本地来源记录不进入Git或DSH交接ZIP，换机按docs/BACKGROUND_MUSIC.md准备同一文件并验哈希。

用户最终要求：全片使用固定低增益，不随播报或停顿升降，不开启ducking/sidechain；仅整片起止约0.35秒淡入淡出。循环播放到视频结束，严格裁到timings.duration，不因一首结束而提前停音/停片。配音优先，保持音色、语速、句间与概览停顿；不重训、不压尾字。

实现audio_mix.py：配音基准-16 LUFS，音乐初始目标-32 LUFS（不是音量百分比），分析200ms正常播报窗口，以窗口音量比的中位数作为整期参考，音乐至少低于代表播报18dB，音乐峰值上限-24dBFS；不再用最轻尾字控制整条音乐。检测阈值、实测差值与恒定增益写入audio-mix.json；静音间隔不自动抬高音乐。不以数值检测冒充主观听感已获用户确认。

build_film和render_sample共用同一soundtrack.wav；后者不再对混音整体二次loudnorm，避免重新抬高背景。纯配音narration.wav独立保留，release保留soundtrack.wav/audio-mix.json便于复核。doctor检查音乐文件/哈希；启用时素材缺失、哈希不符、无有效配音或混音不达标均报错，不默默换曲或生成只有音乐的新闻。缓存绑定原配音/原曲哈希、时长与参数。resume-export仅续传已有成品，不借本次功能修改已发布或已导出的旧视频。


循环起点补充：首次完整播放原曲；从第二遍开始每次从原音频00:03起播放到曲尾，前3秒只播一次。audio_mix.loop_music按48kHz采样帧拼接，循环体为[3秒,原曲结束)，最后按视频时长裁切，不每轮重新淡入淡出。repeat_from_seconds=3；换曲后偏移超出曲长则报错。固定低音量、无播报闪避不变。


2026-10-27午报应用：用户要求本次音频制作流用于今天午间新闻。当前尚无本日noon工作期次或release；之后import-editorial会为新稿固化background_music_requirement（曲目哈希、00:03循环起点、固定低增益、音量限制），release准备阶段必须验证audio-mix.json与soundtrack.wav、时长和输出哈希相符，不允许缺少BGM或错误循环的新版午报放行。旧已导出稿无此标记时仍可按原流程续传，不重做旧稿。


2026-10-27可听性修正：旧的“所有200ms窗口至少20dB差值”会因一个很轻尾音把全曲额外压低，用户反馈听不到，现已废止。以active_window_median正常播报代表值校验18dB差距，最低窗口差仅记录诊断、不再触发全曲压低。固定增益、无ducking、首遍从头/后续00:03循环保持。原曲实际保存在项目assets/music/oshinko.flac，不依赖Downloads，原曲不进公开Git。


## 2026-10-27：重点回顾按事件每天一次（最终澄清）

回顾不是限定只放早报，也不是每天只允许一个主视频包含回顾。每条具体事件在北京时间同一天只在首次合适的主片中报道/回顾一次：凌晨临时新闻可在早报回顾，午晚报不重复；上午新临时新闻可在午报回顾，晚报不重复；下午出现的新事件可在晚报首次回顾。不同新事件各自独立，不因为早报/午报已播过其他事件而禁止后续回顾。

important_events读取同日成功主片导出日志及release中的episode回退记录，按稳定event_key及原始event_key、item_id或规范化原始URL识别同一事件。正常新闻报道与重点回顾均消耗该事件当日主片展示次数；temporary本身不消耗一次主片回顾。只有成功导出/已有成品才记使用，草稿和配音中不提前消耗；同一日期时段的修订沿用原归属，不算新一期。保留原有近24小时、已公开核验temporary、原作者/时间/回顾措辞等条件，不借新规则恢复旧闻或生造新闻。

prepare_main_recaps逐事件决定插入，并移除编辑输入中本日已由其他主片用过的回顾；episode.recap_policy输出once_per_event_per_beijing_date及skipped_event_keys。validate_recap在导入时校验，used_news.record_export在写日志锁内再次逐条验证，防止先前草稿稍后导出造成重复。不同事件或真实实质新进展仍按正常选题与事实核查，不因共用公司/人名被一并排除；相同消息换标题不算新事件。跨日重新按当日记录判断，但仍受24小时时效限制。

已发布视频不改。本期未发布午报按新规则重导入时，若回顾被移除，必须同步重新生成受影响的配音、字幕、时序、导览与导航，不允许只删画面留下旧口播。涉及正在运行的配音/渲染由制作会话安全衔接，不覆盖其共享素材。
