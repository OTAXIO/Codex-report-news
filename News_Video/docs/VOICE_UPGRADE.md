# 2026-10-27 语音后端调研与接入

## GitHub 官方源码核查

星标为本次查询时快照，不代表自然度排名。

| 项目 | Stars | 本次判断 |
| --- | ---: | --- |
| RVC-Boss/GPT-SoVITS | 63,806 | 保留现有已训练音色、原权重和运行时，作为回退；增加可选的完整段落上下文生成，不强制改现有分句接口 |
| SWivid/F5-TTS | 15,458 | 流匹配方案，代码 MIT；官方预训练权重 CC-BY-NC，不设为创作激励视频的默认权重 |
| fishaudio/fish-speech | 33,408 | 新架构且有独立社区/研究许可；不直接混入现有 GPT-SoVITS，旗舰体积也不是本机的优先试验 |
| QwenLM/Qwen3-TTS | 14,024 | 用户已选择。官方支持参考音频克隆与单说话人微调；本机 8GB 显存先试 0.6B Base，而非承诺全参数训练一定能放下 |

来源：https://github.com/QwenLM/Qwen3-TTS 、https://github.com/QwenLM/Qwen3-TTS/blob/main/finetuning/README.md 、https://huggingface.co/Qwen/Qwen3-TTS-12Hz-0.6B-Base 、https://github.com/SWivid/F5-TTS 、https://github.com/fishaudio/fish-speech 、https://github.com/RVC-Boss/GPT-SoVITS 。

## 已做的代码改进

- tools/qwen_generate_job.py 独立接入官方 Qwen3TTSModel API：缓存参考音频的提示特征，支持逐句/段落生成，保留全部尾字，不做强压缩/淡出；输出与新闻工程兼容的 WAV、原始 WAV 与 timings 元信息。
- 专用 .venv-qwen3 安装 Qwen 依赖；只读复用本机 PyTorch 运行时，依赖新版本安装在 venv，未改原 GPT-SoVITS 环境。此环境仍依赖本机共享的 CUDA PyTorch，不是可直接拷贝到另一台机器的独立运行包。
- 固定 qwen-tts 0.1.1、transformers 4.57.3、accelerate 1.12.0、gradio 5.49.1，避免最新版 Gradio 与 Transformers 的 Hugging Face Hub 版本要求相冲突。Windows 走 PyTorch SDPA，不要求编译 FlashAttention。
- 模型约 2.5GB，Hugging Face CDN TLS 失败后改从 Qwen 官方 ModelScope 仓库下载，逐文件核对发布清单的字节数和 SHA-256；不读取账号 token，不执行模型仓库的远程代码。
- GPT-SoVITS 工作器新增可选上下文分组与可配置采样；默认仍兼容旧 job，原文件备份在 audit/20261027-prosody。未替换任何已训练权重。

## 训练路线

先同音色、同参考、同文稿比较零样本 Qwen 与现有模型，听清晰度、尾音、语气、漏字、英文品牌；不能用音频时长或 ASR 分数冒充自然度。

工具 prepare_qwen_dataset.py 将现有 32 条对齐数据导出为官方 audio/text/ref_audio JSONL：28 条训练、4 条留出验证，检查文件、哈希与跨分区重复，并固定一段参考音频。数据输出在 experiments/qwen3-20261027/dataset；trained=false，本次尚未执行 Qwen 微调。

现有材料以角色台词为主，数据量小，重训不保证能得到自然新闻语气。优先增加同音色的清晰、完整、自然叙述材料，人工核对逐字标注，保留中英文品牌与数字读法；避免用合成音频回灌成所谓真人训练集。使用官方 finetuning/prepare_data.py 提取音频码，再用 sft_12hz.py 在独立目录训练；batch_size 从 1 做显存探测，不照抄 README 的 32，不覆盖旧模型。8GB 全参数训练是否可行尚未验证；不足则调整方案，不能静默切 CPU 后宣称正常。

新模型技术跑通与用户试听通过是两个状态。试听前不宣称比旧模型更自然；主视频/临时新闻切换要保留 GPT-SoVITS 回退和现有逐句时间映射。账号、权重、环境、音频数据不进入 Git 或交接 ZIP。


## 2026-10-27 最新模型取舍（覆盖 1.7B 试验意向）

用户确认 Qwen3-TTS 更好，若 1.7B 显存不足则放弃，0.6B 已足够。当前继续使用用户认可的 0.6B Base 参考音频克隆，不在 8GB 显存设备强行启动 1.7B 全参数训练；增加轮数不能解决显存不足。1.7B 下载目录已清理，没有 1.7B 训练结果，也没有完成 Qwen 微调。未来训练 0.6B 需先做 24kHz 数据/参考归一化、音频码准备和显存试跑，按验证与试听选模型，不仅增加轮数。

旧 GPT-SoVITS 的 17 个非当前运行依赖检查点已可恢复移至根目录 .retired-models/20261027-gpt-sovits-checkpoints（约 5.30GiB），SHA-256 已验证，原始音频/标注/参考保留；归档没有释放其磁盘占用。原 GPT-SoVITS 外部运行时与历史代码暂保留，不整库删除；历史训练 profile 如引用归档文件需先恢复。更新后的 Voice_Generate/README.md 为当前语音项目入口。


最新发音与听感要求（覆盖旧 ti bo 规则）：tibo 口播读 tī bo，梯一声、啵轻声（短而轻、无独立升降调），中间不停顿；TTS 输入使用“梯啵”，画面/字幕/来源仍保留 tibo。中文替换是发音引导，不是已验证的强制音素接口。语气平稳、克制，避免活泼上扬。整段统一参考音频、采样设置和逐单元种子，重新生成全部语句，不局部拼接不同听感的句子。低采样温度用于减小变化，不能等同于模型原生情绪控制；最终听感仍需试听。


时间口播规范：13点48分 / 13:48 读“十三点四十八分”，48 不逐位读“四八”。仅转换语音稿，画面/字幕保留原有阿拉伯数字；分钟小于10时读“零五”等，整点读“点整”。tibo 目标为梯一声、啵轻声、两音节连读；语气平稳克制，整段统一生成。


用户最新语速要求：在当前基准上仅将说话部分加快约3%（speech_rate=1.03），每句处理后再插入原长停顿，pause仍为0.20秒，不将整段含停顿音频一起加速。FFmpeg atempo保持音高，禁止额外吞尾或压缩句尾。导览2秒静音另按原规则保留。发音目标为梯一声/啵轻声；时间为十三点四十八分，字幕仍用数字。采样设置是稳定性调整，不是已验证的情绪控制，最终听感待试听。


## 当前生效：连贯语音与停顿（2026-10-27 最新）

- 主模型仍为用户认可的 Qwen3-TTS 0.6B Base，未重新训练或替换权重。
- 改为同一条新闻/场景连续生成，再用本地 FunASR 文本对齐和波形低能量句界恢复逐句时间。避免每句话单独重新采样导致的语气变化；字幕仍单行，tibo 与数字的显示稿不改。
- 取消额外 3% 加速，speech_rate=1.0。句间目标静音约 0.40 秒，场景/新闻切换约 0.60 秒；导览后的 2 秒留时仍按场景规则执行。只调整检测到的低能量间隙，不对发音尾字压缩或淡出；找不到可靠间隙就报错，不盲切活动语音。
- 保留发音目标：tibo 为梯一声、啵轻声（语音稿梯啵），13点48分为十三点四十八分，画面和字幕仍用 tibo/数字。
- 正式新闻入口根据 config.voice.qwen3.contextual_generation 调用 Voice_Generate/tools/qwen_generate_context.py；底层单句接口仍为 qwen_generate_job.py。对齐模型在 Voice_Generate/models/fa-zh，Python 在 config 的 alignment_python；只复用旧环境里的本地 ASR 依赖，不读取旧 GPT-SoVITS 音色 profile/权重。新机器需准备运行时及官方对齐模型，模型不进 Git/ZIP。
- 技术验证：18 项语音测试、54 项新闻测试通过；实际正式入口的 3 句隔离烟测通过，包含 2 秒导览留时、逐句时间映射且移除旧 GPT profile/engine 字段仍可运行。新样片为两段新闻上下文、8 句对齐输出；辅助 ASR 为十三点四十八分，识别不能替代轻声/自然度试听。
- 若新流程仍达不到用户听感要求，再训练独立的 0.6B 候选，使用留出验证与同文稿试听选模型，通过后切换 model_path；不直接覆盖可用 Base，不单纯堆轮数。当前尚未执行 Qwen 微调。
