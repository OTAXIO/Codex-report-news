# 工作流优化记录（2026-10-28）

## 顺序与恢复

`迁移/期次/投稿状态 → 采集与候选索引 → 原文核验及编辑 → 配音和ASR/PCM对齐 → 固定混音 → 双封面和锁定渲染计划 → 视觉构建与真实视频门禁 → release → 已用新闻日志附入release → 投稿契约和上传 → 平台回查 → 已发布归档`

`production_flow.py plan|status [ID]` 只读返回阶段；`advance|resume [ID]` 复用现有脚本，遇编辑/封面简报缺失就停，采集、渲染、导出或投稿每次至多推进一次，避免同故障循环。它不取代语义核验、选题和截图判断，不另建第二份期次状态。旧 `news_video.py`、`build_film.py`、`render_sample.py`、`upload_bridge.py` 入口继续可用。

导出时 `release_manager.prepare(..., create_upload_manifest=False)` 先跑实际时长、音轨、音频内容、导航、画面报告等门禁并准备 release。质量失败不写已用日志。通过后 `used_news.record_export` 按原事件/期次逻辑记账；`attach_used_record` 将记录和哈希加入 release manifest，随后才创建投稿契约并允许自动上传。中断可用 `--resume-export` 幂等恢复；投稿桥在缺记账证明时拒绝提交。已提交/unknown先回查，绝不重置成未投。

release 文件复制中断但尚无回执时，`.prepare-owner.json` 标记本期 ID 和输入文件集合；同一期可续接复制。所有权不符或输入集合变化则停止，不接管未知目录。成功准备后移除标记。隔离测试注入复制失败并在同一期恢复通过。

`upload_bridge.pending` 对每个 release 独立处理；损坏回执或单项回查失败记录 `RELEASE_RECOVERY_ERROR`，继续处理其他稿件。小时简报显式返回 `stopped/reason/retry_after_utc/requires_user_resolution/error_fingerprint` 和待办ID；完整采集报告留本地。同一错误签名由任务说明约束静默，不把登录/冷却/资源忙当无新闻。

视觉构建新增输入指纹：稿件、时间、字幕、声音、配图/logo、配置、渲染模板和相关代码变化时重建本期 shot；渲染中断恢复若输入变化则停止，要求新修订。封面仍独立采用旧Pillow配置；渲染后端和模板继续由原 `render-plan.json` 固定。release/finalize 的文件清单共用 `release_manager.FINAL_NAMES`。

发布后清理只接受本期 `episodes/ID` 和本期明确命名的根目录临时文件；仍先备份并核对清理清单。共享数据库、采集缓存和历史日志不会成为删除目标，因此不再每次对整库历史文件做前后哈希，避免并发采集造成假故障。

## 上下文与候选量

原常规预读 7 份文档共约 73,924 字符（审查时点）；现在常规 `AGENTS.md`、`CURRENT_RUNBOOK.md`、生产 skill 共约 8,550 字符。减少约 88% 的**常规强制阅读字符量**，不是实测Codex计费 token。异常仍查完整规则。两个主片任务 prompt 由约2,2xx字符缩至653/648字符；小时任务约730字符。原 58 条候选的兼容 stdout 约62,966字符；紧凑首12条约3,668字符（不含JSON包装）；完整158,749字节仍保存在本地。分页与全文证据按需读取，不减少实际采集或事实核验。

候选排序只对 GitHub release tag 明示 alpha/beta/nightly/preview 的构建、以 `RT @`/“转发”开头的转载及只有短链而无正文的帖子降低发现优先级，不过滤素材。转载仍可选，但需核验原作者和上下文；短链须展开核实。最终热度仍由人/模型基于观众影响、时效、用途及可靠证据作编辑判断，不能把来源条数或排序当真实平台热度。

## 观看体验边界

用户报告近期多数播放不足100、封面点击率75%、3秒跳出约32%、平均观看不足1分钟；原始分子分母和流量来源未提供。先检查标题/封面承诺的主事件与00首屏、正文兑现时间，避免具体封面事件很晚才讲。现行00提示口播＋2秒及AI→游戏顺序不变。事实先行开场、先游戏后AI只能做 `preview/diagnostic_hold` 的离线实验，用户选定前不得改正式默认。不得以该小样本诊断限流或承诺播放量提升。

真实数据到手后按24/72小时同龄窗口分层比较主片、reset、模型临时稿；记录曝光和点击的分子分母/口径、3秒及30秒留存、平均观看秒数/比例、总时长、模块到达和流量来源。缺失值保持空值；平台无随机A/B时只称观察性比较。一次只变一个主要因素，不重传旧视频、刷量、用无关标签或去掉AI声明。

只读导入入口 `python -B audience_metrics.py 本地CSV`，不写生产数据库。CSV列：`episode_id,edition_type,window_hours,impressions,clicks,reported_ctr_percent,retention_3s_percent,retention_30s_percent,average_watch_seconds,duration_seconds,ai_start_seconds,games_start_seconds,traffic_source`。`edition_type` 用 main/reset/model_temporary；窗口只收24或72小时。曝光和点击缺失时不从用户报告的75%反推分母；计算CTR与平台报告CTR分列保存。当前没有原始后台CSV，不做效果结论。

## 验证与限制

四个已复现问题有隔离回归；又覆盖完整导出/上传顺序、单项异常隔离、视觉输入改变、预发行排序及阶段路由。已配置的 Qwen Python 环境完成新闻项目 157 项测试；系统默认 Python 缺 `librosa`，不能代表完整环境。上传 skill 的契约改动经 17 项 Python＋27 项隔离 Chrome 测试零跳过，并同步源码、生产与安装副本。紧凑候选命令在现有数据库运行，返回58条总量与分页指针。开发过程未真实发布新稿件；新一期开播与B站实际投稿路径仍需下一次生产期次验证，不能以隔离测试冒充实际投稿。
