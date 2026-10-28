# 小时tibo/reset轻量入口

仅在D:/Basement/Codex_Video运行：检查迁移锁，存在静默跳过；在News_Video以既有Python和require_escalated执行hourly_monitor.py --compact及upload_bridge.py pending。每小时30分只读tibo，不采社会RSS、公司、游戏及其他负责人；不调用模型API。无待办/状态变化立即静默，不预读PROJECT_PROMPT、STATE、WORKFLOW、skill、源码或已发布成品。

简报中的 `stopped`、`reason`、`requires_user_resolution`、`retry_after_utc`、`error_fingerprint` 是停止/通知依据，不能把 `sources=[]` 当作正常无新闻。`pending` 逐 release 报告错误；某回执损坏不应掩盖其他投稿回查。同一错误指纹和待办集合未变时静默。完整采集报告只留本地 `data/hourly-monitor-last.json`。

CLI还会本地保存 `data/hourly-monitor-signal.json` 并返回 `changed`/`notification_worthy`；后者为假时不因同一登录/冷却故障再次通知。新警报持续待核时，下一小时 `new_alerts` 清空不造成第二次通知。投稿回查异常单项有稳定指纹，只有故障内容或状态变化时通知。

有needs_review、待制或投稿异常才按需读取RESET_ALERTS.md、AI_GAMES_PRODUCTION.md和对应制作/投稿skill。reset核实原账号、时间、全文与上下文；询问、玩笑、否定或其他重启dismiss，缺证据保留缺口，登录/验证码/限流/BUSY停止，不换渠道绕过。确认有效新事件后按原自动发布授权处理，不重复询问；先查原帖和事件键、在制任务与平台状态，已发布不重做，unknown先回查，资源忙保持队列。

新reset保留原文换行与全部正文，按需分页，中文详细播报不止一句；不添加其他新闻、不承诺所有用户到账。无导览、正文01，不占早晚次数。正式MP4必须>30秒（目标≥31），代码在导出/上传前用真实时长阻止短片；不靠空白/重复/降速凑数。具体B版视频、旧封面、单行字幕、来源时间、BGM-29/-21/16固定无ducking及3秒循环、固定标签明日方舟和终末地、临时活动1325166、release→codex-upload流程按专项文档执行。

渲染已自动投稿不重复publish；最终按钮一次，真实code0+aid/BV才submitted，公开账号/标题一致才published/finalize。未知状态不重投；已发布短片及封面不改。仅新有效reset、成品就绪、发布完成或需用户处理的新故障通知一次，其他静默。禁止外部联系他人及读取/输出/打包凭据、profile、模型或微软字体。
