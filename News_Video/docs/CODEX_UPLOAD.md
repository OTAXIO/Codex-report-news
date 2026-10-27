# 制作成品与 codex-upload 对接

当前制作流程使用项目内 `skills/codex-upload` 的独立投稿器，仓库为 https://github.com/OTAXIO/codex-upload-video 。Chrome 为本次目标；Edge 后续兼容，未作为当前默认。

## 自动链路

制作与事实审核 → 本地语音/封面/单行字幕 → build/check/实际画面复核 → render → MP4 实际校验与已用日志 → release → **自动生成 upload.codex.json** → **codex-upload 设置全部字段、读回并自动提交** → 保存 upload.receipt.json → 平台回查 → 公开发布证据 → finalize 归档清理。

已复用今天的默认设置：科技数码、既有 News 合集（实际 ID 在私有 profile）、AI＋自制原创/禁止转载、双比例封面、相关热门免费活动、代理按内容选择标签、内嵌字幕不另传网页。活动会占一个标签位，默认最多 9 个普通标签；固定标签已锁定而超限时明确报错，不静默丢失。

常规主片由当前 Codex 对话中的定时制作任务选题和生成，2026-10-27 已启用三期调度，首次定时运行尚待验证。reset 临时新闻自动制作与提交仍由现有小时巡检协调，不占三期。

## 成品包契约

- release.json：ready_for_upload、episode_id、edition_slot、video_filename、archive_files 中 MP4 SHA-256。
- episode.json：实际 producer、日期/时段与来源；临时稿另有 alert_id、counts_toward_daily_main_limit=false 和 reset_event_key。
- publication.json：已确认 title、description、tags；新生产期次 `auto_publish=true`。若该包显式 `auto_publish=false`，保留手动发布，不被全局配置覆盖。
- cover-4x3.png / cover-16x9.png：各自比例正确，不互相替代裁剪；script/timings/captions/check/实际成片验证资料沿用原流程。
- upload.codex.json：由 release.prepare 自动生成，路径相对包内 manifest，包含视频/封面哈希、双封面比例、声明、分区、合集、活动策略和标签。

不在生成 manifest 时读取登录态或请求平台；已发布包不能再生成上传计划。`render_sample.py` 默认按配置自动提交，`--no-upload` 仅供明确要求的本地预览/测试；历史样片或禁用发布的包不自动上传。不要为重试而重新渲染或重复录入同一事件。

## 入口

```powershell
python -B uploader_plan.py ../../release/本期目录
python -B upload_bridge.py publish ../../release/本期目录
python -B upload_bridge.py verify ../../release/本期目录
python -B upload_bridge.py pending
```

正常 render 已自动完成 prepare/publish，不再额外手动调用第二次 publish。命令仍有幂等保护。小时巡检运行 pending，检查已提交/未知记录，发现公开发布后才清理工作残留。上传失败保留成品，登录、风控和字段不匹配按真实错误处理，禁止反复重投。

## 状态与认证边界

提交回执不是审核通过。submitted 保存真实 aid/bvid/URL，published 需公开 view 与已绑定账号归属及标题吻合。只有后者或用户明确确认才 finalize；未知提交先 reconcile，不新投一份。

账号、Chrome profile、运行时路径、个人授权和状态账本在根目录 `.codex-upload-private/`，不进 Git 或 DSH ZIP。同机 DSH 可复用此受管认证目录，不从日常浏览器导出 Cookie；换机需重新准备本地登录与路径。全局 skill 和项目内快照均为同一源码版本，制作配置明确指定 CLI 与私有 home。

## 本次验证限度

已验证：真实 Chrome 登录与绑定账号、真实已发布稿件及归属、编辑表单只读核对、News 合集消歧；独立离线浏览器模拟双封面、多选声明、标签、活动、重名合集和自动最终提交；实际 MP4 副本的 release→manifest 契约烟测。

没有可重复用于公开测试的新一期成品；没有上传假样片，也没有重投今天已发布的视频。因此**真实新视频从选择文件到平台最终投稿的完整运行仍未实测**。配置已经接通自动执行；首个新成品必须继续按全部字段读回和真实回执判断成功，不能把离线通过说成平台投稿已通过。


## 2026-10-27 新稿真实自动提交验收

已从 release 正式上传本次用户指定 OpenAI GPT-6.1 Terra 临时新闻，平台 add 回执 code=0，aid=117508761717851，bvid=BV1WLnf6fEgM，提交北京时间03:05。表单读回确认科技数码、News合集9420660、AI生成/自制原创/禁止转载、公开可见、科技猎手免费活动及8个相关标签。双封面以分槽画布像素读回确认保存，不能比较随保存变化的图片URL。新稿空封面入口、Vue渲染时序、自动分类重绘、封面制作等待和折叠可见范围已完成实际兼容。

只有结构化同步字段错误、submit_started=false且经过创作中心回查，才能判定未进入提交并安全恢复；超时、未记录提交标志或submit_started=true继续unknown，不盲目重投。实际最终提交只点击一次并获平台回执。本期submitted不自动等于审核发布，公开状态以后续verify结果为准。


2026-10-27 北京时间03:05 已实际提交并经公开 view 核验发布成功：BV1WLnf6fEgM（aid117508761717851），标题与已绑定账号一致；release/2026_10_27_temporary_023452_f1be03b5b60ff10d0a33。51.27秒，1080p30，单行字幕、双封面、科技数码、News、AI生成＋原创禁止转载、科技猎手活动。已写新闻使用日志，发布后按工作流恢复归档并清理116项可再生残留约25.6MiB。不得再次上传本期。真实新稿自动投稿已验证；Edge未验证，tibo reset整条触发链不据此宣称已实发。


## 2026-10-27 早报故障后的自动投稿约束

- 已授权的正式早午晚/临时新闻，技术质量检查通过后立即投稿；“尚未人工试听/等用户确认音色”不是额外授权关卡，不得因此停在release。明确的音频缺失、时序/解码/内容错误仍必须修复，用户明确要求暂停/审核时以用户指令为准。
- 用旧日志也必须可完成导出：used_news读取时补齐缺失edition_key，兼容无episode_id/video_sha256的来源关联行，不覆盖原JSONL；同片同哈希写日志幂等。日志失败保留MP4，通过render_sample.py <id> --resume-export续接，不重配音/重渲染，不跳过去重记账。
- 已有upload-attempt的release不能重新prepare并把unknown清成ready。resume-export沿用成品与回执，交upload_bridge.py recover <release目录>；已有submitted/reviewing只核验，published直接跳过。
- 封面制作是受支持的窗口：标题、双比例槽与图片输入同时匹配才安全关闭自动打开/残留窗口，随后加载本期定稿封面并像素读回。未知弹窗、认证/验证码仍停止，不盲点完成。
- unknown必须先创作中心回查。只有回查成功、结构化同步字段失败、明确submit_started=false才转failed并保存safe_retry_evidence；仅“没搜到稿件”不足以重试。超时/缺提交标志/已经开始提交保持unknown，不重投。
- 项目recover连接回查与恢复：安全确认的提交前故障最多自动恢复1次，超过上限保留release并报错；不无限循环。pending恢复submitted/reviewing/unknown，以及明确upload_policy=automatic的ready/failed；diagnostic_hold不自动上传。
- 技术检查、成品就绪、提交、公开发布分开记录。最终按钮一次；code0+平台ID才submitted；公开账号/标题一致才published/finalize。不能以口头“继续尝试”替代调用，不能报告无回执的成功。
- 定时目标仍06/12/18；记录实际延迟，不承诺平台审核时刻。失败先修复同一成品，不重做旧片，不因错过目标时间自动取消投稿。

合集恢复补充：News按稳定ID和完整目录次序确认；同一项重复点击可能反选取消。collection只在同表单有界重新选定同一项并读回，不按名字切换另一个同名合集。


## 2026-10-27 最新固定活动

用户指定：之后所有新闻（早/午/晚及临时新闻）固定参与“明日方舟终末地创作者应援计划”，话题ID1325166；替换“科技猎手”，不再按热门度或相关性自动挑其他活动。活动名称依据官方公告，ID来自官方跳转B站活动页https://www.bilibili.com/blackboard/era/hProYF7NSH5CPvi7.html。

默认profile及本机有效profile采用strategy=explicit、精确ID＋名称、fallback=stop。from-release剔除旧科技猎手标签，保留平台活动标签所需容量；未在六个推荐中出现时输入精确活动标签并回车，必须读回平台topic-icon活动标记，普通同名文字标签不算参加成功。不可用/未识别/旧活动未移除时保留release并报错，不改投其他活动。活动奖励或内容资格由平台判断，不把选中话题等同获得奖励。

本要求只用于之后新稿，不修改已发布视频/历史回执；其他分区、News合集、原创/AI生成、标题封面规则保留。
