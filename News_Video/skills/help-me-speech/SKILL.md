---
name: help-me-speech
description: 为项目新闻视频编写来源可核验的中文口播；也保留原有PPT演讲稿模式。
---

# 新闻口播（news 模式）

新闻项目调用本 skill 时使用 news 模式。已确认的风格、受众、时长、读音和停顿由 [当前执行入口](../../docs/CURRENT_RUNBOOK.md)、`episode.json` 与 `Voice_Generate/docs/SPEECH_POLICY.md` 给出，不重复提问，也不读取下方课程 PPT 参考资料。

逐事件从原文和已核实来源写“发生什么→具体事实或用途→适用范围/限制”；保留作者、原发布时间与观点/预告/公告的区别。X 消息的口播须有姓名主语、北京时间原分钟与内容；reset 保留完整原文并忠实解释，不扩大到账范围。导览只口播既定短句；不朗读目录或审查过程。公司和产品命名、数字、多音字按项目语音政策，新闻间自然衔接，句间停顿由现有语音流水线负责。稿件落盘前核对来源和文稿，避免先配音后改事实。

# PPT 演讲稿（ppt 模式）

读[共享边界](../help-me-shared/references/core.md)和[演讲流程](../help-me-shared/references/speech.md)。

1. **先确认风格、目标时长（含硬上限/展示留时）、听众及表达目标。** 已明确的信息复用，只把缺项合并询问；期间可读 PPT、核验资料，不在缺项时定稿。
2. 读全部相关幻灯片、图表、备注和附录，核对版本和页序，不擅自改 PPT。按[个人表达](../help-me-shared/references/writing-voice.md)使用用户授权样本；不可用就依据明确偏好，不声称充分拟合。
3. 确定谁在讲、讲谁、面向谁、以何时间为准；读[身份与时间](../help-me-shared/references/voice-and-time.md)，不把参考作者的“我/我们”、经历和状态移给用户。
4. 明确主线和每页任务，按[段落逻辑](../help-me-shared/references/narrative.md)连起段内、段间与翻页。信息够时直接生成，不额外强加提纲审批；用户要求先看提纲时等待。
5. 按场景和时长写可朗读稿，逐页核对事实/贡献/代词/时间，再查朗读节奏。估时与真实试讲分别记录，不声称未做的实测。

可用[演讲需求表](../help-me-shared/templates/speech-brief.md)与[主体表](../help-me-shared/templates/speaker-map.md)做内部记录，不混入正文。新产物放 work/report 的合理位置，Word/PDF 需要时才用对应工具生成并看实际版式。未经要求不改 PPT、不写 Notion、不发送；submit 等明确指令才压缩。

新闻模式当前排序见 ../../docs/GAMES_FIRST.md：00后正文头条先播，默认游戏→AI，已核实重大消息可提前；模块口播按统一顺序生成。游戏事件充足可多选，不能每类1条截断。

新闻新规则见 [48小时与来源](../../docs/FRESHNESS_AND_SOURCES.md)：原发布时间48h硬门禁、保留临时6h/回顾24h；缺时间不选，旧提醒不刷新；森空岛不自动调用浏览器。导览标题带明确主体和具体事实，不用导航短标签替代，API必须区分OpenAI/GPT、Codex和ChatGPT。干员读gàn yuán（干四声），词组TTS-only，不改汉字字幕。
