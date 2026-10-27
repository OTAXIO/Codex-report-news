# 05｜排错、版本基线与 DSH 交接

## 快速排错表

| 现象 | 先判断什么 | 处理方式 |
| --- | --- | --- |
| LOCAL_PERMISSION_DENIED | 既有运行目录或浏览器锁的本地写权限 | 用已授权 require_escalated 执行同一读取，不改系统安全，不误称 X 故障 |
| NEED_LOGIN / 验证码 / 限流 | 平台是否确实需要人工认证或等待 | 按 Agent Reach 或上传 skill 停止规则处理，不换账号或后端绕过 |
| 某账号返回但没有候选 | 是否超出时间窗口、正文不完整或作者不匹配 | 看 sources 报告和 rejection_reasons；0 候选不等于渠道坏了 |
| 新闻没有进入下一期 | 普通去重、时效还是重要回顾资格 | 看 candidates 的排除原因及 important_recaps，不删除已用日志强行重用 |
| voice.lock / BUSY | 是否真有其他配音或渲染工作 | 保留队列等待，不直接删锁或杀 GPU 进程 |
| 对齐失败 | 文本、采样率、token 数或句界是否匹配 | 查看 voice.log 和 alignment 审计；无可靠静音不盲切活动语音 |
| 普通 Python 缺 librosa | 是否用了错误运行环境 | 使用配置中的对齐 / 科学 Python，不混装推理依赖 |
| 封面编辑器仍制作中 | 是否真实完成异步保存 | 等待保存完成；不能固定睡半秒就判失败或重复点提交 |
| BACKEND_CRASH / 模块路径失效 | 迁移后的 Node、Chrome、Puppeteer 路径是否仍存在 | 用 doctor 和本地运行时配置定位，不重建账号或复制 profile |
| unknown 投稿 | 是否已经有提交迹象 | reconcile / pending 回查，无法唯一确认继续保留 unknown，不二投 |
| 发布完成但工作目录有残留 | 是否已取得公开核验以及文件是否被占用 | 只用 finalize 的本期计划；保留 release、来源、数据库和恢复归档 |

## 先看哪些日志

```text
data/collections/<run>/report.json     这次采集的来源结果
data/hourly-monitor-last.json          最近小时任务摘要
data/leader-collection-state.json      X 冷却、认证或渠道状态
data/reset-alerts/queue/               tibo 待审 / 草稿 / 发布状态
data/model-alerts/queue/               新模型待审 / 草稿 / 发布状态
data/candidates.json                  新候选、排除原因和重要回顾
episodes/<id>/voice.log               配音与对齐运行信息
episodes/<id>/check.json               画面检查结果
logs/news-used/                       已完成新闻与来源关联
release/<edition>/upload-attempt.json  投稿尝试
release/<edition>/upload.receipt.json  真实提交回执
release/<edition>/publication-verified.json 公开核验
```

日志包含业务状态与来源，不应打印或上传 Cookie、账号 profile、API key。上传器私有账本用于防重与回查，不应当作可分享排错附件整包外发。

## V_0 的定义

V_0 是用户给当前代码结构和功能范围命名的项目基线，包含新闻生产、当前本地 Qwen 语音、小时 reset / 新模型通道、重要回顾、封面字幕及自动投稿。它不是 Qwen 模型版本，也不要求把 Python 包或 Node 包的版本字符串改为 V_0。

本地 PROJECT_VERSION.json 记录名称，docs/V_0/SOURCE_BASELINE.json 记录指定源码和配置的 SHA-256。当前三个 Git 仓库存在未提交变更，所以仅凭 HEAD 不能复原完整 V_0；应结合源码指纹、工作树和已生成交接包。

本次命名没有自动创建 Git tag、提交或推送，也没有删除旧模型、重训或重传视频。后续改动可另立 V_1 文档；不要用旧手册声称新实现已经被 V_0 测试覆盖。

## 当前验证到哪一步

| 能力 | 已有证据 | 仍需区分 |
| --- | --- | --- |
| 本地环境 | 本次 news_video doctor 的所有输出检查项通过 | 不等于远程平台当前登录一定有效 |
| 新闻代码 | 上次实现记录 71 项回归通过 | 不等于新真实模型事件已触发过整条生产链 |
| 语音 | 上次实现记录 22 项回归、两句本地合成与对齐烟测通过 | 没有完成 Qwen 微调；自然度和轻声仍需实际试听 |
| 投稿器 | 10 项核心及 4 项含隔离 Chrome 表单测试通过 | 隔离回执不能代替真实提交证据 |
| 真实稿件 | BV1WLnf6fEgM 成功提交，并公开核验账号和标题 | 此次是用户指定模型消息；新小时触发链仍待新的真实事件验证 |
| 自动任务 | 早午晚和小时任务当前均 ACTIVE | 启用不等于每一期已经按时跑通 |
| 旧成品保护 | 上次逐一核对 14 个 release 视频/封面哈希未变 | 不用旧成品做新的上传或编辑回归 |

已公开样例：[OpenAI GPT-6.1 Terra 临时新闻](https://www.bilibili.com/video/BV1WLnf6fEgM)。另有已发布晚间稿 BV1UxnZ6AEVZ，也在防重范围内。两者不应重复上传。

## DSH 接手步骤

1. 先读工作区 PROJECT_PROMPT.md、本版手册、当前 PRODUCTION_RULES.md、WORKFLOW.md 和 STATE.md，确认执行目录和 V_0 边界。
2. 查看 handoff/START_HERE.md 和 DSH_PROMPT.md。交接包包含源码、规则、必要业务状态和部分成品元数据，不包含完整 GPU 环境。
3. 同机优先按配置复用现有 Python、Node、模型、参考音频和受管认证。换机重新安装依赖、下载模型、定位字体，并由用户本人完成平台登录。
4. 为 DSH 配置其自己的执行模型、工具权限及定时机制。不能假设 Codex 应用 heartbeat 会自动跟着 ZIP 迁移。
5. 先跑 doctor、测试和明确禁上传的隔离样例，再核对当前授权、私有 home、账号与 release 路径。
6. 恢复队列和投稿状态时先回查，不能把“本机没有历史文件”当作“外部从未提交”。

常用的交接包生成命令：

```powershell
& $taskPython -B build_handoff.py --date 2026-10-27
```

该日期用于当前版本示例，制作后续版本应写真实记录日期。不要在没有必要时反复重打包。

## 什么不能进入 Notion、Git 或交接包

密码、Cookie、API key、浏览器 profile、私有投稿 home、模型权重和微软字体均不能写入共享手册或交接包。手册中的目录只用于说明位置，不代表要把这些目录上传。

模型、原始音频、数据库、发布账本和已发布成品不是工作垃圾；清理只针对确认可再生的本期残留。任何“恢复失败就删光重来”的操作都不属于 V_0 正常工作流。


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
