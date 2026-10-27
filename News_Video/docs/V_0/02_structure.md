# 02｜项目结构、配置与依赖

## 根目录与三个代码仓库

本机工作区为 `D:/Basement/Codex_Video`。这是工作区根，不是一个包含所有内容的单一 Git 仓库。

```text
D:/Basement/Codex_Video/
├─ AGENTS.md                     执行边界
├─ PROJECT_PROMPT.md              当前任务入口
├─ PROJECT_VERSION.json           V_0 版本命名及基线说明
├─ Codex-report-news/             新闻项目 Git 仓库
│  └─ News_Video/                 唯一新闻生产代码目录
│     ├─ config.json             路径、采集、语音、发布与版式设置
│     ├─ sources.json            RSS / 官方网页来源
│     ├─ leader_sources.json     X 身份白名单与优先级
│     ├─ data/                   数据库、正文、采集状态、事件队列
│     ├─ episodes/               各期制作中间产物
│     ├─ film/                   当前可编辑画面，多个任务不能同时覆盖
│     ├─ assets/                 logo、图片、参考音频等
│     ├─ logs/                   新闻使用记录与发布归档记录
│     ├─ skills/                 项目所用技能快照
│     ├─ docs/V_0/               本版手册及源码基线
│     └─ node_modules/           本机依赖，不进入交接包
├─ Voice_Generate/                本地语音 Git 仓库
│  ├─ tools/                     Qwen 入口、对齐、读音和数据工具
│  ├─ tests/                     语音回归
│  ├─ models/                    本机权重，不入 Git/交接包
│  ├─ .venv-qwen3/               本机 Qwen 环境
│  └─ docs/SPEECH_POLICY.md       当前语音规范
├─ codex-upload-video/            上传 skill 源码 Git 仓库
├─ .codex-upload-private/         私有账号、浏览器及投稿账本，不分享
├─ release/                      唯一正式上传来源
├─ handoff/                      DSH 交接资料
├─ admin_retrain/                历史语音项目，非当前主流程
├─ admin_voice_study/            原始语音研究材料，保留
└─ .retired-models/              历史检查点恢复归档，非当前主模型
```

旧根目录 `News_Video` 已停用。遇到历史文档中的旧路径，应以 `project_paths.py` 和当前 config 解析结果为准，不能为了让旧命令工作重新建一个影子项目。

## 新闻代码按职责看

| 模块 | 职责 |
| --- | --- |
| `news_video.py` | doctor、collect、candidates、article、import-editorial、voice 总入口 |
| `leader_sources.py / hourly_monitor.py` | X 有界采集与小时 RSS、reset、模型队列编排 |
| `reset_alerts.py / model_alerts.py` | 线索、语义审核草稿、事件去重及状态 |
| `important_events.py / used_news.py` | 已发布重要回顾、普通新闻使用日志与排除 |
| `pronunciation.py / scene_pauses.py` | 显示稿与配音稿分离、时刻读法及场景留时 |
| `layout_policy.py` | 概览、页码和封面小字约束 |
| `caption_layout.py / progress_overlay.py` | 单行字幕语义切换、新闻分段与模块进度 |
| `cover_generator.py / build_film.py` | 双比例封面与 HTML 事实页 |
| `render_sample.py / verify_progress_video.py` | 成片渲染、真实解码和导航验证 |
| `release_manager.py / upload_bridge.py` | 命名成品包、上传契约、提交与公开回查 |
| `finalize_release.py / build_handoff.py` | 发布后恢复归档、受限清理及 DSH 交接包 |

`make_sample_editorial.py`、`prepare_publish_20261026.py` 等固定日期脚本属于历史样例，不能拿来充当每天的实时选题器。

## 配置从哪里改

| 配置 | 作用 | 修改后注意 |
| --- | --- | --- |
| `sources.json` | RSS / 官方页面列表 | 保留原生 RSS 与网页桥接的类型区别 |
| `leader_sources.json` | 作者身份、公司、优先级与 enabled | 新账号必须核实身份；不要猜 handle |
| `config.x_collection` | 渠道、每账号条数、超时等 | 当前 scope 还由采集代码限制，不能只改文字期待行为变化 |
| `config.reset_alerts / model_alerts` | 启用、时效和授权规则 | 不降低语义核验与同事件去重 |
| `config.editorial` | 厂商顺序、回顾和内容选择偏好 | 主片回顾有独立来源资格校验 |
| `config.voice / voice.qwen3` | 本地后端、环境、模型与停顿 | 不混用旧 GPT-SoVITS 参数 |
| `config.presentation / theme` | 概览、配色及版式偏好 | 部分硬约束位于 layout_policy、cover_generator、build_film |
| `config.release / publisher` | 成品路径、上传 skill 与私有 home | 不把私有目录移动进可分享仓库 |

当前 X 官方白名单来自代码读取：OpenAI、Anthropic、DeepSeek、智谱、千问、MiniMax。MiniMax 当前启用 handle 为 `MiniMax_AI`；历史双下划线记载不再作为当前配置依据。负责人包括 `thsottiaux`、`sama`、`bcherny`。小时范围为 tibo 与 official_x，其余负责人制作前读取。

## 本机运行环境

| 能力 | 当前入口 |
| --- | --- |
| 新闻普通 Python | `D:/Basement/Miniconda3/python.exe` |
| Qwen 推理 Python | `D:/Basement/Codex_Video/Voice_Generate/.venv-qwen3/Scripts/python.exe` |
| 对齐 / 科学依赖 Python | `D:/others/TOOLS/GPT-SoVITS-v2pro-20250604/runtime/python.exe` |
| Qwen 模型 | `Voice_Generate/models/Qwen3-TTS-12Hz-0.6B-Base` |
| 本地对齐模型 | `Voice_Generate/models/fa-zh` |
| Node | `C:/Users/35303/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe` |
| HyperFrames CLI | `News_Video/node_modules/hyperframes/bin/hyperframes.mjs` |
| FFmpeg / ffprobe | `D:/others/TOOLS/GPT-SoVITS-v2pro-20250604/runtime/` |
| Chrome | `C:/Program Files/Google/Chrome/Application/chrome.exe` |

对齐仍复用旧环境里的依赖，不代表使用旧 GPT 音色权重。普通 Python 不含所有 librosa 等科学依赖；不要为消除一个导入错误把不同环境的 site-packages 混在一起。

## 依赖和费用边界

本地模型、对齐、画面编码使用本机资源；RSS 和当前只读渠道没有配置付费 X API。新闻脚本不自动调用付费选题 API。Codex/DSH 的执行模型、账号套餐、网络和电力仍有各自成本。

V_0 不能给出“每个视频固定消耗多少 Codex 额度”：稿件长度、核验量、失败重试和修改次数都会变化，脚本也没有把这些用量统一计量。不能将本地 TTS 免费误解为整个生产流程没有资源消耗。
