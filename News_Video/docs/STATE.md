> 2026-10-27 最新采集范围：小时巡检只读取 tibo @thsottiaux 并处理 reset、回查投稿；不采集社会 RSS，不读取公司或其他负责人 X。社会 RSS、公司官方 X 和其他负责人仅在视频制作前刷新。每期执行 collect --kind all（社会 RSS + AI 官方来源 + 全部启用 X），不能只复用旧社会缓存。新模型线索在制作阶段采集后按 MODEL_ALERTS 核验，已有授权与去重规则保留。

# 已完成状态与本机边界（2026-10-26）

- 今日最后确认的版本：daily-20261026-evening-v3。用户此前自行发布；本次已通过受管 Chrome 读取真实平台数据核验 BV1UxnZ6AEVZ、账号归属与标题，已写入私有哈希防重账本。
- 成品在 D:/Basement/Codex_Video/release/2026_10_26_night；现视频名为 2026_10_26_night_晚间新闻.mp4，140.351 秒，1920×1080 30fps H.264+AAC，3 条 AI＋国内 3 条＋国际 3 条。
- 导览口播实际 1.39 秒，静音 2 秒，正文 3.39 秒开始；AI→社会新闻在 50.41 秒，已加入承接句。字幕 42 段、单行，最短 1.39 秒。
- 旧版和临时渲染文件已做恢复包后清理；audit/work-history.zip 为本机恢复历史，不纳入 DSH 交接包。117 个受保护文件核对未改变，清理后当时 23 项测试通过；新工作流的回归结果以 docs/VALIDATION.md 为准。
- 新闻库 data/news.sqlite3、来源缓存 data/articles/、采集记录、logs/news-used/ 保留。今天 3 次导出属于同一期修订，唯一新闻为 9 条。下一期不能因为换模型或换日期丢弃这份历史。
- 制作由 Codex 会话进行选题和编辑，非单独配置的无人值守模型 API。2026-10-27 已为 6/12/18 点主片在当前对话启用定时任务，分别于北京时间 05:45、11:45、17:45 启动；首次定时制作和准点完成尚待实际验证。小时来源巡检实际启用信息见 RESET_ALERTS.md。
- 本机可见 D:/Basement/deepseek_harness/DeepSeek Harness.exe，文件 ProductVersion=0.2.1.0。只验证文件存在，未启动、未验证登录、模型设置或 skill 自动加载；不沿用旧安装笔记的端口或插件路径。
- BrowserSkill 能读页面/填部分字段，但本地文件上传因缺少 Allow access to file URLs 权限返回 Not allowed；视频与封面实际依赖用户手动选择。未改变扩展权限，也未绕过停止按钮。用户最终自行完成投稿。
- 项目成品和交接包不保存 B 站 Cookie、浏览器 profile 或 DSH API key；受管 Chrome 登录仅在本机包外的 .codex-upload-private。交接包不包含模型权重、依赖目录、微软字体、私密登录文件或旧恢复大包。

- 最新来源要求已覆盖早先禁用 X 的限制：每小时用 Agent Reach 读白名单负责人推文，tibo 优先于 OpenAI/GPT，其他负责人优先于对应公司，支持只有负责人新消息。twitter 渠道依赖已启用；安装不等于读帖验收通过，实际状态见 X_SOURCES.md。今天已发布版不回填或重复上传。

- 用户完成 X 专用登录后，tibo 真实读帖成功，4 条新候选已入库并进入排序。负责人候选依然需要检查相关性和上下文，不自动当官方公告。

- reset 临时新闻代码与 38 项回归已通过；首次真实小时链路于 2026-10-26 北京时间 22:13 验收成功：tibo 最近 10 条中 7 条通过入库检查（3 条新入库），旧缓存 4 条建立基线，没有新的可核查 reset 紧急条目。未追发白天旧消息。

## codex-upload 接入更新

独立 Chrome 投稿器已实现，真实账号登录和已发布稿件只读核验成功。News 合集存在重名，私有配置已锁定有当前视频的实际合集 ID；不取第一个同名合集。制作 render 在 release 验收后自动生成 upload.codex.json 并投稿，未知回执不盲目重试，小时巡检回查审核结果后清理。Edge 尚未兼容验收。真实新稿完整平台投稿尚未实测，不能把离线模拟回执当真实回执。当前公开成品仍只有今天的晚间版，不重复上传。

GitHub main 已推送并远端核验：7e5aac5f296c3e811352652127e596739eb78f10。全局技能和项目技能已安装同步。测试为投稿器 10＋3 项、新闻项目 41 项通过；详见 VALIDATION.md。


## 2026-10-27 X 本地权限修复

此前 UPSTREAM_BROKEN 的直接原因为受限执行无法写入 Agent Reach 已有 browser-locks，读取尚未到 X 即退出；不是已证实的登录失效或 X 平台故障。采集 wrapper 已区分 LOCAL_PERMISSION_DENIED，且不保存 stderr 或凭据；真实平台登录/验证/限流停止规则保留。小时任务已明确使用 require_escalated 运行既有只读采集，并修复任务提示词中文乱码、更新迁移后路径。

北京时间 00:03 的同一专用渠道实读成功：返回 10 条，7 条合格，3 条不入候选，无新增待核查 reset；最近一条为 2026-10-26 13:48:30 的 ChatGPT 外观提醒（原链接见 x-runtime-fix-20261027.json），旧 reset 不追发。46 项回归通过。迁移锁存在时按迁移规则暂停采集，解锁后恢复；不擅自删锁。


## 2026-10-27 迁移后恢复与新画面要求

迁移锁已解除。北京时间 00:16–00:17 用新生产路径和正确本地权限完成真实小时链路；tibo、sama、bcherny 三个渠道请求均成功，tibo 7 条通过候选检查，无新增待核查 reset；其他账号本次返回未通过候选检查，不声称有可播新消息。数据/去重状态未重置。

来源时间已在 build_film.py 改为普通及临时稿统一尽量显示到分钟，准确标时区与日期精度；50 项回归通过。每位负责人每期最多 2 页画面（非 2 条推文）、AI 可忠实总结、多条合并及原帖截图/头像等新要求已写入 X_PRESENTATION.md、项目 prompt/工作流/技能和 DSH_PROMPT.md。本次未重新生成或上传成片。


## 2026-10-27 Qwen3-TTS 与后台窗口更新

用户已选择 Qwen3-TTS。新闻默认后端现为 config.voice.backend=qwen3，0.6B Base + 现有“帝江号，我已就位，该出发了”参考音频；GPT-SoVITS 原权重、profile 和运行时保留，改 backend=gpt-sovits 可回退。Qwen 接口通过独立 Python 环境和 tools/qwen_generate_job.py，使用逐句映射以保留字幕/导览停顿；Qwen 的 cleanup 强制 off，不做尾字压缩/淡出或机械拉伸语速。旧 GPT-SoVITS speed/cleanup 等参数不是 Qwen 的已实现控制参数，不能混淆。

官方约 2.5GB 权重已下载并逐文件校验 SHA-256；本地克隆样音成功（8.4 秒），新闻入口真实隔离烟测通过逐句输出、2 秒导览停顿和时间映射，无视频生成/上传。安装版本冲突已解决，pip check 通过。自然度与音色仍待用户试听，不能宣称优于旧模型或已完成 Qwen 微调。新方法和训练路线见 VOICE_UPGRADE.md。28 条训练＋4 条验证已导出，尚未训练。

截图命令框属于 Agent Reach 专用 Python 辅助进程。项目采集器现使用 Windows 隐藏启动并仅隐藏标题完全匹配用户 .agent-reach/tools 下 Python 的辅助控制台，不关闭进程，不隐藏 X 登录/验证页面，不影响其他终端。改后真实 tibo 读取成功、reset 无新队列。


## 2026-10-27 最新模型取舍（覆盖 1.7B 试验意向）

用户确认 Qwen3-TTS 更好，若 1.7B 显存不足则放弃，0.6B 已足够。当前继续使用用户认可的 0.6B Base 参考音频克隆，不在 8GB 显存设备强行启动 1.7B 全参数训练；增加轮数不能解决显存不足。1.7B 下载目录已清理，没有 1.7B 训练结果，也没有完成 Qwen 微调。未来训练 0.6B 需先做 24kHz 数据/参考归一化、音频码准备和显存试跑，按验证与试听选模型，不仅增加轮数。

旧 GPT-SoVITS 的 17 个非当前运行依赖检查点已可恢复移至根目录 .retired-models/20261027-gpt-sovits-checkpoints（约 5.30GiB），SHA-256 已验证，原始音频/标注/参考保留；归档没有释放其磁盘占用。原 GPT-SoVITS 外部运行时与历史代码暂保留，不整库删除；历史训练 profile 如引用归档文件需先恢复。更新后的 Voice_Generate/README.md 为当前语音项目入口。


2026-10-27 已使用默认 Qwen3-TTS 0.6B 制作两页配音视频样片，单行内嵌字幕、来源时间和逐条进度高亮。tibo 的口播固定 ti bo，画面/字幕保留 tibo；仅重生成受影响的一句并保留其他音频采样。样片写入 release/previews，不上传，不计正式新闻已用日志。


最新样片 v4：tibo 口播目标梯一声、啵轻声（TTS用梯啵），时间转“十三点四十八分”，字幕保留数字/tibo。8句全部以同一参考和设置重新生成，没有沿用局部修补的旧句；说话部分额外1.03倍，句间0.20秒保持。新样片约40.09秒，输出release/previews/qwen3-voice-demo-ti1bo0-steady-fast-v4，不上传、不登记新闻已用。54项新闻回归通过，时间读法和语音变速/停顿回归通过。情绪与轻声听感仍由用户试听判断，不将采样温度视作原生情绪控制。


## 当前生效：连贯语音与停顿（2026-10-27 最新）

- 主模型仍为用户认可的 Qwen3-TTS 0.6B Base，未重新训练或替换权重。
- 改为同一条新闻/场景连续生成，再用本地 FunASR 文本对齐和波形低能量句界恢复逐句时间。避免每句话单独重新采样导致的语气变化；字幕仍单行，tibo 与数字的显示稿不改。
- 取消额外 3% 加速，speech_rate=1.0。句间目标静音约 0.40 秒，场景/新闻切换约 0.60 秒；导览后的 2 秒留时仍按场景规则执行。只调整检测到的低能量间隙，不对发音尾字压缩或淡出；找不到可靠间隙就报错，不盲切活动语音。
- 保留发音目标：tibo 为梯一声、啵轻声（语音稿梯啵），13点48分为十三点四十八分，画面和字幕仍用 tibo/数字。
- 正式新闻入口根据 config.voice.qwen3.contextual_generation 调用 Voice_Generate/tools/qwen_generate_context.py；底层单句接口仍为 qwen_generate_job.py。对齐模型在 Voice_Generate/models/fa-zh，Python 在 config 的 alignment_python；只复用旧环境里的本地 ASR 依赖，不读取旧 GPT-SoVITS 音色 profile/权重。新机器需准备运行时及官方对齐模型，模型不进 Git/ZIP。
- 技术验证：18 项语音测试、54 项新闻测试通过；实际正式入口的 3 句隔离烟测通过，包含 2 秒导览留时、逐句时间映射且移除旧 GPT profile/engine 字段仍可运行。新样片为两段新闻上下文、8 句对齐输出；辅助 ASR 为十三点四十八分，识别不能替代轻声/自然度试听。
- 若新流程仍达不到用户听感要求，再训练独立的 0.6B 候选，使用留出验证与同文稿试听选模型，通过后切换 model_path；不直接覆盖可用 Base，不单纯堆轮数。当前尚未执行 Qwen 微调。


2026-10-27：六家官方 X 账号已接入同一小时白名单（official_x），保留负责人优先/RSS补充。实读 OpenAI 3条、Anthropic 1条近48小时候选；DeepSeek/智谱未入新候选；千问独立读成功但无合格候选；MiniMax本轮 UPSTREAM_BROKEN，未换后端。用户指定 OpenAI 新模型临时新闻已生成51.27秒并准备release；首次新稿实投在原创控件处中断，尚未确认提交，正在回查。

本轮新增60项新闻回归通过。制作前 collect --kind ai/all 已在 RSS/官方网页之后自动刷新白名单 X；社会采集不重复触发。HyperFrames 两页51.27秒检查及实图通过，MP4 1080p30、AAC、0解码错误。B站投稿器针对新稿空封面入口、声明控件渲染时序、双封面画布读回进行了实际页面修复，提交结果仍须看最终回执。


## 2026-10-27 新稿真实自动提交验收

已从 release 正式上传本次用户指定 OpenAI GPT-6.1 Terra 临时新闻，平台 add 回执 code=0，aid=117508761717851，bvid=BV1WLnf6fEgM，提交北京时间03:05。表单读回确认科技数码、News合集9420660、AI生成/自制原创/禁止转载、公开可见、科技猎手免费活动及8个相关标签。双封面以分槽画布像素读回确认保存，不能比较随保存变化的图片URL。新稿空封面入口、Vue渲染时序、自动分类重绘、封面制作等待和折叠可见范围已完成实际兼容。

只有结构化同步字段错误、submit_started=false且经过创作中心回查，才能判定未进入提交并安全恢复；超时、未记录提交标志或submit_started=true继续unknown，不盲目重投。实际最终提交只点击一次并获平台回执。本期submitted不自动等于审核发布，公开状态以后续verify结果为准。


2026-10-27 北京时间03:05 已实际提交并经公开 view 核验发布成功：BV1WLnf6fEgM（aid117508761717851），标题与已绑定账号一致；release/2026_10_27_temporary_023452_f1be03b5b60ff10d0a33。51.27秒，1080p30，单行字幕、双封面、科技数码、News、AI生成＋原创禁止转载、科技猎手活动。已写新闻使用日志，发布后按工作流恢复归档并清理116项可再生残留约25.6MiB。不得再次上传本期。真实新稿自动投稿已验证；Edge未验证，tibo reset整条触发链不据此宣称已实发。

最终回归：61项新闻测试、10项投稿器核心测试、3项含真实隔离Chrome的表单测试全部通过。已确认本次3条原公告均从下一期候选排除；同事件官网加入已用来源关联。


## 2026-10-27 实操后规则更新

- 当前统一规则在PRODUCTION_RULES.md，项目入口和DSH指向该文件。官方X恢复每小时，与tibo一起；其他负责人每期前。新增model_alerts语义审核队列、版本事件去重、授权/正式发布状态校验和temporary草稿，标记release/publication状态。
- 主片近24小时重要回顾已独立于普通去重实现；使用真实已发布Terra成品的隔离数据库导入烟测通过，00概览→AI回顾→社会新闻，无新上传。
- cover_generator已删除subtitle说明行，footnote移除日期；隔离封面实图已检查。实际build_film在无概览时生成01/02，单一概览00约束通过测试。
- Voice_Generate共享speech_text对调用读音及模型版本空格做TTS专用规范化，context_alignment只缩短复合名纯静音，保留句间/新闻间停顿。22项语音测试、约7.79秒两句真实本地合成/对齐烟测通过；此样例无需缩短额外词内静音，不能声称听感已获用户认可。
- 71项新闻测试、10项上传核心测试、4项含无登录Chrome表单测试通过。投稿器已同步本地源仓库、项目快照、已安装skill，源码未推送。已发布视频/封面SHA-256逐一核对未变。新增小时模型触发规则尚无新真实事件端到端发稿，未为测试重投旧稿。


## 2026-10-27 早报恢复与投稿可靠性修复

兼容缺edition_key/episode_id/video_sha256的旧使用日志及来源关联行；render支持--resume-export；已有投稿release禁止prepare重置。封面自动弹窗按结构处理，News合集反选在同表单有限恢复。upload_bridge recover/pending连接安全回查与单次自动恢复，不再以人工试听为授权关卡，诊断稿hold不上传。已同步生产skill/源仓库/安装skill以及规则、V_0排错手册、DSH提示词。77新闻+10投稿核心+4隔离Chrome表单测试通过。

早报原封面故障恢复后遇COLLECTION_MISMATCH；均有submit_started=false与创作中心回查，修复后继续用户明确授权的早报投稿。北京时间08:44:47取得code0、aid117510087118331、BV1yqHF6YEug；第一次公开verify为-404，当前仅确认submitted，不重复上传。后续公开核验另记。成片MP4保持原SHA256 7ce67e3c3b189b2c876645d0ee63b50128eed47cd72ef4628e0fb616f6584407。


后续真实公开核验已通过：BV1yqHF6YEug，绑定账号mid511076233、标题Anthropic 提交上市注册文件｜10.27 早间新闻一致；已finalize归档清理，release MP4 SHA256保持不变。本期禁止再次上传。归档README/发布日志改为按真实公开证据记platform verification，不误标用户口头确认。


## 2026-10-27 09时：AI 3＋3与投稿流程维护

用户要求代码落实，已增加editorial_policy.py、config.ai_coverage/vendor_regions、候选地区统计及主片导入审核记录，目标国内3＋国外3、优先24小时，重要回顾另计，合格AI无上限。新来源GoogleAI/GoogleDeepMind/Kimi_Moonshot加入official_x，MiniMax_AI保留；Google官方RSS、Kimi公告RSS和日期博客已接入。新模型扫描已识别Gemini/Gemma/Veo/Lyria/Kimi，仍需语义核验。

真实Agent Reach读取：GoogleAI成功、10条均超48h；GoogleDeepMind接受2、Kimi接受1、MiniMax接受3（48h窗口，接受不等于已审核可播）。真实隔离RSS/网页完整采集：Google AI20、DeepMind100、Kimi公告9、Kimi博客10、MiniMax新闻页2；0模型API，不据条目总数声称新鲜新闻数量。证据在data/source-probes/20261027-ai-coverage.json。

投稿skill改为字段级有界修复，不因晚到分类不一致重填全表；封面等真实DOM挂载；重复submit_started拒绝二点，回执只认POST。sync_upload_skill.py统一源码/生产/安装三份，已应用并校验指纹70afe39e50c65f35d0e664e5c610ccc731d79d1875d8f23c403b3dabc0fcb605；doctor绑定mid511076233、版本一致。本次未制作新视频或重新上传已发稿，不把新字段恢复的隔离测试称作新实投。

最终回归：87项新闻测试（含SQL→主片导入→地区审计集成）、10项投稿核心测试、4项含隔离Chrome的表单测试通过。新增来源、规则和字段级恢复已同步Notion手册；交接包同时包含对应版本的公开投稿器源码，便于DSH部署校验，不依赖远程旧checkout。源码未提交/推送，成品未重做或重投。


## 2026-10-27 固定新闻活动

用户指定后续所有新闻使用明日方舟终末地创作者应援计划，替换科技猎手。已核对官方公告https://endfield.hypergryph.com/news/9326及其B站活动页，页面topic_name与topic_id=1325166匹配。已修改source默认profile、本机有效profile、项目配置、skill及DSH文档；代码精确匹配并剔除旧标签，未推荐时通过标签输入＋平台活动标记核验，不可用不换其他活动。只读检查曾打开已发布早报编辑页，没有保存、提交或修改已发布数据。新活动真实新稿投稿尚未验收。

补充：对已有但尚未提交的release，publish_ready在提交前重新生成上传契约以应用最新固定活动，避免缓存manifest沿用旧活动；submitted/unknown仍由原状态守卫拦截，不能以更新设置绕过防重。固定活动核心11项、隔离Chrome5项、恢复相关8项测试通过；新活动真实新稿提交仍待下一次实际制作。


## 2026-10-27：条数改为纯建议，接入腾讯及Agent产品源

editorial_policy不再因候选多但少选/缺少ai_shortfall_reasons抛错，旧严格配置也不强制补数；实际主片导入的隔离测试确认1条AI可以保留1条，不自动填充。source/config/candidates增加产品维度：Codex Releases RSS、既有Claude Code/Qwen Code/ZCode、WorkBuddy带日期版本更新日志、腾讯混元Hy3官方RSS；OpenAIDevs、claudeai、TencentHunyuan、WorkBuddy_AI已核实账号资料并加入官方小时/期前白名单。WorkBuddy支持已有外部模型不触发新模型临时新闻；HY模型标识加入扫描，严格语义核验保留。

真实隔离采集：Codex RSS10、Claude Code RSS10、WorkBuddy日志85、HY RSS0（有效空源），均零模型API。账号profile读取4项成功；后续时间线验收首项因本地采集器BUSY停止，没有读完四账号最新帖，不删锁/抢占/换渠道。证据在data/source-probes/20261027-product-agents.json。90项完整新闻回归通过，含软条数、实际导入、不混淆产品集成和模型发布、日期拆条；修正旧投稿测试将元数据刷新计作提交的断言，确保真实publish只调用一次。

同步规则、制作skill、V_0手册和DSH交接；本轮未制作/上传视频、未修改模型或既有已发布成品、未修改固定活动默认。


## 2026-10-27：完整导览与负责人归属、顺序及遗漏审核

layout_policy.py导览使用完整主语标题、已核验一句事实和板块总述，通常4卡两列，保留固定开场口播和2秒。leader_editorial.py在主片导入、概览和配音前执行：原帖published绑定、姓名与分钟口播、已核实身份画面、tibo主片单页、reset在公司前/普通发言在公司后、其他负责人最多2页以及逐候选include/skip/defer审核。未知身份不猜职位，reset仍须严格语义核验；无合格材料可跳过，不强制补数。审计文件随release保存。

早报tibo遗漏已查本地证据：03:24原帖、03:27首次入库，05:40期前采集仍接受6条tibo；未在早报editorial入选、未有逐条排除原因，不是X读取失败。最新归档有requires_context=true，不能将采集成功说成上下文已审核可播。证据data/source-probes/20261027-morning-tibo-omission.json。已发布早报SHA256重新核对一致，未重做或重投。

104项新闻回归通过，包含真实隔离SQL→import-editorial→负责人原时间/身份/排序/审计产出，以及原始时间替换错误编辑时间、不伪造缺失分钟、reset语义与页数限制。两套隔离film通过HyperFrames check（ok=true）和真实截图人工检查；新版概览与负责人身份均无重叠或截断。概览整期仍有原进度/来源小字及轨道密度警告，不宣称零警告。预览位于.cache/overview-review-20261027与.cache/leader-review-20261027；后者是静音排版fixture，未完成上下文核验，不是待发布成品。此次未合成新语音、未渲染新MP4、未投稿、未修改共享生产film或模型。V_0文档、Notion与DSH交接同步更新。


## 2026-10-27：固定低音量背景音乐

用户提供《おしんこ》FLAC（94.366667秒），本地复制assets/music/oshinko.flac，配置绑定SHA256。最终要求明确不用播报闪避：音乐全期恒定低增益，循环到timings.duration，仅首尾淡入淡出。audio_mix.py统一供build_film/render_sample使用，原配音保留，混音不再整体二次loudnorm；audio-mix.json/soundtrack.wav随release保存。doctor核对文件/哈希，缺源/不符/无有效配音拒绝混音。原曲排除Git和交接包。

108项新闻回归通过，包含真实FFmpeg短曲循环/缺源/缓存、恒定增益在响句/轻句/静音间不改变、配音时序不变、峰值与间隔限制。真实用户原曲＋既有配音完成100秒循环混音，200ms有效播报窗口最小音量差20.5dB，音乐峰值-46.56dBFS，PCM时长100秒。另生成20秒本地MP4试听并解码通过：.cache/bgm-review-20261027/低音量背景音乐试听_20秒.mp4。此为既有画面的隔离混音样段，未重新制作或投稿早报、未修改已发布成品或模型，不将技术检测称为用户听感确认。制作规则、skill、V_0手册、Notion与DSH指令已同步。


2026-10-27午报应用：用户要求本次音频制作流用于今天午间新闻。当前尚无本日noon工作期次或release；之后import-editorial会为新稿固化background_music_requirement（曲目哈希、00:03循环起点、固定低增益、音量限制），release准备阶段必须验证audio-mix.json与soundtrack.wav、时长和输出哈希相符，不允许缺少BGM或错误循环的新版午报放行。旧已导出稿无此标记时仍可按原流程续传，不重做旧稿。

最终补充验收：109项新闻回归全部通过；采样帧序列确认首遍0秒开始、后续均从3秒开始，真实FFmpeg短曲多次循环、固定增益、缓存、缺源停止与release错误循环拒绝均覆盖。真实100秒混音报告intro_play_count=1、repeat_from_seconds=3、ducking=false，时长100秒。


## 2026-10-27：用户反馈BGM听不到后的修正

根因：最轻200ms窗口把整首音乐额外压低24.57dB，旧峰值仅-46.56dBFS。现改为正常播报窗口中位数参考，不按极轻尾音压整曲；配置参考18dB差、目标-32LUFS、峰值-24dBFS，保持固定增益、无ducking、首遍从头后续3秒。真实100秒新版参考差22.01dB、音乐峰值-24dBFS，比旧试听提高22.56dB；新20秒MP4解码通过。不将此声称为用户听感确认。原曲已稳定复制在assets/music/oshinko.flac，SHA核对，未公开上传原音乐。当前尚无本日noon工作期次/release；新导入午报将固化最新要求。


2026-10-27试听确认：用户已确认“听到了听到了，是我的问题，以后就按这个执行”。采用刚才听到的当前版本，停止继续提高或更改混音：音乐初始目标-32LUFS、正常播报窗口中位数参考差18dB、峰值上限-24dBFS、固定增益且无ducking、首遍从头、后续每轮00:03起播。样段主观可听性已由用户确认；此事实不代表未来每个节目天然通过技术检测，原release检查继续执行。原曲继续保存在assets/music/oshinko.flac，不依赖Downloads。

## 2026-10-27：重点回顾按事件日内去重（确认版）

用户澄清不是只允许早报或一天全局第一主片回顾，而是每条具体事件在当天首次合适主片只展示一次。上午临时事件可午报回顾，晚报不重复；下午另一新事件可晚报首次回顾。important_events读取成功主片日志及release/episode回退，按事件/原始事件键、原item_id或原URL匹配，普通报道也记已用；temporary不消耗主片机会，草稿不提前记，修订不重复计。导入逐事件剔除，导出写锁内再次校验。保留24小时、真实公开临时成品、原始时间与归属的原有门槛。

115项完整新闻回归通过，覆盖早报已用/午晚不重播、上午临时到午报而晚报不重播、下午新事件晚报仍可入选、正常报道不再加同事件回顾、修订/跨日及缺日志release回退。真实本机记录回查：已在早报展示的Terra回顾对noon/night均不再允许；morning同一期修订保留资格。已通知视频制作定时任务会话按澄清规则更新当前未发布午报，并同步重建因删回顾而变化的声音、字幕、时序、导览及导航；没有修改任何已发布视频。
