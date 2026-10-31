> 每个新视频页面至少1张相关图片，含00、负责人和reset分页；新闻原图优先，缺图用对应游戏/软件/公司官方图标，本地保存来源与hash；无相关素材先补图，不能空白或用无关图凑数。详见SCENE_IMAGES.md。


后续新正式片按 [48小时、来源与导览规则](FRESHNESS_AND_SOURCES.md) 执行：仅原始发布48h内（临时6h/回顾24h更严），导入/release/首次提交共用门禁；森空岛默认非浏览器模式，暂无验收替代源时记录缺口；干员读gàn yuán，仅TTS词组替换；00标题有公司/产品/游戏或人物主体及具体事件。已发布不改。

> 2026-10-30 当前排序：早报morning默认AI动态→游戏资讯，晚报night默认游戏资讯→AI动态。00导览后正文01仍为真实封面头条，其他核实重大消息随后置顶，再按本期时段排列剩余栏目；无重大消息从该时段首栏目选头条，素材不足可由另一栏目开场。统一story_order与lead_event_id，详见GAMES_FIRST.md。已有任务按固化顺序恢复，已发布不重做。

# 当前执行入口（2026-10-29）

本页只给常规运行所需规则。细节按需查 `PRODUCTION_RULES.md`、`AI_GAMES_PRODUCTION.md`、`WORKFLOW.md`、`RESET_ALERTS.md`、`MODEL_ALERTS.md`、`CODEX_UPLOAD.md`。`STATE.md` 是历史状态记录，不能代替当前规则。已发布作品不重做、不重传。

## 身份、时段与数据

- 工作区 `D:/Basement/Codex_Video`；代码 `Codex-report-news/News_Video`；release、Voice_Generate 和私有上传目录均在工作区根，按 `project_paths.py` / `config.json` 解析。开始先查迁移锁、对应期次/投稿状态及在制 voice/film 锁；未知投稿先回查。
- `production_flow.py status ID` 给本期紧凑阶段；`plan` 同样只读，`advance ID` 运行现有确定性入口直到需要编辑或完成一个渲染/导出/投稿动作，`resume ID` 续接。没有 ID 的 `advance` 只做主片采集和紧凑候选，随后停在人工语义选题。不要把 CLI 阶段推进替代真实来源核验和画面判断。
- 主片北京时间 06:00 morning 早报、18:00 night 晚报开始制作；noon 已停用。每小时30分只读 tibo 的 X 并处理 reset 和投稿回查；不做社会 RSS、公司 X 或其他负责人小时采集。主片前运行 `news_video.py collect --kind all`，刷新官方 AI/游戏来源和已启用 X。
- 主片只含 AI 动态和游戏资讯。AI 国内/国外约 3+3、游戏明日方舟国服/英文国际服与终末地更新/活动约 2+2，都是建议，不是配额。素材有效可更多，不足则少发，不生造。官方网页/RSS优先，X补充；原账号、正文、上下文、原时间及图片来源逐条核实。候选游戏前置且报告保留各类全量ID，不在每类1条处停止；先用 `news_video.py candidates --compact --limit 12 --cursor 0` 分页；完整数据在 `data/candidates.json`。网页用 `article ID --compact` 初读，重要截断段必须读完整归档。采集与去重不调用模型。
- 负责人正常且有价值的发言可用。主片 tibo 最多1页，其他人每人最多2页；reset回顾依语义审核决定头条资格，其余在AI部分；普通负责人在AI部分跟随对应公司。画面核实身份与原分钟时间；口播有姓名主语和具体内容。已公开临时事件在当天**首次合适的主片**按事件回顾一次，放 AI 模块，不重复。临时 reset 全文原样保留并可超过2页，仅讲该事件、无00导览、正文01，不许将关键词当公告或说所有人必定到账。新模型临时稿先按语义核验。

## 定稿、声音与画面

- 用项目 `help-me-speech` 的 news 模式写稿。事实、解释、限制按原来源核对；公司/产品名、数字、多音字按语音政策处理。00 导览用完整主语和一句事实说明，口播仅“这是本视频的导览。”并停2秒；reset 无导览。先完成来源核验和回顾/负责人合并，import-editorial生成统一story_order与新导览，再定稿配音。重大例外须importance_review，publication.json和cover.json均填同一lead_event_id；接口见GAMES_FIRST.md。
- 配音沿用现有 Qwen3 0.6B、音色、语速、读音与句间/场景停顿；本地 ASR 内容核对和最终 PCM 字幕对齐须通过。正式片实际 MP4 时长 >30.0秒，目标≥31秒，不靠空白、重复、降速凑时长。
- 视频默认 Multiplane/persona（2026-10-31 起，P3蓝白版：#01A1FE斜切页眉、白底正文卡片），B（graphic）与旧 HyperFrames 可显式选；每期 render-plan 锁定，不暗中回退。正文黑字、#01A1FE 主色、右侧满高64px蓝块，游戏图可用880×460但不裁主体。单行字幕、来源时间、两模块分段导航和全片进度保留。封面用 Pillow 双比例，2026-10-31 起默认 P3 蓝白版（cover_generation.style=persona，`--style legacy` 可出旧版）；真实最重要新闻作标题主体，日期只出现一次。
- `audio_mix.py` 一次生成 soundtrack.wav：音乐目标-29LUFS、峰值-21dBFS、正常口播中位差≥16dB，恒定增益、无ducking；首遍0秒、以后每轮从3秒播放。模型、音色、原曲、已确认声音参数不在本轮优化中修改。

## 交付、上传与恢复

- 经过实际帧、字幕、导航、解码、音画同步、音轨、封面、真实MP4时长检查后才准备 release。完整质量门禁先于已用新闻日志；有合格 release 后，必须把该期日志记录随包附上，再允许投稿。中断用同一 episode `render_sample.py ID --resume-export` 续接；不能重做已发布片或让 `pending` 把未知状态当草稿。
- 投稿仅从 release，使用现有 `codex-upload`。科技数码、实际 News 合集、自制原创/禁止转载及 AI 生成声明；固定标签“明日方舟”“终末地”，其他标签按事实且排除 Claude 标签。活动 morning 1325166、night 8314、temporary 1325166，精确搜索、不可用就停止，不换热门活动。标题与封面从同一真实 `lead_event_id` 取材；记录封面承诺到正文兑现的时间，头条必须是正文01，早报默认AI→游戏、晚报默认游戏→AI，核实重大消息可置顶。
- 已有自动投稿授权持续有效，试听不是额外审批。最终提交一次；unknown先回查，不盲目二投。返回提交回执才记 submitted，公开账号与标题核验才记 published；确认发布后只清理本期可再生残留。开发样片 `preview/diagnostic_hold` 禁止真实投稿。认证数据、浏览器 profile、模型、原曲和字体不得进公开 Git 或交接包。

## 失败动作与节省上下文

- 无事小时巡检只用 `hourly_monitor.py --compact` 与 `upload_bridge.py pending`；无变化静默。停止原因、下次可运行时间、待办 ID 和证据路径必须在简报可见，不能把登录/限流/BUSY误报为“无新闻”。同一故障签名不重复通知；实质变化才通知。
- 常规主片先读本页和本期状态。只有需要语义判断或发生异常，才读对应完整规则、来源全文、上游渲染文档；不整包加载 `STATE.md`、候选大 JSON、全部历史日志或 3D/浏览器 skill。省上下文不省核验。
- 观看数据：用户报告近期多数作品播放<100、封面点击率75%、3秒跳出约32%、平均观看<1分钟。统计口径/分母未知；先核实封面承诺和早期正文兑现，不推断平台限流或因果。00口播保持；正文执行早报AI优先、晚报游戏优先及已核实重大头条规则，其他开场仅离线实验并待用户选择。

竖版新闻海报按比例自动放大：高宽比>1.35使用随字幕布局扩展的完整图窗口（当前B版742px，旧引擎727px），横图保持大横框，logo不强制拉伸；标题/正文与图分栏，字幕和导航不受遮挡，见SCENE_IMAGES规则。

底部全片进度细条贴视频下边界：1080p时y1072、高8px，新闻导航保持相对布局下移；字幕随导航下移，扩展正文/图片/来源安全区；以progress.json的caption、reading_area_bottom及进度坐标验收。


2026-10-30 原曲恢复：固定BGM从工作区`media-library/music/oshinko.flac`读取（仓库外，config相对路径`../../media-library/music/oshinko.flac`）；原SHA256不变，原曲属于生产源素材，不是缓存。不得随源码清理或同步删除，不进Git/交接包。项目assets/music保留核验副本。
