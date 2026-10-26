"""User-requested vendor focus; this never calls a model or uploads."""
import news_video as n
from pathlib import Path
ROOT=Path(__file__).parent
cfg=n.config()
cfg['editorial'].update(preferred_vendors=['OpenAI','Anthropic','DeepSeek','Qwen','Z.ai'],secondary_vendors=['MiniMax','Google','Meta','Mistral'],research_sources_policy='review_only_for_major_broad_impact_updates; ordinary paper/tool posts are supplementary',preferred_topics=['model releases','consumer and developer product updates','availability and pricing changes','practical workflow changes'],ai_item_limit=None)
n.dump(ROOT/'config.json',cfg)
sources=n.load(ROOT/'sources.json')
extra=[dict(id='qwen-code-releases',name='Qwen Code Releases',group='ai',publisher='Qwen',vendor='Qwen',url='https://github.com/QwenLM/qwen-code/releases.atom',type='rss'),dict(id='glm-zcode',name='Z.ai ZCode Changelog',group='ai',publisher='Z.ai',vendor='Z.ai',url='https://zcode.z.ai/en/changelog',type='official_page')]
for source in extra:
    if not any(s['id']==source['id'] for s in sources):sources.append(source)
vendors={'openai':'OpenAI','claude-code':'Anthropic','anthropic':'Anthropic','deepseek':'DeepSeek','minimax':'MiniMax','deepmind':'Google','huggingface':'Hugging Face','qwen-code-releases':'Qwen','glm-zcode':'Z.ai'}
for source in sources:
    if source['group']!='ai':continue
    vendor=vendors.get(source['id'],source['publisher']);source['vendor']=vendor
    source['priority_tier']=1 if vendor in cfg['editorial']['preferred_vendors'] else (3 if vendor=='Hugging Face' else 2)
    source['selection_policy']='supplementary_research_review' if vendor=='Hugging Face' else 'product_and_model_updates_first'
n.dump(ROOT/'sources.json',sources)
n.dump(ROOT/'data/source-probes/coverage-notes.json',{'qwen_research':{'url':'https://qwen.ai/research','status':'HTML reachable but article links absent; dynamic-page adapter still needed. Old qwenlm.github.io blog is discontinued and is not a current feed.'},'glm_models':{'url':'https://github.com/zai-org/GLM-5','status':'README readable but no reliable event dates in sampled text; not treated as fresh news. ZCode dated changelog is connected separately.'},'ai2':{'status':'Research institution; ordinary Ai2/Hugging Face tool posts supplementary, not a default main-video selection.'}})
print('Priority updated; Qwen Code Atom and Z.ai dated ZCode changelog added.')
