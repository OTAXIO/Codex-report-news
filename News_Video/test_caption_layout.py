import json,re,unittest
from pathlib import Path
from caption_layout import cues,normalize,PROTECTED,width
from progress_overlay import build_progress

class CaptionLayoutChecks(unittest.TestCase):
    def test_long_clause_does_not_leave_flashing_one_word_tail(self):
        parts=cues('一则居家养老报道关注了上门照护、社区助餐和智能照护产品的应用。')
        self.assertTrue(all(width(p['text'])>=6 for p in parts))
        self.assertTrue(all('\n' not in p['text'] and width(p['text'])<=24 for p in parts))
    def test_sample_captions_keep_text_numbers_and_terms(self):
        path=Path(__file__).parent/'episodes/sample-20261026-v5/episode.json'
        episode=json.loads(path.read_text(encoding='utf-8'))
        for scene in episode['scenes']:
            for sentence in re.split(r'(?<=[。！？!?])\s*|(?<=\.)\s+|\n+',scene['narration']):
                if not sentence:continue
                parts=cues(sentence);normalized,weights=normalize(sentence)
                self.assertTrue(all('\n' not in part['text'] for part in parts))
                result=''.join(x['text'] for x in parts)
                self.assertEqual(re.sub(r'\s+','',result),re.sub(r'\s+','',normalized))
                self.assertAlmostEqual(sum(x['weight'] for x in parts),len(sentence))
                lines=[line for p in parts for line in p['text'].splitlines()]
                self.assertTrue(all(width(line)<=24 for line in lines))
                for term in PROTECTED+['2.1.310','20.1 亿千瓦','6.34 亿千瓦时','Claude Code','OpenAI','LitPivot']:
                    if term in normalized:self.assertTrue(any(term in line for line in lines),term)
    def test_timeline_keeps_each_news_item_and_active_label(self):
        episode={'scenes':[dict(id='intro',section='资讯样片',title='开场',short_title='导览'),dict(id='a',section='AI 动态',title='新闻 A',short_title='A'),dict(id='b',section='AI 动态',title='新闻 B',short_title='B')]}
        offsets=[dict(start=0,end=2),dict(start=2,end=6),dict(start=6,end=10)]
        html,spec=build_progress(episode,offsets,10,'#01A1FE')
        self.assertEqual([x['label'] for x in spec['chapters']],['导览','A','B'])
        self.assertEqual([x['start'] for x in spec['chapters']],[0,2,6])
        self.assertIn('active-a',html);self.assertIn('active-b',html)
        self.assertIn('current clip',html)
    def test_two_major_modules_follow_the_actual_social_transition(self):
        ep={'scenes':[dict(id='intro',section='晚间新闻',title='导览'),dict(id='ai',section='AI 动态',title='AI'),dict(id='domestic',section='国内新闻',title='国内'),dict(id='world',section='国际新闻',title='国际')]}
        offsets=[dict(start=0,end=3),dict(start=3,end=20),dict(start=20,end=40),dict(start=40,end=60)]
        markup,spec=build_progress(ep,offsets,60,'#01A1FE')
        self.assertEqual([(m['label'],m['start'],m['end']) for m in spec['modules']],[('AI 动态',0,20),('国内外重点新闻',20,60)])
        self.assertIn('module-active-news',markup)
if __name__=='__main__':unittest.main()

class ModelNameChecks(__import__('unittest').TestCase):
    def test_multiword_model_and_benchmark_names_are_atomic(self):
        from caption_layout import cues
        text='GPT-6 Astra 和 GPT-6.1 Sol 在 Agents’ Last Exam 测试中的表现。'
        result=cues(text,max_width=20)
        for name in ['GPT-6 Astra','GPT-6.1 Sol','Agents’ Last Exam']:
            self.assertTrue(any(name in c['text'] for c in result),result)
