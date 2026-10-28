---
name: news-video-production
description: 按当前项目规则采集、核验并制作新闻视频，生成本地语音、单行字幕、双封面与release，调用已授权投稿及回查恢复。
---

# 新闻视频制作

先读工作区AGENTS.md、PROJECT_PROMPT.md，以及[完整规则](../../docs/PRODUCTION_RULES.md)、[工作流](../../docs/WORKFLOW.md)、[状态](../../docs/STATE.md)。按当前规则执行，不从历史样片推断要求。

## 采集与编辑

- 小时巡检只读取tibo、核验reset并回查投稿；社会RSS、公司官方X、其他负责人只在视频制作前读取，每期以既定权限运行news_video.py collect --kind all。
- 主片仅morning早间与night晚间两期，北京时间06:00与18:00开始制作，不提前15分钟；noon午间已取消，不补做。按日期与时段唯一去重；迁移锁、voice、film、投稿共享资源串行，reset优先。
- 使用[help-me-speech](../help-me-speech/SKILL.md)，核实原始作者、时间、正文与上下文。AI国内3＋国外3只是建议，不凑数不生造；公司、产品与Agent均可入选。
- 使用leader_editorial逐条记录负责人候选真实include/skip/defer原因。tibo主片最多1页；核实reset在公司前，普通发言在公司后社会新闻前；其他人每人最多2页。画面身份、姓名主语、原时间必须准确。
- 主片用important_events保留近24小时已公开临时新闻的重要回顾，单列并明确原时间；不得将回顾冒充新发生。临时稿分别遵循RESET_ALERTS.md / MODEL_ALERTS.md，不混无关消息。

## 制作与检查

- 当前Qwen3-TTS0.6B参考克隆，按Voice_Generate/docs/SPEECH_POLICY.md，不训练或改权重。人工试听不新增授权关卡；实际音频错误须修。
- 00导览采用完整主语标题＋一句事实，通常3—4项两列；只口播“这是本视频的导览。”并留2秒。正文01起；reset默认无导览。
- 白底黑字、#01A1FE边缘点缀，真实logo/配图、单行字幕、来源原时间、两模块与逐条导航。双封面只保留一次大日期，删无关说明和重复小日期。
- 按render-plan调用renderer_backends.py check（Multiplane读取../multiplane/SKILL.md，旧后端使用HyperFrames），实际截图、MP4解码及导航通过后先准备带日期和时段的release，公开内容不含内部计划或审核话术。

## 投稿与恢复

- 按[codex-upload](../codex-upload/SKILL.md)与[上传契约](../../docs/CODEX_UPLOAD.md)，从config.json解析生产入口。制作前检查sync_upload_skill.py --check --installed与生产doctor，指纹漂移或缺完整验证证据不能继续投稿；修改投稿器须先经validate.py实际隔离Chrome与Python零跳过验证，再同步部署，见docs/UPLOAD_RELIABILITY.md。
- 默认科技数码、实际News合集、AI生成＋自制原创禁止转载、公开可见；固定明日方舟终末地创作者应援计划，topic_id=1325166、strategy=explicit、fallback=stop，不可用不换其他活动。
- render自动投稿后不得再publish。中断使用render_sample.py <id> --resume-export或upload_bridge.py recover <release>续接；不重配音重渲染，不prepare重置unknown。
- 字段只在同表单有限修复。unknown先回查，安全恢复须有同步字段错误、submit_started=false、成功创作中心回查证据；自动恢复不设固定次数上限，每次必须重新回查。最终提交一次，真实POST code0＋aid/BV才submitted，公开账号/标题核验后才published/finalize。
- diagnostic_hold不上传，已发布不改不重传。失败保留成品并报告真实阻塞。凭据、profile、模型及微软字体不进Git/交接包。


背景音乐当前要求：后续主片/临时新闻使用本地assets/music/oshinko.flac《おしんこ》，全片固定低音量循环到片尾；不用播报ducking，不在停顿时抬高。audio_mix.py统一生成soundtrack.wav供预览和渲染复用，原配音独立保留、实测报告随release。目标音乐显著低于播报，必要时全曲统一降低；原曲不进Git/交接ZIP，缺源或哈希错误停止。详见docs/BACKGROUND_MUSIC.md；既往成品不重做。

背景音乐循环：首遍从头，第二遍起每轮从00:03开始，开头3秒只播放一次；config.background_music.repeat_from_seconds=3。

背景音乐可听性修正：以正常播报窗口中位数定固定增益（参考差18dB、目标-32LUFS、音乐峰值-24dBFS），不再用最弱尾字限制整首导致听不到。仍无ducking、后续从00:03循环；原曲本体位于项目assets/music/oshinko.flac。详见BACKGROUND_MUSIC.md，午报使用此新版。

重点回顾最终规则：按具体事件在北京时间当天主片中只报道/回顾一次，而非全局只准早报回顾。上午新临时新闻可午报首次回顾、晚报不再重复；下午新事件可晚报首次回顾。important_events结合当日主片日志/release识别同事件，temporary不消耗主片名额，草稿不记已用，修订不算新一期；导入和导出日志锁内校验。详见PRODUCTION_RULES.md当前澄清。

新配音必须通过verify_speech_content逐句本地ASR/异常时长/削波核验，再用align_captions按最终PCM时间戳生成单行字幕。release对新标记检查报告及哈希，不能用强制对齐成功或解码成功替代实际音频内容核验。见PRODUCTION_RULES.md音频检查。


2026-10-27 用户最新指令：取消“最多自动恢复一次”限制。安全回查确认未进入最终提交、且故障已修复后可自动恢复，不设固定次数上限；每次重新回查并累计审计次数，未知提交、已提交、登录/验证码/风控仍按原规则停止，不盲目重复上传。原有失败记录和次数保留；同一未修复故障不原样反复重投，诊断后继续修复。此前日志里的次数上限与额外授权要求属于历史状态，不再作为当前阻塞。


## Multiplane视觉扩展

新增可选multiplane/editorial（A清爽编辑版）与multiplane/graphic（B强图形版），实际验收通过，用户选定后新期默认B（multiplane/graphic）；hyperframes/legacy保留。每期render-plan锁定后端/版本/模板；未指定但已在制的旧期保留旧引擎。两侧满幅蓝黑图形，不留白侧条；右侧为贯穿全高的64px完整亮蓝矩形，右下角不得留白或斜切缺口，正文安全边距保留。采集、配音、固定BGM及00:03循环、早晚安排、逐事件回顾去重、release与投稿流程不变。按对应后端使用renderer_backends.py check，技术样片强制preview/diagnostic_hold不投稿；新引擎实际截图、确定性、DOM边界、解码/导航与离线上传契约通过才启用。详情见docs/MULTIPLANE.md和RENDERER_ACCEPTANCE.md。


### 临时新闻统一B版（2026-10-27）

后续新建的所有temporary临时新闻（tibo reset及核实的新模型发布）统一采用multiplane/graphic，即B强图形版，与早晚主片一致。首次构建显式使用`python -B build_film.py <id> --renderer multiplane --template graphic`并读回render-plan.json；现有config默认已经是B，临时期次复用相同的后端选择逻辑，不另建采集/音频/投稿流水线。右侧64px完整亮蓝矩形贯穿全高、右下角填满，左右无白边，中间白底黑字，单行字幕和临时新闻独立导航。

reset仍只讲该次已核实重置消息，不加00导览、正文01起；新模型临时稿继续遵循MODEL_ALERTS的概览及页数规则。不占早晚主片次数，主片重点回顾仍逐事件日内去重。使用`renderer_backends.py check <id>`及实际截图、最终MP4解码/导航/字幕/边缘检查，质检后先release再按既有授权自动投稿。

B失败先诊断修复，不静默改A或旧引擎；明确回退需新修订并记录真实原因。已有固定render-plan的在制任务沿用原计划。已发布的视频、封面与投稿记录不重做、不修改、不重传；unknown先回查，同原帖/事件防重。小时任务继续每小时30分只读tibo并处理reset/投稿回查，不扩大到公司X或社会RSS。


### 2026-10-28 封面恢复旧版（当前有效）

用户确认后续早报、晚报及临时新闻的封面统一恢复原cover_generator.make_hyperframes/Pillow配置，config.cover_generation.backend=hyperframes、style=legacy；正常调用cover_generator.py <id>即可，不再跟随视频后端自动换用Multiplane封面。视频本体仍是Multiplane B（graphic），render-plan保持不变。旧封面的版式、标题层级、logo处理与双比例输出沿用原实现；真实新闻标题、单次大日期、简短类型说明、双封面及投稿规则照旧。此要求覆盖此前“B版生成双封面”的措辞；B仅指视频画面。只作用于之后新制作的封面，不重做或覆盖已发布封面/视频，不重投旧稿。
