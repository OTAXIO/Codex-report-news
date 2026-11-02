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
