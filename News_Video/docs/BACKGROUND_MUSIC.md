# 背景音乐使用与验收

默认曲目：用户提供的《おしんこ》。本地配置文件config.json的background_music.enabled=true，file=assets/music/oshinko.flac，循环至视频结束。普通早午晚与temporary共用，无播报时自动降低、无停顿时恢复音量。

SHA256：c23453e509f1f112c50e300b2fabf224a8d4dc70d89567d6f9cfbd4bff014ea2

原始来源：用户附件“おしんこ00108000.flac”，FLAC、48kHz、双声道、94.366667秒。原曲仅本地保留，不随Git/交接ZIP分发；本文件不是原音乐许可证明。换机在上述路径放置相同哈希文件；更换曲目应明确修改配置及来源记录。

## 执行路径

1. 运行doctor核对素材与SHA256，再按原工作流采集、编辑和配音。
2. build_film.py调用ensure_soundtrack，保留纯配音并生成固定低音量混音，Studio的assets/narration.wav实际播放这份混音。
3. render_sample.py复用同一混音输入最终MP4，不再整体loudnorm；缓存通过源哈希、配置、时长及输出哈希检查。
4. release中保留最终视频、soundtrack.wav和audio-mix.json；published仍不可改，缺文件等错误不得绕过。

固定音乐增益由整条节目的最保守有效播报窗口计算一次，不进行实时音量包络或随声音闪避。用户反馈无需播报时降低，禁止擅自重新启用ducking。配音音色、时序及TTS模型不变。

## 检查

运行test_audio_mix：验证响/轻句和停顿中的音乐增益相同、配音时序不变、音乐峰值/间隔符合限制、短曲真实循环至尾、缓存复用、缺源停止及纯音乐新闻拒绝。FFmpeg真实文件测试应执行，不把skip当通过。局部200ms阈值分析用于技术防遮盖，不是人耳可懂度保证；可通过本地试听调整保守固定音量。


## 2026-10-27：固定低音量循环背景音乐

后续制作所有主片和临时新闻使用用户提供的《おしんこ》FLAC作为背景音乐。原文件已复制至本地assets/music/oshinko.flac（94.366667秒），config.background_music记录SHA256与混音参数；不依赖Downloads原文件继续存在。原始音乐及本地来源记录不进入Git或DSH交接ZIP，换机按docs/BACKGROUND_MUSIC.md准备同一文件并验哈希。

用户最终要求：全片使用固定低增益，不随播报或停顿升降，不开启ducking/sidechain；仅整片起止约0.35秒淡入淡出。循环播放到视频结束，严格裁到timings.duration，不因一首结束而提前停音/停片。配音优先，保持音色、语速、句间与概览停顿；不重训、不压尾字。

实现audio_mix.py：配音基准-16 LUFS，音乐初始目标-36 LUFS（不是音量百分比），分析200ms有效播报窗口，必要时把整条音乐统一再降低，使这些窗口音乐RMS至少比配音低20dB，并限制音乐峰值不高于-30dBFS。检测阈值、实测差值与恒定增益写入audio-mix.json；静音间隔不自动抬高音乐。不以数值检测冒充主观听感已获用户确认。

build_film和render_sample共用同一soundtrack.wav；后者不再对混音整体二次loudnorm，避免重新抬高背景。纯配音narration.wav独立保留，release保留soundtrack.wav/audio-mix.json便于复核。doctor检查音乐文件/哈希；启用时素材缺失、哈希不符、无有效配音或混音不达标均报错，不默默换曲或生成只有音乐的新闻。缓存绑定原配音/原曲哈希、时长与参数。resume-export仅续传已有成品，不借本次功能修改已发布或已导出的旧视频。


循环起点补充：首次完整播放原曲；从第二遍开始每次从原音频00:03起播放到曲尾，前3秒只播一次。audio_mix.loop_music按48kHz采样帧拼接，循环体为[3秒,原曲结束)，最后按视频时长裁切，不每轮重新淡入淡出。repeat_from_seconds=3；换曲后偏移超出曲长则报错。固定低音量、无播报闪避不变。


2026-10-27午报应用：用户要求本次音频制作流用于今天午间新闻。当前尚无本日noon工作期次或release；之后import-editorial会为新稿固化background_music_requirement（曲目哈希、00:03循环起点、固定低增益、音量限制），release准备阶段必须验证audio-mix.json与soundtrack.wav、时长和输出哈希相符，不允许缺少BGM或错误循环的新版午报放行。旧已导出稿无此标记时仍可按原流程续传，不重做旧稿。
