"""2026-11-11 快讯 pages: 2-3 verified, fresh, attributed entries; rumors and context posts keep their own page."""
import datetime as dt,json,shutil,sqlite3,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import news_video as n
import briefs

HERE=Path(__file__).resolve().parent
NOW=dt.datetime.now(dt.timezone.utc)

class BriefTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
        for name in ['config.json','sources.json','leader_sources.json']:shutil.copy2(HERE/name,self.root/name)
        p=patch.object(n,'ROOT',self.root);p.start();self.addCleanup(p.stop)
        self.db=n.database();self.addCleanup(self.db.close)
        self.catalog={s['id']:s for s in json.loads((self.root/'sources.json').read_text(encoding='utf-8'))}
        self.add('a','google-ai','Google Cloud launches Gemini for healthcare','https://blog.google/a')
        self.add('b','techcrunch-ai','ElevenLabs launches Scribe v3','https://techcrunch.com/b')
        self.add('c','reddit-singularity','Rumor: GPT-6.2 spotted','https://reddit.com/c')
        self.add('old','google-ai','An old post','https://blog.google/old',hours=80)

    def add(self,i,source,title,url,hours=3):
        published=(NOW-dt.timedelta(hours=hours)).isoformat()
        self.db.execute('INSERT INTO items VALUES(?,?,?,?,?,?,?,?,?,?,?)',(i,source,self.catalog[source]['publisher'],'ai',title,url,published,title,published,published,'h'))
        self.db.commit()

    def scene(self,entries,narration):
        return dict(scene_type='briefs',item_id=entries[0]['item_id'],source_url=entries[0]['source_url'],brief_items=entries,narration=narration)
    def entry(self,i,url,title,key,detail='一句话说明这条消息'):return dict(item_id=i,source_url=url,title=title,detail=detail,spoken_key=key)

    def test_valid_page_builds_facts_and_returns_every_entry(self):
        scene=self.scene([self.entry('a','https://blog.google/a','谷歌推出医疗版Gemini','医疗版Gemini'),
                          self.entry('b','https://techcrunch.com/b','ElevenLabs发布Scribe v3','Scribe v3')],
                         '谷歌推出医疗版Gemini，面向医院。据TechCrunch报道，ElevenLabs发布Scribe v3语音识别模型。')
        out=briefs.validate(scene,self.db,self.catalog,self.root)
        self.assertEqual([i for i,_ in out],['a','b']);self.assertEqual(len(scene['facts']),2)
        self.assertTrue(scene['facts'][1]['detail'].endswith('（TechCrunch）'));self.assertEqual(scene['segment'],'briefs')

    def test_rules(self):
        a=self.entry('a','https://blog.google/a','谷歌推出医疗版Gemini','医疗版Gemini')
        b=self.entry('b','https://techcrunch.com/b','ElevenLabs发布Scribe v3','Scribe v3')
        cases=[([a],'医疗版Gemini','BRIEFS_ITEMS'),
               ([a,b],'医疗版Gemini，然后Scribe v3。','BRIEFS_MEDIA'),
               ([a,b],'Scribe v3先说，医疗版Gemini后说。据TechCrunch报道','BRIEFS_NARRATION'),
               ([a,self.entry('c','https://reddit.com/c','传GPT-6.2灰度','GPT-6.2')],'医疗版Gemini。GPT-6.2。','BRIEFS_SOURCE'),
               ([a,self.entry('old','https://blog.google/old','旧消息再发','旧消息')],'医疗版Gemini。旧消息。','BRIEFS_FRESHNESS'),
               ([a,dict(b,source_url='https://evil.example/b')],'医疗版Gemini。据TechCrunch报道Scribe v3。','BRIEFS_URL'),
               ([a,dict(b,spoken_key='语音')],'医疗版Gemini。据TechCrunch报道语音。','BRIEFS_KEY')]
        for entries,narration,code in cases:
            with self.subTest(code=code),self.assertRaisesRegex(ValueError,code):
                briefs.validate(self.scene(entries,narration),self.db,self.catalog,self.root)

    def test_story_order_puts_briefs_after_official_and_never_first(self):
        import production_policy as pp
        self.assertLess(pp.SEGMENT_ORDER['ai']['official'],pp.SEGMENT_ORDER['ai']['briefs'])
        self.assertLess(pp.SEGMENT_ORDER['ai']['briefs'],pp.SEGMENT_ORDER['ai']['github'])
        self.assertEqual(pp.GROUP_LABELS['briefs'],'快讯')

    def test_description_lists_every_entry_and_title_skips_the_page(self):
        import publication_policy as pub
        a=self.entry('a','https://blog.google/a','谷歌推出医疗版Gemini','医疗版Gemini')
        b=self.entry('b','https://techcrunch.com/b','ElevenLabs发布Scribe v3','Scribe v3')
        scene=self.scene([a,b],'谷歌推出医疗版Gemini。据TechCrunch报道，ElevenLabs发布Scribe v3。')
        briefs.validate(scene,self.db,self.catalog,self.root)
        self.assertEqual(scene['brief_publishers'],['Google AI','TechCrunch'])
        lead=dict(id='lead',item_id='lead',title='Claude 额度重置',source_url='https://x.com/lead',narration='重置。')
        ep=dict(edition_slot='morning',edition_series='ai',edition_date='2026-11-11',lead_event_id='lead',scenes=[lead,dict(scene,id='briefs',title='今日快讯')])
        text=pub.describe(ep,{},dict(sentences=[dict(scene_id='lead',start=3),dict(scene_id='briefs',start=70)]))
        self.assertIn('01:10 快讯：谷歌推出医疗版Gemini / ElevenLabs发布Scribe v3',text)
        for url in ['https://x.com/lead','https://blog.google/a','https://techcrunch.com/b']:self.assertIn(url,text)
        with self.assertRaisesRegex(ValueError,'TITLE_BRIEFS_PAGE'):
            pub.title_for(ep,dict(title_groups=[dict(kind='ai',event_ids=['lead','a'])]))
        many=dict(ep,scenes=[dict(lead,id=f's{i}',item_id=f's{i}',source_url=f'https://example.com/{i:03}/'+'x'*90) for i in range(40)])
        self.assertLessEqual(len(pub.describe(many,{},{})),2000)

if __name__=='__main__':unittest.main()
