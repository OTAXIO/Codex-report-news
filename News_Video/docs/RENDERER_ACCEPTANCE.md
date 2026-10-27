# Multiplane 实际验收记录（2026-10-27）

本实现是V_0之后的兼容扩展，V_0历史源码基线不改写。用户在A/B最终v4预览后明确选择B；配置已启用multiplane/graphic，A/editorial与hyperframes/legacy可选择。只影响新建期次，已有计划沿用原后端。技术样片不投稿。

## 实际产物

同一份已归档、已核验新闻和既有配音组成94.81秒历史素材样片；不是重新采集的最新一期。含00导览、AI产品、tibo消息、研究临时消息、社会新闻路线与数字图形、模块承接、单行字幕、导航及原固定BGM。三种方式的soundtrack.wav SHA256完全一致，没有重训练或更换音色。

- A完整：release/previews/renderer-demo-20261027-a-v4/2026_10_27_preview_multiplane_editorial.mp4
- B完整：release/previews/renderer-demo-20261027-b-v4/2026_10_27_preview_multiplane_graphic.mp4
- 旧版同素材：release/previews/renderer-demo-20261027-legacy-v2/2026_10_27_preview_hyperframes_legacy.mp4
- A/B静帧、24秒动态、验收JSON：release/previews/multiplane-20261027-review/

上面release相对工作区根目录D:/Basement/Codex_Video。完整版为1920×1080/30fps、H.264/AAC，实际复用音轨94.81秒、编码长度94.834秒。封面同时生成16:9和4:3。

## 已运行并通过

1. 锁定npm Multiplane0.3.13，Node24.22.1、Chromium153、FFmpeg7.1/libx264的doctor通过；可选three未安装，不影响本次平面新闻。
2. A/B分别实际执行lint、inspect、stills、verify、render，最终NDJSON返回ok。固定舞台、本地资源预加载、同步render(t)及硬切声明通过确定性检查。
3. 实际浏览器逐场景及逐字幕切换检查标题、要点、来源、字幕的边界与重叠；已查看产品页、负责人页、导览、切点、起止帧和封面。
4. 完整MP4解码零错误；六段导航、两大模块高亮、字幕和进度检查通过。新验证器读取布局元数据，不沿用旧硬编码坐标。
5. 左侧黑边及右侧完整64px亮蓝矩形满幅；右下角填满。实际视频边缘抽样要求右侧蓝色覆盖率≥98%，不是仅改预览CSS。
6. 三个后端/模板的隔离release准备、投稿器from-release和validate_meta实际通过；浏览器未启动、未提交平台。正式上传继续复用既有投稿器和去重日志。
7. 本地样片强制preview/diagnostic_hold，并阻止resume-export进入正式发布；样片不消耗新闻事件去重记录。

## 性能与限制

同机1080p、3秒代表镜头：1 worker约9.29秒，2 workers约6.96秒，选择2。最终v4完整A渲染86.073秒/峰值3.12GB，B87.612秒/峰值3.15GB。旧版同素材完整流水线54.35秒；统计阶段不同，不直接声称新引擎更快。

本次未重新执行真实B站投稿，不将离线契约验证当成已发布。无全页3D、景深、颗粒或最高采样；本次没有测试NVENC。上游包、运行时缓存、字体、原音乐、账号及模型不进公开Git；换机需按MULTIPLANE.md准备运行时及合法本地素材。

本地机器报告在.cache/renderer-acceptance-final.json，各期保留render-plan/render-job/check/layout-audit/render-validation/progress-validation。已完成渲染复用必须核对输入与MP4哈希；中断恢复显式--resume-render；回退必须记录实际原因。操作说明见MULTIPLANE.md。

最终默认切换后的完整新闻回归133项通过。投稿器源码/生产/安装副本一致性检查通过，未重新执行真实投稿。
