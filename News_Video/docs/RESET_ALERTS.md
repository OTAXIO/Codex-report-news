> 2026-10-27 最新采集范围：小时巡检只读取 tibo @thsottiaux 并处理 reset、回查投稿；不采集社会 RSS，不读取公司或其他负责人 X。社会 RSS、公司官方 X 和其他负责人仅在视频制作前刷新。每期执行 collect --kind all（社会 RSS + AI 官方来源 + 全部启用 X），不能只复用旧社会缓存。新模型线索在制作阶段采集后按 MODEL_ALERTS 核验，已有授权与去重规则保留。

# 小时推文与 reset 临时新闻

用户最新要求覆盖“负责人仅每期前读取”：所有已启用负责人白名单每小时读取，tibo 最先；社会 RSS 每小时采集，AI 公司官方 RSS 仍只在每期前读取。复用最新小时缓存，临近制作时发现缺口再补读，不每小时全站搜索。优先 Agent Reach 专用 X 渠道，公开 Sotwe 镜像作已授权备用核查，遵循登录/验证/限流停止规则。

## 紧急触发

发现 tibo (@thsottiaux) 发布新的 reset 消息后，优先核查原文及必要上下文；确认他在宣布将进行、正在进行或已完成额度重置时，立即制作并按已有授权优先发布“临时新闻”。不等待 06/12/18 点，不占早、午、晚三次次数。关键词命中只是待核查线索，不能把愿望、玩笑、否定、他人转述、普通服务重启或不明指代当成额度通知。

首次开启会将已缓存推文建立已读基线；初次补读只检查最近 1 小时未见过的推文。后续受 6 小时时效保护，避免电脑长时间离线后把失效重置通知当紧急消息。已读原帖、相同 reset 事件不重复制作；发生实质新重置才另立事件键。正文不明确范围、时间、服务或人群时，不推测为全部账号均已重置。

主片选题日志继续使用。临时新闻的 edition_type/edition_slot 为 temporary，counts_toward_daily_main_limit=false。导出后立即写已用日志，后面的主片不再重复播同一事件；另有实质进展需重新核验。

## 画面和发布

只呈现相关 reset 推文：tibo、原始发布时间、原链接、准确原文摘录和忠实中文概括；可沿用本地配音和单行内嵌字幕。不加导览、不拼 AI 其他公司消息、不拼国内外新闻。白底黑字、亮蓝点缀，底部模块只显示“临时新闻”。标题封面围绕原推文，不能写成“你的额度一定到账”。

制作完成先 release，上传仍按科技数码、News 实际分类/合集、原创＋AI 声明、按内容自动选相关标签和相关热门活动。单独命名示例：

```
release/2026_10_27_temporary_014501_a1b2c3d4e5f60718293a/
  2026_10_27_temporary_014501_a1b2c3d4e5f60718293a_临时新闻.mp4
```

codex-upload 已接入自动提交。发布授权已明确，不重复请求日常授权；render 自动准备 release/manifest 并调用投稿器，成功提交保存实际回执，小时巡检回查 published 后才清理。真实新稿的完整实投仍未实测，不能把离线通过称为平台成功。技术故障保留成品并报告，不谎称发布。临时稿和主片串行使用语音/film，不覆盖在制任务。

## 命令与审核文件

```powershell
python -B hourly_monitor.py
# 手动只测一位负责人，不启动完整小时任务
python -B hourly_monitor.py --leaders-only --handle thsottiaux
python -B reset_alerts.py pending
python -B reset_alerts.py draft <alert-id> --review data/<alert-id>-review.json
# 核查后确认不是通知，说明原因并消除待处理项
python -B reset_alerts.py dismiss <alert-id> --reason '原文为询问，非重置通知'
```

review JSON：producer（实际执行者）、is_reset_announcement=true、context_verified=true、announcement_status（planned/ongoing/completed）、reset_event_key（同一次服务/生效时间的重置共用键）、quote（原文中精确摘录，≤160 字符）、summary（≤90 字符）、narration、title（≤24 字符）、必要的 context_evidence。这些布尔值是实际完成核验后的记录，不能为通过校验随意填写。

draft 生成独立 episode、文稿、publication.json、cover.json。后续复用 voice → cover → build → check/截图 → render → release → 上传工作流；临时稿没有目录导览和栏目转场。render 自动将队列标为 ready_for_upload；发布确认后的 finalize --slot temporary 再标为 published。只有真实发布回执或用户确认才写成功。

小时采集/规则检测没有模型 API 调用；Codex 定时巡检自身会消耗会话额度。电脑与应用需运行，离线不能保证准点或即时发布；轮询发现延迟最多接近 1 小时，再加制作和平台处理时间。

## 本次启用状态

Codex 应用的当前聊天小时巡检已创建并启用，automation ID 为 reset。首次手动验收读取成功，旧缓存 4 条建立基线，10 条返回中 7 条通过入库（3 条新条目），无新的 reset 紧急队列。系统未重复发布今天的旧消息。三期主片的定时制作于 2026-10-27 另行启用，首次定时运行尚待验证；投稿状态以实际平台回执为准。


最新画面规则见 X_PRESENTATION.md：来源原始发布时间尽量精确到分钟（北京时间，不补造）；同一期每位负责人合计最多 2 页画面，非 2 条推文；可合并总结多条消息并附原帖截图或头像。reset 临时稿仍只含相关重置信息，保留核验、时效与去重要求。


## 2026-10-27：重点回顾按事件每天一次（最终澄清）

回顾不是限定只放早报，也不是每天只允许一个主视频包含回顾。每条具体事件在北京时间同一天只在首次合适的主片中报道/回顾一次：凌晨临时新闻可在早报回顾，午晚报不重复；上午新临时新闻可在午报回顾，晚报不重复；下午出现的新事件可在晚报首次回顾。不同新事件各自独立，不因为早报/午报已播过其他事件而禁止后续回顾。

important_events读取同日成功主片导出日志及release中的episode回退记录，按稳定event_key及原始event_key、item_id或规范化原始URL识别同一事件。正常新闻报道与重点回顾均消耗该事件当日主片展示次数；temporary本身不消耗一次主片回顾。只有成功导出/已有成品才记使用，草稿和配音中不提前消耗；同一日期时段的修订沿用原归属，不算新一期。保留原有近24小时、已公开核验temporary、原作者/时间/回顾措辞等条件，不借新规则恢复旧闻或生造新闻。

prepare_main_recaps逐事件决定插入，并移除编辑输入中本日已由其他主片用过的回顾；episode.recap_policy输出once_per_event_per_beijing_date及skipped_event_keys。validate_recap在导入时校验，used_news.record_export在写日志锁内再次逐条验证，防止先前草稿稍后导出造成重复。不同事件或真实实质新进展仍按正常选题与事实核查，不因共用公司/人名被一并排除；相同消息换标题不算新事件。跨日重新按当日记录判断，但仍受24小时时效限制。

已发布视频不改。本期未发布午报按新规则重导入时，若回顾被移除，必须同步重新生成受影响的配音、字幕、时序、导览与导航，不允许只删画面留下旧口播。涉及正在运行的配音/渲染由制作会话安全衔接，不覆盖其共享素材。
