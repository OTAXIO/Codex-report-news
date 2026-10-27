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
