import datetime as dt,json,tempfile,unittest,hashlib
from pathlib import Path
from unittest.mock import patch
import news_video as n
import reset_alerts as r
from release_manager import naming
from progress_overlay import build_progress

class ResetAlertChecks(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.patch=patch.object(n,'ROOT',self.root);self.patch.start()
        cfg=json.loads((Path(__file__).parent/'config.json').read_text(encoding='utf-8'));n.dump(self.root/'config.json',cfg)
        # Isolated reset drafts use the same verified-identity requirement as production.
        import shutil
        asset=self.root/'assets/logos/openai.png';asset.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(Path(__file__).parent/'assets/logos/openai.png',asset)
        n.dump(self.root/'assets/logos/sources.json',dict(assets=[dict(id='openai',path='assets/logos/openai.png',source='https://github.com/openai',sha256=hashlib.sha256(asset.read_bytes()).hexdigest())]))
        self.now=dt.datetime.now(n.UTC)
    def tearDown(self):self.patch.stop();self.tmp.cleanup()

    def post(self,number,text='We will reset Codex usage limits today.',age=0,handle='thsottiaux'):
        url=f'https://x.com/{handle}/status/{number}';key=hashlib.sha256(url.encode()).hexdigest()[:20]
        post=dict(id=key,summary=text,handle=handle,source_type='leader_x',published=(self.now-dt.timedelta(hours=age)).isoformat(),
                  url=url,author='tibo' if handle=='thsottiaux' else 'Other',requires_context=False)
        n.dump(self.root/'data/leader-posts'/(key+'.json'),post)
        db=n.database();db.execute('INSERT INTO items VALUES(?,?,?,?,?,?,?,?,?,?,?)',(key,'x-leader-'+handle,post['author'],'ai',text,url,post['published'],text,self.now.isoformat(),self.now.isoformat(),hashlib.sha256(text.encode()).hexdigest()));db.commit();db.close()
        return key

    def review(self):
        return dict(is_reset_announcement=True,context_verified=True,announcement_status='planned',summary='tibo 预告今天重置 Codex 额度。',
                    narration='tibo 于北京时间十二点十分表示，今天计划重置 Codex 使用额度。这里的消息来自他本人发布的推文，属于对今天重置安排的预告，而不是已经完成重置的确认。原帖没有列出适用账号、具体额度数量或准确生效时间，因此不能据此认定所有用户已经获得新的额度。具体情况需要结合后续官方消息确认，本条只介绍这一次推文明确表达的信息。',title='tibo：今天重置 Codex 额度',quote='We will reset Codex usage limits today.',reset_event_key='codex-reset-test')

    def test_existing_posts_baseline_then_new_tibo_only_and_idempotent(self):
        self.post(1);self.assertTrue(r.scan(self.now)['initialized'])
        self.post(2);self.post(3,handle='sama');self.post(4,text='A new product theme');self.post(5,age=10)
        result=r.scan(self.now);self.assertEqual(len(result['new_alerts']),1)
        self.assertFalse(r.pending()[0]['counts_toward_daily_main_limit']);self.assertEqual(r.scan(self.now)['new_alerts'],[])

    def test_keyword_alone_cannot_make_publishable_draft(self):
        r.scan(self.now);key=self.post(10,text='Please reset my limits!');r.scan(self.now)
        n.dump(self.root/'review.json',dict(self.review(),is_reset_announcement=False))
        with self.assertRaises(ValueError):r.draft(key,self.root/'review.json',self.now)
        self.assertFalse((self.root/'episodes').exists())

    def test_reviewed_tweet_only_draft_and_one_reset_event(self):
        r.scan(self.now);key=self.post(20);r.scan(self.now);n.dump(self.root/'review.json',self.review())
        alert=r.draft(key,self.root/'review.json',self.now);ep=n.load(self.root/'episodes'/alert['episode_id']/'episode.json')
        self.assertEqual(ep['edition_slot'],'temporary');self.assertEqual(len(ep['scenes']),1)
        self.assertFalse(ep['counts_toward_daily_main_limit']);self.assertEqual(ep['scenes'][0]['publisher'],'tibo')
        self.assertEqual(ep['scenes'][0]['resolved_media']['subject'],'openai')
        _,spec=build_progress(ep,[dict(start=0,end=8)],8,'#01A1FE')
        self.assertEqual([x['label'] for x in spec['modules']],['临时新闻'])
        other=self.post(21);r.scan(self.now)
        with self.assertRaises(ValueError):r.draft(other,self.root/'review.json',self.now)
        a,b=naming(ep['edition_date'],'temporary',ep['edition_timestamp'],key)
        c,_=naming(ep['edition_date'],'temporary',ep['edition_timestamp'],other)
        self.assertNotEqual(a,c);self.assertTrue(b.endswith('_临时新闻.mp4'))

    def test_no_news_mix_and_no_stale_urgent_publish(self):
        with self.assertRaises(ValueError):r.validate_temporary(dict(edition_slot='temporary',edition_type='temporary',counts_toward_daily_main_limit=True,scenes=[]))
        r.scan(self.now);key=self.post(30);r.scan(self.now);n.dump(self.root/'review.json',self.review())
        with self.assertRaises(ValueError):r.draft(key,self.root/'review.json',self.now+dt.timedelta(hours=7))
        r.scan(self.now+dt.timedelta(hours=7));self.assertEqual(r.pending(),[])

if __name__=='__main__':unittest.main()
