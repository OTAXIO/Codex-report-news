> 后续正式片的48h时效门禁、森空岛非浏览器模式、干员四声和导览主体约束见 [当前政策](News_Video/docs/FRESHNESS_AND_SOURCES.md)。

> 2026-10-29 当前排序：主片00导览后，正文01为真实封面头条，其后为其他核实重大消息、剩余游戏、普通AI及对应负责人。无重大消息优先游戏头条；2＋2不是上限或每类只取1条。统一story_order与lead_event_id，详见docs/GAMES_FIRST.md（docs内文件见GAMES_FIRST.md）。已有任务按原计划，已发布不重做。

# 新闻视频生成项目

本仓库现在也是实际运行目录，代码、修改和 Git 版本保存在同一个位置，不再另存一份源码备份。

```text
工作区/
  Codex-report-news/
    News_Video/         唯一制作代码与本机运行数据
  Voice_Generate/      既有语音工具仓库，通过配置引用
  admin_retrain/       现有模型 profile 和模型
  admin_voice_study/   原语音实验
  release/             成品包，保持原位置
  .codex-upload-private/ 本地认证与投稿账本，不进 Git
```

## 代码入口

| 文件 | 功能 |
| --- | --- |
| `News_Video/news_video.py` | 采集、候选、稿件导入、配音、环境检查 |
| `News_Video/build_film.py` | HTML、单行字幕和导航构建 |
| `News_Video/cover_generator.py` | 本期双比例封面 |
| `News_Video/render_sample.py` | 渲染、成片校验、先准备 release，按配置对接投稿 |
| `News_Video/project_paths.py` | 根据配置定位工作区和成品目录，支持仓库嵌套 |
| `News_Video/episode_paths.py` | 解析工作期次和已归档成品 |
| `News_Video/upload_bridge.py` | 对接现有 codex-upload CLI，区分提交与公开发布 |
| `News_Video/release_manager.py`、`finalize_release.py` | 成品准备与发布确认后的收尾 |
| `News_Video/hourly_monitor.py`、`reset_alerts.py` | 小时采集、临时消息队列和去重 |

## 本机使用

所有制作命令在 `News_Video` 中运行。项目规则、制作手册和所需 skill 快照随仓库维护；先读 News_Video/docs/PRODUCTION_RULES.md 和 WORKFLOW.md。工作区入口及 DSH 提示词的版本快照保存在 workspace-context/；账号状态仍只留本地。

```powershell
Set-Location ./News_Video
$env:PYTHONIOENCODING='utf-8'
$env:PYTHONDONTWRITEBYTECODE='1'
python -B news_video.py doctor
python -B -m unittest discover -p 'test_*.py' -v
```

本机数据库、已用新闻日志、素材、依赖和技能随实际项目迁移，仍可在原有环境中使用。release 和语音/模型/投稿私有目录保持原位。小时巡检使用新的代码目录。

## 换机安装

使用 Python 3.10+，在仓库根目录安装 `requirements-test.txt`；基础制作依赖见 `News_Video/requirements.txt`。Node 渲染依赖使用 package.json 与 pnpm-lock.yaml 安装，HyperFrames 锁定版本为 0.8.196。另需准备 Chrome、FFmpeg/FFprobe、字体及本地 Qwen3-TTS 语音环境。

config.json 的 workspace_directory 相对于 News_Video；release.directory 可为绝对路径或相对于 News_Video 的路径。voice 中的工具、引擎、模型 profile 和参考音频路径需按本机设置。publisher.private_home 相对于 News_Video，认证始终留在仓库外。独立投稿 CLI 必须另行安装并配置，缺少时 doctor 会报告，不应默认自动投稿可用。

语音默认调用相邻 Voice_Generate 仓库的 Qwen3-TTS 0.6B 上下文生成入口，参考音频克隆而非已完成微调；模型、参考音频和运行环境需另行准备。既有 GPT-SoVITS 后端保留回退。本仓库不复制 Voice_Generate 源码，模型与音频权利按原授权。

仅克隆 Git 不能获得本机运行环境。数据库、去重日志和 reset 基线需另行安全迁移；缺少生产数据库时对应的来源映射测试跳过。历史固定日期脚本不作为实时选题入口，历史稿件不可重新投稿。

## Git 保存范围

提交代码、公开源配置、锁文件和必要测试素材。项目手册、制作 skill 与当前投稿 skill 快照纳入版本控制；忽略本机数据库、日志、运行依赖、生成视频、参考音频、模型、字体及所有认证信息。后续直接在这个工作副本编辑、测试和提交，不再使用旧的源码导出脚本。

迁移核验见 VALIDATION.md。未为本次目录整理生成或投稿新视频。


## V_0 当前功能与配套仓库

- 主片目标为北京时间06/12/18点，制作前刷新社会RSS、AI官方来源及全部启用X；小时仅巡检tibo reset和投稿状态。具体最新规则以PRODUCTION_RULES.md为准。
- AI数量与国内外3＋3仅为建议；候选来源覆盖公司、负责人、模型及Codex/Claude Code/WorkBuddy等产品，保留事实、原发布时间和已用新闻去重。
- 完整导览、单行字幕、分段导航、负责人身份/口播主语与原时间、页数和遗漏审计均在导入/构建阶段执行。
- 成品先进入release，再按已确认默认设置调用独立投稿器；unknown先回查，提交与公开发布分开记录。
- [上传skill](https://github.com/OTAXIO/codex-upload-video)：源码权威位置；本仓库skills/codex-upload是经过指纹核对的生产快照。
- [语音项目](https://github.com/OTAXIO/Voice_Generate)：Qwen3-TTS入口、停顿和读音规则，模型/参考音频不随Git分发。

详见[完整手册](News_Video/docs/V_0/README.md)、[生产规则](News_Video/docs/PRODUCTION_RULES.md)、[工作流](News_Video/docs/WORKFLOW.md)、[当前状态](News_Video/docs/STATE.md)。Git中的配置是本机生产示例；换机必须检查路径、授权、登录、模型与去重基线，不能仅克隆后直接投稿。


背景音乐：已接入用户本地《おしんこ》，固定低音量循环到片尾，无播报闪避；预览与MP4共享混音，原曲不进Git。规则和换机准备见[BACKGROUND_MUSIC.md](News_Video/docs/BACKGROUND_MUSIC.md)。


## 可选视频引擎

新增Multiplane的A清爽编辑版和B强图形版，保留HyperFrames旧方式。当前默认与验收状态查config.rendering和[Multiplane手册](News_Video/docs/MULTIPLANE.md)。后端共用现有音频、新闻和发布契约；技术样片不投稿。V_0历史基线保留。
