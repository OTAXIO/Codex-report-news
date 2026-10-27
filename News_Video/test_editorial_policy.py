import datetime as dt,unittest
from editorial_policy import coverage,audit_selection
class EditorialCoverageChecks(unittest.TestCase):
    def setUp(self):
        self.now=dt.datetime(2026,10,27,9,tzinfo=dt.timezone.utc)
        self.cfg={'vendor_regions':{'Kimi':'domestic','MiniMax':'domestic','Google':'international'},'ai_coverage':{'targets':{'domestic':3,'international':3},'fresh_hours':24}}
        self.sources={'kimi':{'vendor':'Kimi'},'minimax':{'vendor':'MiniMax'},'google':{'vendor':'Google'}}
    def row(self,key,source='kimi',age=1):
        return dict(id=key,source_id=source,kind='ai',url='https://example.com/'+key,published=(self.now-dt.timedelta(hours=age)).isoformat())
    def test_three_plus_three_target_not_cap(self):
        rows=[self.row('d'+str(i)) for i in range(4)]+[self.row('i'+str(i),'google') for i in range(4)]
        result=audit_selection({'edition_slot':'morning'},rows,rows,self.sources,self.cfg,self.now)
        self.assertEqual(result['selected'],{'domestic':4,'international':4});self.assertEqual(result['status'],'target_met')
    def test_old_future_and_social_do_not_fill_ai_quota(self):
        rows=[self.row('old',age=25),self.row('future',age=-1),dict(self.row('social'),kind='social')]
        self.assertEqual(coverage(rows,self.sources,self.cfg,self.now)['available']['domestic'],0)
    def test_unknown_vendor_and_duplicate_event_do_not_inflate_count(self):
        rows=[dict(self.row('a'),event_key='same'),dict(self.row('b'),event_key='same'),self.row('c','unverified')]
        result=coverage(rows,self.sources,self.cfg,self.now)
        self.assertEqual(result['available']['domestic'],1);self.assertEqual(result['candidate_ids']['unknown'],['c'])
    def test_scarcity_is_recorded_without_blocking(self):
        rows=[self.row('a')]
        result=audit_selection({'edition_slot':'noon'},rows,rows,self.sources,self.cfg,self.now)
        self.assertEqual(result['status'],'partial_with_reason');self.assertEqual(result['shortfall'],{'domestic':2,'international':3})
    def test_abundant_raw_candidates_never_force_minimum_or_reason(self):
        rows=[self.row(str(i)) for i in range(8)]
        self.cfg['ai_coverage']['require_omission_reason_when_candidates_available']=True
        result=audit_selection({'edition_slot':'night'},rows[:1],rows,self.sources,self.cfg,self.now)
        self.assertEqual(result['selected']['domestic'],1);self.assertTrue(result['advisory_only'])
        self.assertFalse(result['enforce_minimum']);self.assertEqual(result['shortfall']['domestic'],2)
        empty=audit_selection({'edition_slot':'night'},[],rows,self.sources,self.cfg,self.now)
        self.assertEqual(empty['selected'],{'domestic':0,'international':0})
        result=audit_selection({'edition_slot':'night','ai_shortfall_reasons':{'domestic':'另外内容均为重复案例。'}},rows[:1],rows,self.sources,self.cfg,self.now)
        self.assertIn('重复案例',result['reasons']['domestic'])
    def test_temporary_not_subject_to_six_news_target(self):
        self.assertIsNone(audit_selection({'edition_slot':'temporary'},[],[],self.sources,self.cfg,self.now))
    def test_kimi_dated_card_uses_date_not_crawl_time(self):
        import news_video as n
        markup=b'<a href="/en/blog/model"><div class="card-body"><h4>New Kimi</h4><p>2026-10-24</p></div></a>'
        entries=n.official_bridge(markup,{'id':'kimi-blog','url':'https://www.kimi.com/blog/'},'utf-8')
        self.assertEqual(entries[0]['title'],'New Kimi');self.assertEqual(entries[0]['published_precision'],'date')
        with self.assertRaises(ValueError):n.official_bridge(b'<p>Updated today</p>',{'id':'kimi-blog','url':'https://www.kimi.com/blog/'},'utf-8')

    def test_editorial_import_writes_regional_audit_from_database(self):
        import tempfile,json,news_video as n
        from pathlib import Path
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp,patch.object(n,'ROOT',Path(tmp)):
            now=dt.datetime.now(dt.timezone.utc)
            cfg={'x_enabled':False,'publication_preset':{},'presentation':{'prefer_overview':False},'editorial':dict(self.cfg,include_important_recaps=False)}
            n.dump(n.ROOT/'config.json',cfg);n.dump(n.ROOT/'sources.json',[dict(v,id=k) for k,v in self.sources.items()])
            db=n.database();scenes=[]
            for i in range(6):
                key=str(i);source='kimi' if i<3 else 'google';url='https://example.com/'+key
                db.execute('INSERT INTO items VALUES(?,?,?,?,?,?,?,?,?,?,?)',(key,source,source,'ai','Fixture '+key,url,now.isoformat(),'fixture',now.isoformat(),now.isoformat(),key))
                scenes.append(dict(id='scene'+key,item_id=key,title='Fixture '+key,source_url=url,evidence='isolated fixture',selection_reason='isolated test',published=now.isoformat(),narration='隔离测试，不上传。'))
            db.commit();db.close()
            n.dump(n.ROOT/'input.json',dict(id='fixture-main',producer='Codex current conversation',edition_slot='morning',scenes=scenes))
            n.import_editorial(n.ROOT/'input.json')
            audit=n.load(n.ROOT/'episodes/fixture-main/ai-coverage-audit.json')
            self.assertEqual(audit['selected'],{'domestic':3,'international':3});self.assertEqual(audit['status'],'target_met')
            short=n.load(n.ROOT/'input.json');short['scenes']=short['scenes'][:1];n.dump(n.ROOT/'input.json',short)
            n.import_editorial(n.ROOT/'input.json')
            saved=n.load(n.ROOT/'episodes/fixture-main/episode.json');self.assertEqual(len(saved['scenes']),1)
            self.assertTrue(saved['ai_coverage_audit']['advisory_only'])

    def test_workbuddy_versions_have_distinct_ids_and_date_precision(self):
        import news_video as n
        markup=('<h2>5.9.2 版本发布（2026-10-26）</h2><p>新增实用功能</p>'
                '<h2>5.9.1 版本发布（2026-10-22）</h2><p>旧版修复</p>').encode()
        source={'id':'workbuddy-changelog','url':'https://www.workbuddy.cn/docs/workbuddy/Changelog'}
        entries=n.official_bridge(markup,source,'utf-8')
        self.assertEqual(len(entries),2);self.assertNotEqual(entries[0]['entry_key'],entries[1]['entry_key'])
        self.assertEqual(entries[0]['published_precision'],'date');self.assertIn('新增实用功能',entries[0]['summary'])
        self.assertNotIn('旧版修复',entries[0]['summary'])
