> 2026-10-29 当前排序：主片00导览后，正文01为真实封面头条，其后为其他核实重大消息、剩余游戏、普通AI及对应负责人。无重大消息优先游戏头条；2＋2不是上限或每类只取1条。统一story_order与lead_event_id，详见docs/GAMES_FIRST.md（docs内文件见GAMES_FIRST.md）。已有任务按原计划，已发布不重做。

# AI＋游戏资讯制作规则与接口（2026-10-28）

这是V_0之后的功能升级，不改写V_0历史源码基线。当前仅06:00早报、18:00晚报开始制作，小时30分只读tibo、处理reset及投稿回查；午报不恢复。已发布稿件不重做、不修改、不重传。默认视频Multiplane B、旧版Pillow双封面、新BGM -29LUFS/-21dBFS/参考差16dB、无ducking及00:03循环、原Qwen3模型与既有活动安排保持。

## 内容结构

主片只有AI动态和游戏资讯。AI继续覆盖热门公司、Agent及正常有信息价值的负责人消息；国内3＋国外3是建议，无上限、不凑数。tibo与其他负责人原排序/页数规则保留，普通发言在AI模块跟随公司；已核实reset是否置顶按importance_review，临时稿独立规则不变。

游戏只含明日方舟及明日方舟：终末地。推荐基础覆盖：明日方舟国服1条、英文国际服（用户所称美服）1条；终末地游戏更新1条、国内外活动1条。2＋2是推荐，不是固定数量或上限，可以更多，也可以少发。更新优先，其次活动；同一事件跨语言、来源、地区同步转述或多页展示不重复计数。不把国际服资料伪称美服独立版本进度。

不重复仍在进行但无新进展的旧活动，不用旧闻填配额。区分发布时间与活动时间、服务器时间与北京时间，未知条件或时间不补造。新片不再采集或导入社会新闻；历史数据、social参数与旧布局留兼容，但sources中社会源disabled，collect all不会读取。游戏源按期前读取，不进入小时监控。

## 已核实官方来源

- 明日方舟国服：https://ak.hypergryph.com/news （Next.js公告数据，原始displayTime秒级时间）。
- 英文国际服：https://arknights.global/news ，其官方网页调用的公开接口 `/api/resource/news/list?index=1&size=30&type=latest`；publishTime为毫秒时间戳，不与秒混淆。
- 终末地国服：https://endfield.hypergryph.com/zh-cn/news 。
- 终末地国际：https://endfield.gryphline.com/en-us/news 。

四个官方页面本次未发现RSS/Atom自动发现声明，不编造RSS地址。使用明确标为official_game_page的适配，不称其为官方RSS。未来有真实官方RSS时可在sources启用，通用RSS适配已支持HTML图片、media/enclosure。

X补充：ArknightsEN由Yostar官方发布公告链接核实；AKEndfield由终末地官方客户端layout脚本中的twitter.com/AKEndfield链接核实。leader_sources记录证据及before_episode_only，不触发模型发布队列。沿用Agent Reach，只读；身份核实不等于本次已成功实读最新推文，登录/验证/限流仍停止。本次游戏官网采集与图片实读通过，X渠道新账号实时读取状态以实际报告为准。

## 数据与制作入口

`news_video.py collect --kind all`刷新AI和游戏官方源及启用X；`--kind games`只读游戏源和游戏X。候选包含game_coverage：arknights_cn/global、endfield_update/event的建议目标/缺口，maximum_items=null、enforce_minimum=false。统计仅代表原始候选，不是已经核验可播素材。

`article <item_id>`核对公告全文与图片，下载相关官方图片到assets/game-news，记录data/articles中的related_images（本地file、source_url、article_url）。源列表卡片brief可能截断，body_complete=false时须读详情，不能只靠brief写稿。游戏图只有与已检查公告关联、image_source_url匹配才可导入。下载图不进公开Git。

同一游戏事件确需多页时沿用同item_id、source_url与event_key，并给每页递增page_number；覆盖统计只计一次，不用多页凑推荐条数。

游戏scene需要：section=游戏资讯、game=arknights/endfield、game_region=cn/global或经核验范围、game_topic=update/event/other，以及原item_id、source_url、published、evidence、selection_reason。图片可用image与image_source_url。game_region记录公告来源地区；终末地不据此推断独立版本进度，页面默认标官方公告，有证据时用scope_label标具体活动地区。activity_start/activity_end未知留空，活动起止及条件作为明确来源的facts/detail写入，不用采集时间替代发布时间。游戏scene必须填写经语义核验的event_key，跨源同事件赋相同event_key；主片导入拒绝重复事件，旧事件仍共用used_news去重。

首次游戏口播按当前位置生成，开场“先来看游戏资讯”，承接“接下来是游戏资讯”，导览保留00和完整主语标题/事实说明，不逐项朗读。导航按实际连续区间显示游戏资讯/AI动态，重大提前消息可有头条组，页面标注游戏与地区。两引擎读取同一模块定义，历史社会导航留读取兼容。

## reset全文与详细播报

normalize_post保存original_text原始换行，队列保存完整正文。draft仍需真实语义核验、准确状态、原时间、精确短quote（仅核验用），但短quote不再代替正文。reset_layout按完整词及中文字分页，逐页original_text_page拼接必须等于original_post_text；另存original-post.json。原文太长可增页，手机可读优先，不压小字或静默截断。

review.narration至少120字符和3个句子，仅作为防止一句话摘要的下限，不能代替时长检查；页面多时需足够的逐页播报。详细播报自动使用短上下文分组，仍按最终PCM恢复既有句间0.4秒/场景0.6秒，不改变模型、音色或语速。说明谁在何时说了什么、planned/ongoing/completed，原文范围/时间/限制缺失就明确未说明，不编造所有用户到账，不添加其他消息或空泛教程。全部页必须同一原帖、同一事件，无概览、正文01起。中文概括与英文原文分开，原文不是强制逐词英语口播。

## 正式MP4必须超过30秒

`production.minimum_duration_exclusive_seconds=30`，生产目标至少31秒。production_policy用实际ffprobe视频流和容器时长的较小值核验，不信timings或人为修改的receipt。正式complete_export在记已用新闻前检查；release.prepare和publish_ready/uploader_plan再次检查。≤30.0秒、无可读视频流或探测失败均不能发布。

不足时修改有来源的说明、原文展示和合理阅读时间，同步配音/字幕/时序/导航/混音，不能靠空白、重复或机械降速凑数。已发布短片不追溯；submitted/unknown先按原状态回查，不因时长规则重投。preview/diagnostic_hold样片不能进入投稿。

## 标签与交付

全部未来正式新闻固定标签“明日方舟”“终末地”，其余按本期事实，合计最多9个普通标签，预留第10个活动名额。prepare写入publication/tags.txt，上传入口再次统一，不能换成近似标签。morning活动1325166、night活动8314、temporary1325166不变，原AI/原创、News合集、双封面读回及未知先回查继续执行。

每期保存game-coverage-audit、来源/配图、原文与混音报告，成片先release再投稿。诊断样片明确历史素材、preview/diagnostic_hold，不生成虚假的当前reset或调用投稿验收。


2026-10-28 用户补充：游戏官方图片提高占比，采用接近右半幅的大图窗口（1080p为880×460），完整保留海报内容不强行裁切；左侧要点与来源独立列，字幕与导航区域留空。图片不压字，三条长要点放不下应分页，不能缩小到难读。只用于新片，已发布不重做。


## 本次实际验收

143项新闻回归通过，含真实30秒MP4拒绝/31秒通过、短片上传前不启动浏览器、建议条数可超过4、来源时间/图片解析、全文无损分页、原句间和场景停顿保持。四个官方游戏来源实采86条原始记录并下载了公告相关图片；不是86条当期可播新闻。新X账号完成官方身份链核验，但未将本轮公开X读取失败说成已经实时验收。投稿器部署检查一致，17项Python和27项隔离Chrome验证记录有效。

诊断AI＋游戏样片使用历史核验素材，50.834秒、1080p/30fps；大图版已做实际截图、DOM边界及确定性检查，完整解码和导航通过。reset诊断首轮长上下文生成异常被对齐检查拦下；同模型短分组重试后语音内容识别通过，最终PCM按原停顿校准、字幕重对齐。未截尾字或伪造对齐/审核结果。两种诊断均preview/diagnostic_hold，不占新闻已用记录、不投稿。最终路径和reset实际渲染状态见本地release/previews及STATE后续记录。


最终成片：AI＋游戏大图样片50.834秒、详细reset全文样片38.467秒，均1080p/30fps、解码零错误，严格preview不投稿。Windows跨运行身份的临时混音权限问题已修复为episode内唯一文件原子写入；旧不可替换缓存保留并明确新修订，不改ACL或系统设置。通过同一混音SHA验证音量/PCM不变。最终143项回归通过，已发布两期SHA与原回执一致。
