"""This sample's editorial decisions authored by Codex in the current conversation."""
import json
from pathlib import Path
import news_video as n

ROOT=Path(__file__).parent
db=n.database()
def scene(key, item, section, title, lines, narration, reason, evidence):
    row=dict(db.execute('SELECT * FROM items WHERE id=?',(item,)).fetchone())
    return dict(id=key,item_id=item,section=section,title=title,facts=lines,narration=narration,
                source_url=row['url'],publisher=row['publisher'],published=row['published'],
                selection_reason=reason,evidence=evidence)
scenes=[dict(id='intro',section='资讯样片',title='先看事实，再看变化',facts=['AI 动态 · 国内 3 条 · 国际 2 条','采集快照：2026.10.26 北京时间','本地样片 / AI 生成 / 待人工审核'],narration='这是一条本地资讯样片。先看人工智能动态，再看国内外新闻。所有条目都保留来源和日期。')]
scenes.append(scene('claude','97c5df49eed3f0cf21b0','AI 动态','Claude Code 更新',
 ['版本 2.1.310','新增部分平台的 Monitor 支持','修复网关兼容与文件清理问题'],
 'Claude Code 更新到二点一点三一零版本。官方更新记录列出了监控工具支持，以及网关兼容和文件清理等修复。',
 '官方产品版本更新，直接影响开发者使用。',
 ['Official release: Added the Monitor tool and plugin monitors on Bedrock, Vertex, and Foundry', 'Fixed requests failing behind some gateways', 'Fixed background cleanup deleting some recent files']))
scenes.append(scene('openai-storage','ee4c22366ef7e7abd786','AI 动态','OpenAI 分享存储扩展',
 ['官方工程博客 · 10 月 23 日','多租户、全球缓存与 Cosmos DB','读取性能提升：官方报告 12 倍'],
 'OpenAI 发布存储系统扩展的工程文章。官方介绍了多租户和全球缓存等方案，并报告读取性能提升十二倍。这是工程指标，不代表模型回答速度。',
 '官方基础设施技术进展；明确区分系统指标与用户体验。',
 ['OpenAI official RSS description: scaled Habitat with reliable multi-tenancy, global caching, and Azure Cosmos DB to deliver 12× faster reads for ChatGPT. Original page returned 403; facts limited to official RSS description.']))
scenes.append(scene('openai-training','f8c156dba7886826388b','AI 动态','训练环境安全措施',
 ['官方工程博客 · 10 月 23 日','训练与评估环境的隔离','离线环境及安全测试'],
 '同一天，OpenAI 还介绍了训练与评估环境的隔离措施，包括离线环境与安全测试。本条只概述公开的防护方向。',
 '另一项独立的官方更新，非与存储文章重复，不展示攻击细节。',
 ['OpenAI official RSS: strengthened containment for frontier model training and evaluation, including offline environments and high-compute red-teaming. Original page returned 403; summary restricted to official RSS.']))
scenes.append(scene('litpivot','5d794c3788a3a4be0d42','AI 动态','用文献校准研究想法',
 ['Ai2 团队发布 LitPivot','把问题、贡献、评估与文献关联','研究者决定接受、修改或拒绝'],
 'Ai2 团队介绍了研究构思工具 LitPivot。它把问题、贡献和评估方案分别关联到文献，并提供有依据的修改建议。研究者仍然决定是否采用。',
 '团队原文可核验，研究工具具有实际使用价值；不把小样本研究写成普遍结论。',
 ['Ai2 author article on Hugging Face: separates a research idea into its problem, proposed contribution, and evaluation plan.', 'suggests revisions that researchers can accept, edit, or reject.']))
scenes.append(scene('energy','bd990d0d99529dec2927','国内 01 / 03','风光装机突破 20 亿千瓦',
 ['统计时点：2026 年 9 月底','风电 + 太阳能：20.1 亿千瓦','装机容量 ≠ 实际发电量'],
 '国内方面，国家能源局消息显示，截至九月底，风电和太阳能发电累计装机达到二十点一亿千瓦。这里说的是装机容量，不能直接当作实际发电量。',
 '公共关注度、数据规模和时效性较高，原文有明确统计时点。',
 ['原文：截至2026年9月底，风电和太阳能发电累计装机容量达到20.1亿千瓦。']))
scenes.append(scene('rocket','a38f73f764e4ef76f535','国内 02 / 03','力箭二号完成转运',
 ['遥二运载火箭转至发射工位','后续开展接口与全流程演练','处于准备阶段，尚未宣布发射成功'],
 '力箭二号遥二运载火箭已转运到发射工位，进入发射前准备阶段。后续还要进行接口和全流程演练。转运完成并不等于已经发射成功。',
 '航天科技进展，时间明确，避免把计划误写成结果。',
 ['原文：今天(26日)…转运至专属发射工位，进入发射前的关键准备阶段，近期择机发射。', '即将展开箭地接口与全流程演练。']))
scenes.append(scene('elder-care','a9aabf8681e058fe5d82','国内 03 / 03','居家养老服务新场景',
 ['上门照护 · 社区助餐','智能照护产品进入应用场景','各地服务与补贴条件不同'],
 '一则居家养老报道关注了上门照护、社区助餐和智能照护产品的应用。各地的服务条件和补贴标准不同，具体办理仍要核对当地规定。',
 '民生实用性高，避免展示患者、诊疗建议和未经核验的医疗效果。',
 ['原文报道沈阳上门照护服务、社区嵌入式养老服务和智能照护产品应用；不同地区案例不可推广成全国统一标准。']))
scenes.append(scene('panda','abf8163842574b277a1e','国际 01 / 02','大熊猫“冉冉”拟赴比',
 ['延续中比大熊猫保护研究合作','赴比前准备工作进行中','不表述为已抵达'],
 '国际方面，大熊猫冉冉将赴比利时，继续参加大熊猫保护研究合作。目前有关单位正在落实饲养管理安排，开展出发前的准备工作。',
 '跨国生物多样性合作，低风险且适合事实短讯。',
 ['原文：大熊猫“冉冉”…将赴比延续此前合作项目。', '目前…共同落实“冉冉”饲养管理相关安排，做好赴比前的各项准备工作。']))
scenes.append(scene('nepal-power','61dd073256a593c4c378','国际 02 / 02','尼泊尔跨境电力贸易',
 ['报道区间：9 月中旬至 10 月中旬','对印度出口约 6.34 亿千瓦时','报道来源：中国新闻网'],
 '中新网援引尼泊尔媒体报道，九月中旬至十月中旬，尼泊尔对印度出口电力约六点三四亿千瓦时。这是特定统计区间的数据，不是当天的出口量。',
 '跨境能源与民生主题，日期和计量单位可核验；保留转引关系。',
 ['原文：中国新闻网援引尼泊尔《共和报》及尼泊尔电力局数据：今年9月中旬至10月中旬，尼对印出口电力约6.34亿千瓦时。']))
episode=dict(id='sample-20261026-v2',producer='Codex current conversation',title='资讯样片 · 2026.10.26',
 candidate_window_hours=72,ranking='Codex qualitative ranking within collected sources: recency, public relevance, specificity, evidence and safety. Not a measured global trending ranking.',
 review_status='local_sample_pending_human_review',scenes=scenes,
 skipped=[dict(reason='政治、冲突、伤亡、宗教或其他敏感主题，先跳过待人工审核；本期不生成 P2。'),dict(reason='部分来源失败或缺少可信发布时间，不推断其没有新消息。')])
db.close()
n.dump(ROOT/'data/sample-editorial.json',episode)
n.import_editorial(ROOT/'data/sample-editorial.json')
