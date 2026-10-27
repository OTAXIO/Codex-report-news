# 依赖、插件与迁移边界

## 必需

| 能力 | 本机入口 | 迁移说明 |
|---|---|---|
| 普通 Python | D:/Basement/Miniconda3/python.exe | Python 3.10+；numpy、Pillow、requests，requirements.txt 有最低依赖 |
| 本地语音 | D:/others/TOOLS/GPT-SoVITS-v2pro-20250604/runtime/python.exe | 该运行时含 torch/librosa/jieba 等；不要把 site-packages 混入普通 Python |
| 语音 worker | D:/Basement/Codex_Video/Voice_Generate/tools/generate_job.py | 使用现有模型，交接包附工具源码副本；同机优先用原项目 |
| 语音 profile | D:/Basement/Codex_Video/admin_retrain/recommended_profile.json | 本地读取权重路径，不打印凭据；权重不入包、不重训 |
| Node.js | C:/Users/35303/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe | 同机 DSH 可复用；换机重新定位 Node，不依赖 Codex 专属 API |
| HyperFrames CLI | News_Video/node_modules/hyperframes/bin/hyperframes.mjs | 0.8.196 已实测；package.json 与 pnpm-lock.yaml 保留，包不含 node_modules |
| FFmpeg/ffprobe | D:/others/TOOLS/GPT-SoVITS-v2pro-20250604/runtime/ffmpeg.exe、ffprobe.exe | 本机使用 h264_mf；其他编码器/平台先做探测，不把缺 libx264 当作不可渲染 |
| 中文字体 | C:/Windows/Fonts/msyh.ttc、msyhbd.ttc | 构建时在本机读取，不将微软字体打入可迁移 ZIP |
| Chrome | C:/Program Files/Google/Chrome/Application/chrome.exe | HyperFrames 本地截图渲染；不复用浏览器私密 profile |

## Skills

- news-video-production：项目自带的工作流入口，链接需求、步骤、状态和交接说明。
- help-me-speech＋help-me-shared：用户指定的文稿检查；已复制相关本地技能目录，DSH 可显式读取 SKILL.md，不依赖自动发现。
- hyperframes、hyperframes-cli、media-use：HTML 视频、CLI、原始素材/本地语音规则。交接包附本机技能目录快照；实际运行靠 Node CLI，不靠 Codex 私有工具。
- browser-skill：仅在当前环境已安装并连接时使用。当前因本地文件权限需要人工选文件；不能把这个能力假设为 DSH 已有。
- agent-reach 1.6.0：X 只读渠道；CLI C:/Users/35303/.local/bin/agent-reach.exe，已启用 twitter，安装私有 Node 24.22.1 与 OpenCLI 1.8.7。技能快照在 skills/agent-reach，CLI 本体及登录态不入包。DSH 需能调用 CLI 并显式读取该技能；首次读帖结果见 X_SOURCES.md。
- B 站上传第三方能力：见 BILIBILI_UPLOAD_RESEARCH.md。未安装或登录未经核验的上传包，不声称账号自动投稿已通过。

## DSH

本机 DeepSeek Harness.exe 文件存在，ProductVersion 0.2.1.0。没有改动 DSH 的安装、模型、API key 或插件配置。新会话先显式阅读 START_HERE.md 和 DSH_PROMPT.md；是否自动发现 AGENTS.md/skill 由该环境决定。

同机迁移应将工作目录设为 D:/Basement/Codex_Video，直接复用现有外部运行时和模型。换机需要先修改 config.json 中的 voice 路径、源码中的 Node/FFmpeg 路径，准备模型与字体，再运行 doctor 和测试；ZIP 自身不是带完整 GPU 环境的安装包。

交接包不含任何 API key、cookies.json、浏览器登录目录、GitHub 凭据、DSH 用户数据、模型权重、node_modules、旧样片恢复包或 Microsoft 字体。不要为方便运行扫描私人配置提取密钥。

## 已知实现边界

- 社会来源能采集不等于拥有图片/全文转载权；默认自行摘要、适当引用，图片单独保留来源。
- 本地语音模型及参考音频的公开使用权须遵守原有授权；此包不把语音权利默认为新授权。
- 自动采集不等于自动核查；来源失败记录为缺口。部分官方页面是本地 RSS 转换，不伪称官方原生 RSS。
- 三期主片及每小时来源巡检已在当前 Codex 对话启用定时任务；三期首次定时运行尚待验证。未单独配置无人值守选题 API。DSH 自己使用哪个模型及其计费由用户配置，本项目不写入或假设免费额度。

## codex-upload

项目快照 skills/codex-upload，Python 标准库＋Node24＋puppeteer-core25.16.0＋Chrome；复用既有 Node/Chrome/puppeteer 模块。私有运行时与绑定账号在 ../.codex-upload-private，不入 ZIP。当前已通过真实认证和只读平台核验，Edge 尚未验收。


## 2026-10-27 目录统一

唯一运行代码位于 D:/Basement/Codex_Video/Codex-report-news/News_Video，数据库、已用新闻日志、素材、依赖和项目技能随目录迁移。原工作区根目录 News_Video 已停用并移除，不建立旧路径目录链接。release、Voice_Generate、admin_retrain、admin_voice_study、handoff 与 .codex-upload-private 保持原位。所有命令在新的 News_Video 中运行；访问成品使用 ../../release。根目录 AGENTS.md 与 PROJECT_PROMPT.md 继续作为项目规则入口。


## 2026-10-27 Qwen3-TTS 与后台窗口更新

用户已选择 Qwen3-TTS。新闻默认后端现为 config.voice.backend=qwen3，0.6B Base + 现有“帝江号，我已就位，该出发了”参考音频；GPT-SoVITS 原权重、profile 和运行时保留，改 backend=gpt-sovits 可回退。Qwen 接口通过独立 Python 环境和 tools/qwen_generate_job.py，使用逐句映射以保留字幕/导览停顿；Qwen 的 cleanup 强制 off，不做尾字压缩/淡出或机械拉伸语速。旧 GPT-SoVITS speed/cleanup 等参数不是 Qwen 的已实现控制参数，不能混淆。

官方约 2.5GB 权重已下载并逐文件校验 SHA-256；本地克隆样音成功（8.4 秒），新闻入口真实隔离烟测通过逐句输出、2 秒导览停顿和时间映射，无视频生成/上传。安装版本冲突已解决，pip check 通过。自然度与音色仍待用户试听，不能宣称优于旧模型或已完成 Qwen 微调。新方法和训练路线见 VOICE_UPGRADE.md。28 条训练＋4 条验证已导出，尚未训练。

截图命令框属于 Agent Reach 专用 Python 辅助进程。项目采集器现使用 Windows 隐藏启动并仅隐藏标题完全匹配用户 .agent-reach/tools 下 Python 的辅助控制台，不关闭进程，不隐藏 X 登录/验证页面，不影响其他终端。改后真实 tibo 读取成功、reset 无新队列。
