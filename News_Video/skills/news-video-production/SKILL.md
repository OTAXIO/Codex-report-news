---
name: news-video-production
description: 按当前项目规则采集、核验并制作新闻视频，生成本地语音、单行字幕、双封面与release，调用已授权投稿及回查恢复。
---

# 新闻视频制作

先读工作区AGENTS.md、PROJECT_PROMPT.md，以及[完整规则](../../docs/PRODUCTION_RULES.md)、[工作流](../../docs/WORKFLOW.md)、[状态](../../docs/STATE.md)。按当前规则执行，不从历史样片推断要求。

## 采集与编辑

- 小时巡检只读取tibo、核验reset并回查投稿；社会RSS、公司官方X、其他负责人只在视频制作前读取，每期以既定权限运行news_video.py collect --kind all。
- 主片目标北京时间06/12/18点，05:45/11:45/17:45启动。按日期与时段唯一去重；迁移锁、voice、film、投稿共享资源串行，reset优先。
- 使用[help-me-speech](../help-me-speech/SKILL.md)，核实原始作者、时间、正文与上下文。AI国内3＋国外3只是建议，不凑数不生造；公司、产品与Agent均可入选。
- 使用leader_editorial逐条记录负责人候选真实include/skip/defer原因。tibo主片最多1页；核实reset在公司前，普通发言在公司后社会新闻前；其他人每人最多2页。画面身份、姓名主语、原时间必须准确。
- 主片用important_events保留近24小时已公开临时新闻的重要回顾，单列并明确原时间；不得将回顾冒充新发生。临时稿分别遵循RESET_ALERTS.md / MODEL_ALERTS.md，不混无关消息。

## 制作与检查

- 当前Qwen3-TTS0.6B参考克隆，按Voice_Generate/docs/SPEECH_POLICY.md，不训练或改权重。人工试听不新增授权关卡；实际音频错误须修。
- 00导览采用完整主语标题＋一句事实，通常3—4项两列；只口播“这是本视频的导览。”并留2秒。正文01起；reset默认无导览。
- 白底黑字、#01A1FE边缘点缀，真实logo/配图、单行字幕、来源原时间、两模块与逐条导航。双封面只保留一次大日期，删无关说明和重复小日期。
- HyperFrames check、实际截图、MP4解码及导航通过后先准备带日期和时段的release，公开内容不含内部计划或审核话术。

## 投稿与恢复

- 按[codex-upload](../codex-upload/SKILL.md)与[上传契约](../../docs/CODEX_UPLOAD.md)，从config.json解析生产入口。制作前检查sync_upload_skill.py --check --installed与生产doctor，指纹漂移不能继续用旧副本。
- 默认科技数码、实际News合集、AI生成＋自制原创禁止转载、公开可见；固定明日方舟终末地创作者应援计划，topic_id=1325166、strategy=explicit、fallback=stop，不可用不换其他活动。
- render自动投稿后不得再publish。中断使用render_sample.py <id> --resume-export或upload_bridge.py recover <release>续接；不重配音重渲染，不prepare重置unknown。
- 字段只在同表单有限修复。unknown先回查，安全恢复须有同步字段错误、submit_started=false、成功创作中心回查证据；最多一次恢复。最终提交一次，真实POST code0＋aid/BV才submitted，公开账号/标题核验后才published/finalize。
- diagnostic_hold不上传，已发布不改不重传。失败保留成品并报告真实阻塞。凭据、profile、模型及微软字体不进Git/交接包。
