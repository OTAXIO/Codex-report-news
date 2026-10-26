"""Codex speech edit following help-me-speech; public text only in scenes."""

def revise(ep):
    scenes={s['id']:s for s in ep['scenes']}
    scenes['intro'].update(title='本视频导览',short_title='导览',show_source=False,
        narration='这是本视频的导览。',hold_after_seconds=2.0,
        facts=[dict(title='AI 动态',detail='OpenAI 存储扩展 · Qwen Code 长会话管理 · Claude Code 更新'),
               dict(title='国内新闻',detail='风光装机 · 力箭二号转运 · 居家养老服务'),
               dict(title='国际新闻',detail='大熊猫保护研究合作 · 跨境电力贸易 · 文化展览')])
    scenes['openai-storage']['facts']=scenes['openai-storage']['facts'][:2]
    scenes['openai-storage']['narration']='先看 OpenAI 的存储系统。OpenAI 近期分享了多租户、全球缓存和数据库架构等扩展方案。官方报告存储读取性能提升十二倍，这项指标针对存储系统，不代表模型回答速度。'
    scenes['qwen-code']['narration']='Qwen Code 的近期更新，重点改善长会话管理。绑定工作区的托管会话在空闲时，可以手动压缩上下文，并保留审计历史。工作区恢复会显示原因和可用操作，会话列表也支持按标题筛选。'
    scenes['claude']['facts'][0]['detail']='这是本次 Claude Code 的版本号，主要变化涉及监控工具支持和兼容性修复。'
    scenes['energy']['facts']=[
        dict(title='累计装机达到 20.1 亿千瓦',detail='国家能源局数据显示，统计时间截至 2026 年 9 月底。'),
        dict(title='太阳能 13.1 亿 · 风电 7.0 亿千瓦',detail='风电与太阳能两类发电设备共同构成上述累计装机规模。'),
        dict(title='装机容量与发电量的区别',detail='装机反映设备规模，实际发电量还取决于运行时间与资源条件。')]
    scenes['rocket']['facts'][2]=dict(title='近期择机发射',detail='火箭完成转运后，仍处于发射前准备阶段。')
    scenes['rocket']['narration']='航天方面，力箭二号遥二运载火箭已转运到发射工位，进入发射前准备阶段。后续将开展箭地接口和全流程演练，并于近期择机发射。'
    scenes['elder-care']['facts'][1]['detail']='陪伴、巡检等智能照护产品，正进入上门和社区照护场景。'
    scenes['elder-care']['facts'][2]=dict(title='服务与补贴存在地区差异',detail='各地的服务条件和补贴标准不同，办理时需核对当地规定。')
    scenes['elder-care']['narration']='养老服务方面，一则报道关注了上门照护、社区助餐和智能照护产品的应用。各地的服务条件和补贴标准不同，具体办理仍要核对当地规定。'
    scenes['panda']['facts'][2]=dict(title='当前处于赴比准备阶段',detail='成年雌性大熊猫“冉冉”将赴比延续此前合作项目。')
    scenes['energy']['narration']='接下来是国内外重点新闻，先来看国内的能源消息。国家能源局消息显示，截至九月底，风电和太阳能发电累计装机达到二十点一亿千瓦。这里说的是装机容量，实际发电量还取决于运行时间等条件。'
    for scene in ep['scenes']:
        for field in ('title','short_title','narration','publisher','company'):
            if isinstance(scene.get(field),str):scene[field]=scene[field].replace('Qwen Code','千问编程助手').replace('Qwen','千问')
        for fact in scene['facts']:
            for field in ('title','detail'):fact[field]=fact[field].replace('Qwen Code','千问编程助手').replace('Qwen','千问')
    ep['revision']='Speech revision: one-line guide cue, 2-second silent reading hold, clean news directory, remove production and editorial instructions from public cards.'
    ep['script_workflow']='help-me-speech: existing news brief and audience reused; full script checked for spoken flow, attribution, dates and production-note leakage.'
    return ep
