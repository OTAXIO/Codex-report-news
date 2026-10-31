# Multiplane 双渲染器与视觉系统

这是V_0之后的兼容扩展，不改写V_0历史源码基线。2026-10-27实际验收通过且用户选定B后，当前默认已切换为Multiplane/graphic；hyperframes/legacy保留。实际默认值查config.rendering，实际某期查render-plan.json。

## 引擎与模板

- multiplane/editorial：A清爽编辑版，白底、大标题、蓝色信息层次、图文或事实图形。
- multiplane/graphic：B强图形版，蓝黑边缘几何、拼贴卡片及更明确的切入，正文保持稳定。
- hyperframes/legacy：旧制作方式，保留原HTML/GSAP和快照＋FFmpeg路径。

新版左边14px黑色、右边64px完整亮蓝矩形贯穿全高，不加白边/白色侧条；右下角也填满，不用斜切缺口。正文仍保留安全阅读边距。底部模块、新闻分段、时钟与连续进度使用独立白底，不让边缘装饰侵入导航。路线和数字图形只使用编辑稿中明确、有source_url的diagram数据，不从标题猜坐标、数字或性能。

## 使用

在News_Video执行：

```powershell
python -B build_film.py EPISODE --renderer multiplane --template editorial
python -B renderer_backends.py check EPISODE
python -B cover_generator.py EPISODE
python -B render_sample.py EPISODE
```

首次不指定引擎/模板时采用配置。当前默认B；想用A，把首次build参数设为--template editorial；旧方式首次build使用--renderer hyperframes。已经生成render-plan.json后不允许换引擎、模板或依赖版本，改用新episode/revision；旧在制期次已有scene-timings而无计划时保留HyperFrames，不因默认切换中途换引擎。两种引擎均输出每期独立visuals目录，不覆盖共享film。

完整技术样片使用--preview，或usage_tracking=false/local_sample标记；这些标记会强制preview并阻止resume-export进入发布。技术样片不写已用新闻日志、不上传。正式稿沿用已有release/自动投稿授权，不加每期人工确认关卡。

中断渲染先查render-job.json及Multiplane作业状态；使用render_sample.py EPISODE --resume-render。上游拒绝续传时保留作业，按具体inputs/environment原因修复或新建修订，不能静默启动重复作业。渲染已成功但应用层质检失败，修好验证后可复用成片重新质检；不会再渲同一片。完成后上传阶段中断仍使用既有--resume-export/recover，unknown先回查。

## 数据与边界

共用episode、timings、单行captions、scene-timings、progress、cover.json、soundtrack与release契约。renderer_backends负责选择、版本锁定、CLI/NDJSON、确定性和布局质检；renderers目录负责新视觉。render_sample负责后端分发、最终解码/导航检查与现有发布衔接，不复制采集、选题或投稿器。

配音仍用原Qwen3-TTS。背景音乐沿用用户确认的固定增益与00:03循环，由audio_mix生成同一soundtrack.wav，三个对照版本的混音SHA一致；新引擎通过--audio加载，不用浏览器audio播放、不二次归一化。素材、字体均本地加载，镜头由同步render(t)驱动，并声明硬切。新封面按原cover.json生成16:9/4:3，保留一次大日期与简短类型说明。

发布门禁保留check/progress-validation、音频审核、混音、去重与未知投稿回查；Multiplane额外要求layout-audit及render-validation。prepare在隔离环境已实际生成包并经投稿器from-release/validate_meta校验，不能把离线契约校验称为真实B站投稿。

## 安装与恢复

锁定npm multiplane 0.3.13；上游main的版本号与实际npm发布曾不同，不能仅按README文字猜版本。先用项目锁文件安装依赖，然后：

```powershell
python -B setup_multiplane.py --install-runtime
python -B setup_multiplane.py
```

脚本只准备项目.cache/playwright与.tools/ffmpeg，不改系统Chrome、旧语音FFmpeg或模型。当前Node需24+。Windows FFmpeg来自imageio-ffmpeg 0.6.0的已核验wheel，保留二进制配套许可/来源；原先语音FFmpeg缺libx264，因而独立配置。Multiplane源码Apache-2.0，官方技能及许可证保存在skills/multiplane。依赖运行时、浏览器、微软字体、原音乐、模型、账号和Cookie不进Git/DSH包，换机按说明准备。

新下载浏览器在此主机的用户缓存启动曾返回spawn UNKNOWN；项目本地PLAYWRIGHT_BROWSERS_PATH实测正常，因此固定使用本地缓存，不关闭系统安全设置、不读取投稿浏览器profile。

## 验收与选择

make_renderer_demo.py基于已有归档和试听素材构建明确标注“历史素材·视觉验收·不投稿”的同源对照。使用--suffix创建新修订，不覆盖已经完成的样片。A/B各提供完整MP4、双封面、静帧及布局/确定性报告，旧版保留同源对照；实际文件链接及性能记录见RENDERER_ACCEPTANCE.md。

doctor、lint、inspect、stills、verify必须真实运行。每幕及每次字幕切换做DOM边界检查，实际MP4检查开始/稳定帧/切点/片尾、左右边缘、六段导航、音视频时长与完整解码。新布局由progress元数据提供坐标，不删除检查适配外观。帧上黑色章节刻度会切开蓝色进度，验证取填充前沿而非像素总数。

同机1080p三秒代表页面：1进程9.29秒，2进程6.96秒，采用2进程；这是项目代表镜头测试，不是上游全场景benchmark。不默认使用3D/景深/颗粒，不为新闻阅读启用全片运动模糊。事实页的静止阅读区不依赖特效提升观感。

明确回退使用新episode/revision，在episode.json中填写rendering_fallback={"from_backend":"multiplane","reason":"实际故障原因"}，首次build指定--renderer hyperframes，render-plan会保留原因。不得改写已固定或已归档期次。


### 临时新闻统一B版（2026-10-27）

后续新建的所有temporary临时新闻（tibo reset及核实的新模型发布）统一采用multiplane/graphic，即B强图形版，与早晚主片一致。首次构建显式使用`python -B build_film.py <id> --renderer multiplane --template persona`并读回render-plan.json；现有config默认已经是B，临时期次复用相同的后端选择逻辑，不另建采集/音频/投稿流水线。右侧64px完整亮蓝矩形贯穿全高、右下角填满，左右无白边，中间白底黑字，单行字幕和临时新闻独立导航。

reset仍只讲该次已核实重置消息，不加00导览、正文01起；新模型临时稿继续遵循MODEL_ALERTS的概览及页数规则。不占早晚主片次数，主片重点回顾仍逐事件日内去重。使用`renderer_backends.py check <id>`及实际截图、最终MP4解码/导航/字幕/边缘检查，质检后先release再按既有授权自动投稿。

B失败先诊断修复，不静默改A或旧引擎；明确回退需新修订并记录真实原因。已有固定render-plan的在制任务沿用原计划。已发布的视频、封面与投稿记录不重做、不修改、不重传；unknown先回查，同原帖/事件防重。小时任务继续每小时30分只读tibo并处理reset/投稿回查，不扩大到公司X或社会RSS。


### 2026-10-28 封面恢复旧版（当前有效）

用户确认后续早报、晚报及临时新闻的封面统一恢复原cover_generator.make_hyperframes/Pillow配置，config.cover_generation.backend=hyperframes、style=legacy；正常调用cover_generator.py <id>即可，不再跟随视频后端自动换用Multiplane封面。视频本体仍是Multiplane B（graphic），render-plan保持不变。旧封面的版式、标题层级、logo处理与双比例输出沿用原实现；真实新闻标题、单次大日期、简短类型说明、双封面及投稿规则照旧。此要求覆盖此前“B版生成双封面”的措辞；B仅指视频画面。只作用于之后新制作的封面，不重做或覆盖已发布封面/视频，不重投旧稿。


### 2026-10-31 P3蓝白版（multiplane/persona，当前默认）

新增可选模板`persona`，参考女神异闻录3的斜切与速度线语言，主色仍为#01A1FE与白色（用户提供参考图实测主蓝#01A1FD），辅以墨黑#101218与深蓝#023077细线。顶部为贯穿全宽的#01A1FE斜切页眉（淡深蓝速度线），下沿一黑一深蓝两道平行斜线；标题黑底白字、蓝色投影；分类与编号都是白色斜切标签配墨黑硬投影，编号为主蓝斜体数字；正文区白底淡蓝斜纹，事实卡片浅蓝交替；字幕白底、两端蓝块；底部导航保留B版白底蓝色高亮。换页时蓝色斜向擦屏在切点前后0.25秒内完成，不影响稳定阅读帧。右侧64px满高蓝块与左侧14px黑边保留。

阅读区坐标、单行字幕、导航采样坐标与B版共用，DOM审计及最终MP4蓝色验收不放宽。编号字体为本机Impact，与微软雅黑一样仅本地复制进期次visuals目录，不进Git/交接包。用户确认样片后设为默认：config.rendering.default_template=persona，新早晚主片与临时新闻均使用；B（graphic）仍可首次构建显式`--template graphic`选择。已有render-plan的在制期次沿用原模板，已发布不重做。用户已逐轮确认静帧样例；隔离样片persona-preview-20261031复用10月31日晚报已发布素材，preview/diagnostic_hold，不写已用新闻、不投稿。

封面同日改为P3蓝白版并设为默认：config.cover_generation.style=persona，仍是cover_generator.py <id>的Pillow路径，与视频render-plan相互独立。#01A1FE底配深蓝速度线；左侧依次为时段白色斜切标签、白色大字主体（墨黑硬投影）、黑底白字headline_main标题条、白底蓝字highlight；右侧为斜放白框配图（墨黑描边与投影）及image_label标签；底部白色斜切色带只放一次大日期（footnote与时段相同则不重复）。16:9与4:3分别排版，cover-bilibili.jpg仍由4:3缩放。cover.json字段、lead_event_id、文字须见于头条的发布校验均不变。`--style legacy`可显式生成旧版；样例见persona-preview-20261031与cover-sample-20261031-morning（后者仅复制早报已发布元数据出封面，不渲染、不投稿）。
