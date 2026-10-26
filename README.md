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

所有制作命令在 `News_Video` 中运行。原工作区的项目规则和本地 docs/skills 随目录指引读取；公开仓库不包含这些内部资料或账号状态。

```powershell
Set-Location ./News_Video
$env:PYTHONIOENCODING='utf-8'
$env:PYTHONDONTWRITEBYTECODE='1'
python -B news_video.py doctor
python -B -m unittest discover -p 'test_*.py' -v
```

本机数据库、已用新闻日志、素材、依赖和技能随实际项目迁移，仍可在原有环境中使用。release 和语音/模型/投稿私有目录保持原位。小时巡检使用新的代码目录。

## 换机安装

使用 Python 3.10+，在仓库根目录安装 `requirements-test.txt`；基础制作依赖见 `News_Video/requirements.txt`。Node 渲染依赖使用 package.json 与 pnpm-lock.yaml 安装，HyperFrames 锁定版本为 0.8.196。另需准备 Chrome、FFmpeg/FFprobe、字体和合法可用的 GPT-SoVITS 环境。

config.json 的 workspace_directory 相对于 News_Video；release.directory 可为绝对路径或相对于 News_Video 的路径。voice 中的工具、引擎、模型 profile 和参考音频路径需按本机设置。publisher.private_home 相对于 News_Video，认证始终留在仓库外。独立投稿 CLI 必须另行安装并配置，缺少时 doctor 会报告，不应默认自动投稿可用。

语音直接调用既有 Voice_Generate 工具，并使用外部 GPT-SoVITS 引擎和模型，在本期 episodes 下生成音频。本仓库不再复制 Voice_Generate 源码。GPT-SoVITS 主体来自原上游项目，模型与音频权利按原授权。

仅克隆 Git 不能获得本机运行环境。数据库、去重日志和 reset 基线需另行安全迁移；缺少生产数据库时对应的来源映射测试跳过。历史固定日期脚本不作为实时选题入口，历史稿件不可重新投稿。

## Git 保存范围

提交代码、公开源配置、锁文件和必要测试素材。忽略本机数据、运行依赖、项目技能快照、内部文档、生成视频、模型、字体及所有认证信息。后续直接在这个工作副本编辑、测试和提交，不再使用旧的源码导出脚本。

迁移核验见 VALIDATION.md。未为本次目录整理生成或投稿新视频。
