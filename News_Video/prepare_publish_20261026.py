"""Reviewed one-off daily-news edition; no automatic publishing."""
import datetime as dt
import hashlib
import io
from pathlib import Path
from PIL import Image
import news_video as n

ROOT = Path(__file__).parent
EPISODE = 'daily-20261026-evening-v3'

def stored_item(item_id):
    db=n.database()
    try:return dict(db.execute('SELECT * FROM items WHERE id=?',(item_id,)).fetchone())
    finally:db.close()

def prepare():
    ep = n.load(ROOT/'episodes/sample-20261026-v5/episode.json')
    ep.update(id=EPISODE, title='OpenAI 官方报告：存储读取性能提升 12 倍｜10.26 晚间新闻',
              review_status='editorial_checked_pending_platform_review', edition_date='2026-10-26',
              footer_tag='AI 生成 · 晚间新闻',
              revision='Public edition: Qwen replaces Ai2; remove older training-environment item; new narration and daily-news opening.')
    scenes = {s['id']:s for s in ep['scenes']}
    intro = scenes['intro']
    intro.update(section='晚间新闻 · 2026.10.26', title='OpenAI：存储读取提升 12 倍', short_title='今日导览',
                 publisher='本期导览', published='2026-10-26',
                 facts=[dict(title='本期焦点：OpenAI 存储扩展方案', detail='官方工程文章报告读取性能提升 12 倍，指标针对存储系统。'),
                        dict(title='3 条 AI 动态 · 6 条国内外新闻', detail='再看 OpenAI 存储工程、风光装机、航天与跨境合作消息。'),
                        dict(title='新闻保留原始发布日期', detail='本期为 10 月 26 日整理；近期 AI 更新不表述为今天刚刚发布。')],
                 narration='十月二十六日，晚间新闻。OpenAI 报告存储读取性能提升十二倍，这个指标指的是什么。接着看 AI 编程工具更新，以及国内外新闻。')
    row = stored_item('2df989db5683bb988755')
    qwen = dict(id='qwen-code', item_id=row['id'], section='AI 动态', title='Qwen Code：长会话更好管理',
                short_title='Qwen 更新', company='Qwen', logo='assets/logos/qwen.png',
                publisher='Qwen', published=row['published'], source_url=row['url'],
                facts=[dict(title='版本 0.26.1：手动压缩上下文', detail='绑定 Workspace 的托管会话可在空闲时手动压缩上下文，并保留审计历史。'),
                       dict(title='工作区恢复信息更明确', detail='WebShell 展示恢复原因和可用操作，在恢复稳定后再继续处理消息。'),
                       dict(title='会话更方便查找', detail='会话列表支持不区分大小写的标题筛选，WebShell 增加搜索入口。')],
                narration='Qwen Code 的近期版本，重点改善长会话管理。托管会话空闲时，可以手动压缩上下文，并保留审计历史。工作区恢复会显示原因和可用操作，会话列表也支持按标题筛选。',
                selection_reason='本期焦点：热门 AI 编程产品的明确可用性改进；不是新模型发布。',
                evidence=['Official v0.26.1 release: idle-only manual context compression for Workspace-bound Managed Sessions, preserving audit history.',
                          'Official release: managed Workspace recovery shows recovery reasons and valid actions in WebShell; session title filter and WebShell search.'])
    # Keep exact official notes alongside the editorial for future inspection.
    n.dump(ROOT/'data/articles'/f"{row['id']}-rss-evidence.json", row)
    claude = scenes['claude']
    claude['narration']='Claude Code 更新了监控工具支持，覆盖 Bedrock、Vertex 和 Foundry 等平台。新版本还修复部分网关的请求兼容问题，以及后台清理误删近期文件的问题。'
    scenes['openai-storage']['narration']='OpenAI 近期分享了存储扩展方案，涉及多租户、全球缓存和数据库架构。官方报告存储读取性能提升十二倍，这个数字针对存储系统，不代表模型回答速度。'
    culture_row=stored_item('88cb7487bdd1084a7dc4')
    culture=dict(id='tapestry',item_id=culture_row['id'],section='国际 03 / 03',title='千年挂毯展吸引年轻观众',short_title='文化展览',
                 source_url=culture_row['url'],publisher='The Guardian',published=culture_row['published'],
                 facts=[dict(title='贝叶挂毯展览：新一轮门票 3 小时售罄',detail='此前首轮门票在 24 小时内售罄，第二轮售票明显加快。'),
                        dict(title='银行样本中，55% 的买家未满 35 岁',detail='指第二轮售票首小时，Monzo 客户向博物馆付款的人群，并非全部观众。'),
                        dict(title='一项文化消费观察',detail='银行支付数据反映特定样本，不宜推论为所有年轻人的文化偏好。')],
                 narration='英国方面，贝叶挂毯展览新一轮门票在三小时内售罄。卫报援引银行支付数据称，首小时样本买家中，百分之五十五未满三十五岁。这反映特定银行客户的购票情况，并不代表所有观众。',
                 selection_reason='当日文化新闻，补齐国际 3 条；只讨论购票和样本统计，不展示战争图像。',
                 evidence=['Guardian 26 October: second round tickets sold out within three hours.', 'Monzo: 55% of its cardholder buyers in the first hour were under 35; not all museum visitors.'])
    scenes['panda']['section']='国际 01 / 03';scenes['nepal-power']['section']='国际 02 / 03'
    ep['scenes']=[intro,scenes['openai-storage'],qwen,claude]+[scenes[x] for x in ('energy','rocket','elder-care','panda','nepal-power')]+[culture]
    ep['ranking']='Codex editorial selection among collected free sources; no claim of measured global trending rank.'
    from speech_editorial import revise
    ep=revise(ep)
    url='https://avatars.githubusercontent.com/u/141221163?s=512&v=4'
    body, final, _ = n.fetch(url)
    im=Image.open(io.BytesIO(body)); im.verify(); im=Image.open(io.BytesIO(body))
    path=ROOT/'assets/logos/qwen.png'; im.save(path)
    ledger=n.load(ROOT/'assets/logos/sources.json')
    ledger['assets']=[a for a in ledger['assets'] if a['id']!='qwen']+[dict(id='qwen',path=path.as_posix(),source=final,organization='https://github.com/QwenLM',width=im.width,height=im.height,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),usage='Editorial organization identification; no endorsement')]
    n.dump(ROOT/'assets/logos/sources.json',ledger)
    n.dump(ROOT/'data/publish-editorial-20261026.json',ep)
    n.import_editorial(ROOT/'data/publish-editorial-20261026.json')
    directory=ROOT/'episodes'/EPISODE
    description='10 月 26 日晚间新闻：OpenAI 官方工程文章报告存储读取性能提升 12 倍。这个数字针对存储系统，不是模型回答速度。本期还整理千问编程助手、Claude Code 的近期更新，以及国内、国际各 3 条消息。\n\nAI 消息为近期发布，画面保留原始日期；并非全部在今天发布。内容由 AI 辅助整理、AI 配音和生成画面，已对照公开来源核查。字幕已内嵌。\n\n本期来源：\n'+'\n'.join(s['title']+'\n'+s['source_url'] for s in ep['scenes'] if s.get('source_url'))
    n.dump(directory/'publication.json',dict(title=ep['title'],description=description,tags=['晚间新闻','人工智能','千问','Claude','科技资讯'],original=True,ai_generated=True,category_requested='News',manual_upload_authorized=True,auto_publish=False))
    (directory/'description.txt').write_text(description,encoding='utf-8')

if __name__=='__main__': prepare()
