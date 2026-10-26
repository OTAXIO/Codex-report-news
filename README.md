# 新闻视频生成代码

从本地项目整理的视频生成源码备份，保存 2026-10-26 的生成实现、配置、依赖锁文件与回归测试。当前实际运行项目仍保留在原位置。

## 目录

| 路径 | 用途 |
| --- | --- |
| `News_Video/*.py` | 新闻采集、稿件导入、配音调用、封面、字幕、HTML 构建、渲染、校验和 release 管理 |
| `News_Video/config.json` | 原生成参数；包含本机路径，迁移前修改 |
| `News_Video/sources.json`、`leader_sources.json` | 公开新闻源配置 |
| `News_Video/package.json`、`pnpm-lock.yaml` | HyperFrames 渲染依赖 |
| `News_Video/assets/logos/` | 小体积 logo 和公开来源记录，权利归原权利人 |
| `News_Video/episodes/` | 测试所需的四个公开新闻样例 JSON，不是新稿件 |
| `Voice_Generate/tools/` | 直接调用的三个语音工具源码文件 |
| `Voice_Generate/LICENSE` | 原语音工具的上游许可 |
| `SOURCE_MANIFEST.json` | 源文件与备份的 SHA-256、大小和改动说明 |
| `export_news_source.py` | 白名单导出工具，只写新的空目录，不移动或删除原文件 |

## 配音依赖

```text
news_video.py voice <episode>
  -> Voice_Generate/tools/generate_job.py
  -> 外部 GPT-SoVITS 运行时、模型 profile 与参考音频
  -> News_Video/episodes/<episode>/narration.wav
  -> HTML、字幕与视频合成
```

原本机的 Voice_Generate 是一个独立语音工具 Git 仓库，GPT-SoVITS 引擎与模型另存于本地。这里仅保存新闻生成直接调用的工具源码，未复制整个语音仓库或完整 TTS 环境。主体推理引擎来自 [GPT-SoVITS](https://github.com/RVC-Boss/GPT-SoVITS)，这些工具不能替代引擎、模型或其安装步骤。

## 安装与检查

使用 Python 3.10+。在仓库根目录运行：

```powershell
python -m pip install -r requirements-test.txt
Set-Location News_Video
$env:PYTHONIOENCODING='utf-8'
$env:PYTHONDONTWRITEBYTECODE='1'
python -B -m unittest discover -p 'test_*.py' -v
```

基本制作依赖见 `News_Video/requirements.txt`，全部回归额外需要 librosa。系统临时目录受限时，将本进程 TEMP / TMP 指向工作目录内自行创建的临时文件夹。

实际制作还需要 Node、pnpm、HyperFrames（锁文件版本 0.8.196）、Chrome、FFmpeg / FFprobe、中文字体和已有 GPT-SoVITS 环境。安装 Node 依赖后，修改 config.json 中 voice.repository、voice.engine、voice.profile、voice.reference_audio，并检查渲染源码内的 Node、FFmpeg、Chrome 和 Windows 字体路径。

```powershell
# 在 News_Video 内，配置本机资源路径后运行
pnpm install --frozen-lockfile
python -B news_video.py doctor
python -B news_video.py collect --kind ai
python -B news_video.py collect --kind social
python -B news_video.py candidates --hours 48
# 根据来源核验并编写本期 editorial JSON
python -B news_video.py import-editorial <editorial.json>
python -B news_video.py voice <episode>
# 根据本期事实另行填写 episodes/<episode>/cover.json
python -B cover_generator.py <episode>
python -B build_film.py <episode>
# HyperFrames check 和截图检查通过后渲染
python -B render_sample.py <episode>
```

生成程序保留原实现和参数，本仓库不是跨平台即装即用安装包。固定日期脚本仅作为历史代码保存，不能当作实时内容生成器。`build_handoff.py` 需要原生产数据和成品作为输入，此源码备份未提供这些文件。

## 保存范围

保存代码、依赖配置和测试。排除内部项目规则、历史状态、交接文档、技能快照、账号、Cookie、浏览器 profile、API key、模型、参考音频、数据库、运行记录、视频成品、运行时、依赖目录及微软字体。

原生产数据库、已用新闻日志和监测状态仍留在本机；迁移正式制作时需另行保存这些状态，避免重复选题或重发历史消息。

备份副本的 38 项测试中，37 项通过、1 项因缺少原新闻数据库跳过。生成源码与源文件逐项核对，仅测试文件增加数据库缺失时跳过条件。详细范围见 `VALIDATION.md` 和 `SOURCE_MANIFEST.json`。此次未重新生成真实配音、渲染或投稿。
