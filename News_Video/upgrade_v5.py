"""Codex-authored richer fact cards; evidence remains linked to the sample."""
import json
from pathlib import Path
import news_video as n
ROOT=Path(__file__).parent
ep=n.load(ROOT/'episodes/sample-20261026-v4/episode.json');ep['id']='sample-20261026-v5'
details={
'intro':('导览',[('本期内容','4 条 AI 动态、3 条国内新闻、2 条国际新闻，逐条查看关键变化。'),('事实与来源','各条消息保留发布机构、原始日期和来源链接。'),('阅读方式','正文补充解释，口播与字幕提炼重点；底部显示逐条新闻进度。')]),
'claude':('Claude 更新',[('版本 2.1.310','本次为 Claude Code 的官方版本更新，具体改动以发布记录为准。'),('新增 Monitor 支持','更新涉及 Bedrock、Vertex、Foundry 等平台上的监控工具与插件监控支持。'),('兼容与清理修复','修复部分网关的请求兼容问题，以及后台清理误删近期文件等问题。')]),
'openai-storage':('存储扩展',[('面向规模化服务的存储方案','官方工程文章介绍多租户、全球缓存与 Azure Cosmos DB 等方案。'),('读取性能：官方报告提升 12 倍','这项指标描述存储读取，不等于模型回答速度提升 12 倍。'),('来源范围','本条依据 OpenAI 官方 RSS 摘要整理；未将其写作独立实测结论。')]),
'openai-training':('训练安全',[('训练与评估环境隔离','官方文章介绍加强前沿模型训练和评估环境隔离的防护方向。'),('离线环境与安全测试','官方摘要提及离线环境及高算力安全测试，不展开攻击操作细节。'),('公开信息的边界','本条只总结公开防护措施，不推断其内部配置或实际防护效果。')]),
'litpivot':('LitPivot',[('围绕文献修订研究构思','Ai2 团队介绍 LitPivot，将研究想法与相关文献证据联系起来。'),('分别检查问题、贡献与评估','工具围绕正在编辑的部分组织文献，并提供带证据的修改建议。'),('最终决定仍由研究者作出','用户可接受、修改或拒绝建议；小样本研究结果不能推广为普遍保证。')]),
'energy':('风光装机',[('累计装机达到 20.1 亿千瓦','统计截至 2026 年 9 月底，其中太阳能 13.1 亿、风电 7.0 亿千瓦。'),('装机容量与发电量是不同指标','装机反映设备规模，实际发电还取决于运行时间与资源条件。'),('保留数据的统计时点','本条为国家能源局发布的数据，经中国新闻网转载，不将存量当成当天新增。')]),
'rocket':('火箭转运',[('力箭二号遥二转至发射工位','报道指出火箭总装、测试已经完成，进入发射前的关键准备阶段。'),('后续还需接口与全流程演练','转运后继续开展箭地接口、全流程演练及发射前准备工作。'),('计划与结果分开表述','消息称将近期择机发射；转运完成不能表述为已经发射成功。')]),
'elder-care':('居家养老',[('上门照护与社区服务','报道以沈阳等地案例，介绍上门照护和社区嵌入式养老服务。'),('智能照护产品进入应用场景','相关产品用于陪伴、巡检等照护场景；不将展示功能写成医疗效果保证。'),('办理条件需要按当地核对','报道中的补贴和服务标准具有地区差异，不推广成全国统一标准。')]),
'panda':('熊猫赴比',[('“冉冉”将参加保护研究合作','根据补充协议，中方向比方增补成年雌性大熊猫，延续合作项目。'),('赴比前准备正在进行','有关单位正在落实饲养管理安排，做好出发前的准备。'),('目前不能写成已经抵达','消息描述的是未来安排；保护研究合作与实际出发、抵达属于不同阶段。')]),
'nepal-power':('跨境电力',[('对印出口约 6.34 亿千瓦时','统计区间为 9 月中旬至 10 月中旬，消息由中新网援引尼泊尔媒体报道。'),('贸易方式包括协议与市场交易','报道援引当地电力局数据，约三分之二通过双边协议出售。'),('对孟加拉国供电恢复','据报道，10 月 23 日晚恢复经印度电网向孟加拉国输电。')]),
}
for s in ep['scenes']:
    short,facts=details[s['id']];s['short_title']=short;s['facts']=[dict(title=a,detail=b) for a,b in facts]
    if s['id']=='claude':s.update(company='Anthropic',logo='assets/logos/anthropic.png')
    elif s['id'].startswith('openai'):s.update(company='OpenAI',logo='assets/logos/openai.png')
    elif s['id']=='litpivot':s.update(company='Ai2',logo='assets/logos/ai2.png')
    if s.get('item_id'):s['evidence'].append('V5 explanatory facts checked against saved article/RSS evidence; distinctions of metric and publication stage are editorial qualifications.')
ep['revision']='Item-level timeline, richer fact cards, official organization logos and word-aware Arabic-number captions.'
n.dump(ROOT/'data/sample-editorial-v5.json',ep);n.import_editorial(ROOT/'data/sample-editorial-v5.json')
cfg=n.config();cfg['voice'].update(speed=1.0,pause=.20,tail_style='natural',soft_release=False)
n.dump(ROOT/'config.json',cfg)
