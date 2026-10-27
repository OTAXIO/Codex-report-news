# 03｜使用手册与常用命令

## 最常见的使用方式

日常在当前已配置的 Codex 项目中提出制作要求。明确日期、时段或临时事件，代理按项目规则完成取源、核验、写稿、本地配音和上传。已有默认发布设置不重复确认；若只要本地样片，应明确说明不要上传。

例如：

```text
按 V_0 当前规则制作今天的午间新闻。刷新 RSS 和 X，加入重要回顾；
先完成检查和 release，再按默认配置自动投稿，不修改旧成品。
```

调试音色时应说“只生成本地配音样例，不生成正式新闻、不记新闻使用日志、不上传”，避免测试误入生产路径。

## 启动前的只读检查

以下命令按本机安装编写。先在 PowerShell 设置变量，再执行需要的命令；不要整段盲目运行所有生产步骤。

```powershell
$projectDir = 'D:/Basement/Codex_Video/Codex-report-news/News_Video'
$taskPython = 'D:/Basement/Miniconda3/python.exe'
$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONDONTWRITEBYTECODE = '1'
Set-Location $projectDir
& $taskPython -B news_video.py doctor
```

本次 doctor 返回的模型、对齐运行时、上传入口及账号绑定文件检查均为 true。doctor 只检查它实现的本地项目条件，不能据此宣称 X 或 B 站登录现在一定有效。

## 从来源到一份新稿

```powershell
& $taskPython -B news_video.py collect --kind ai
& $taskPython -B news_video.py candidates --hours 48
& $taskPython -B news_video.py article '实际候选ID'
```

`collect --kind ai` 会同步刷新全部启用 X 白名单。Agent Reach 需要访问现有运行及浏览器锁目录时，Codex 执行应使用已授权的 require_escalated；这不是让用户关闭 Windows 安全设置。

先读 `data/candidates.json` 中的新事件、已用排除和 `important_recaps`，再写 `data/本期ID-editorial.json`。`48` 是候选补充窗口，优先看真正新鲜的消息，不把两天前消息写成今天首发。

每期至少提供 id、producer、edition_date、edition_slot、title、footer_tag、scenes。每条新闻提供 id、section、title、short_title、facts、narration，以及真实 item_id、source_url、publisher、published、evidence、selection_reason。X 新闻还要有 source_type、author_handle、claim_type 和 attribution_checked；引用或回复按规则补 context_evidence。

```powershell
& $taskPython -B news_video.py import-editorial 'data/实际本期ID-editorial.json'
```

导入会补主片重要回顾、默认概览，并检查来源及重复。导入后仍需准备真实 publication.json 和封面简报，不要用占位稿上传。普通稿 producer 使用允许的真实执行者名，不能把 DSH 执行伪装成 Codex。

## 配音、封面与画面

```powershell
$editionId = '替换为实际新一期ID'
& $taskPython -B news_video.py voice $editionId
& $taskPython -B cover_generator.py $editionId
& $taskPython -B build_film.py $editionId
```

生成封面前，在 `episodes/本期ID/cover.json` 填好主体标题、主信息、突出词、真实图片路径和短小 footnote。subtitle 不再绘制，footnote 不重复日期。图片必须是 assets 下已经核实的素材。

不要同时对不同期次运行 build_film 或 voice。`film/` 是共享当前项目，voice.lock 是并发保护，不是报错后随手删除的垃圾文件。

## 检查和正式导出

```powershell
$taskNode = 'C:/Users/35303/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe'
$taskCli = Join-Path $projectDir 'node_modules/hyperframes/bin/hyperframes.mjs'
$env:HYPERFRAMES_NO_TELEMETRY = '1'
$env:HYPERFRAMES_BROWSER_PATH = 'C:/Program Files/Google/Chrome/Application/chrome.exe'
$env:HYPERFRAMES_FONT_CACHE_DIR = Join-Path $projectDir '.cache/fonts'
& $taskNode $taskCli check (Join-Path $projectDir 'film') --json
```

必须把成功 check 的 JSON 以 UTF-8 保存到本期 check.json，并实际截图检查画面。仅运行上述命令而没有保存结果，不满足 release 的输入要求。

```powershell
& $taskNode $taskCli snapshot (Join-Path $projectDir 'film') --at '1,10' --no-end --describe false --output '实际本期截图目录' --json
```

截图时间必须落在实际视频长度内。检查正文、来源、完整字幕、导航和转场，不只看封面。

```powershell
# 正式生产：会准备 release 并按已授权设置自动上传
& $taskPython -B render_sample.py $editionId

# 本地诊断替代入口：明确禁止该次自动上传
# & $taskPython -B render_sample.py $editionId --no-upload
```

`render_sample.py` 虽然名字保留了 sample，但默认是生产链入口，会写新闻使用日志、准备成品和调用上传。`--no-upload` 也不是完全无副作用的试听；纯样例应走隔离目录或明确的 preview 流程。

## 投稿后只回查，不再重复 publish

```powershell
& $taskPython -B upload_bridge.py pending
```

render 已调用投稿器，正常情况下不要再手动 publish 一遍。pending 会回查 submitted 或 unknown，核对公开账号和标题后才 finalize。

release 包中 upload.codex.json、upload-attempt.json、upload.receipt.json、publication-verified.json 和 release.json 分别提供计划、尝试、提交回执、公开核验与最终状态；缺少某个阶段就按实际缺口判断。

## 小时巡检与紧急稿

```powershell
& $taskPython -B hourly_monitor.py
& $taskPython -B reset_alerts.py pending
& $taskPython -B model_alerts.py pending
```

每小时读取社会 RSS、tibo 和公司官方 X；只建立线索和队列，不在该脚本里直接调用 TTS 或上传。Codex 小时任务再读取待核验条目、写真实 review 并执行后续生产。

两种 draft 的 CLI 参数不同：

```powershell
& $taskPython -B reset_alerts.py draft '实际reset线索ID' --review '实际review.json'
& $taskPython -B model_alerts.py draft '实际模型线索ID' '实际review.json'
```

review 中的核验布尔值只有实际查证后才可设为 true。没有身份、原时间或上下文时先记录缺口，不能为了让命令通过填假审核。忙时保留 drafted/ready_for_upload，先恢复已有任务，不重复创建事件。

## 自动任务时间

| 任务 | 当前启动安排 | 目标 |
| --- | --- | --- |
| 早间 | 每天 05:45 | 06:00 早间新闻 |
| 午间 | 每天 11:45 | 12:00 午间新闻 |
| 晚间 | 每天 17:45 | 18:00 晚间新闻 |
| 小时巡检 | 每小时第 30 分钟 | 缓存来源、处理有效临时消息及投稿回查 |

时间以北京时间的项目要求为准。这些是当前已启用任务的安排，不是承诺一定 15 分钟内完成；本地 GPU、网络、平台审核和代理运行状态会影响完成时间。自动任务需在 Codex 应用/执行宿主中管理，不是 Windows 系统服务，也不是放一个 Python 文件就自动定时。


## 当前补充：AI 选题与投稿部署

AI主片尽量国内3＋国外3，优先24小时未用有效事件；不足则记录实际缺口，回顾单列，合格新闻无上限。candidates.json的ai_coverage提供地区候选；import-editorial生成ai-coverage-audit.json，ai_shortfall_reasons（国内domestic、国外international）可选，不作为条数门槛。Google AI/DeepMind、Kimi、MiniMax的X与官方RSS/网页进入统一采集；具体来源和边界见PRODUCTION_RULES.md。

投稿修复后运行 `python -B sync_upload_skill.py --apply --installed` 统一部署，随后 `--check --installed` 只读验证。配置的implementation_sha256与实际实现不符会在调用浏览器前阻止操作。表单只修失败字段，不重填整张表；已开始提交禁止二次点击。更新不等于未来平台永不变化，隔离回归与真实公开回执分别记录。
