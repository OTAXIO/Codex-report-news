import unittest
from unittest.mock import Mock
from skland_sources import parse_rows,BrowserReader,SourceStopped

class SklandSourceChecks(unittest.TestCase):
    def setUp(self):
        self.source=dict(url='https://www.skland.com/game/arknights?cateId=1',official_authors=['明日方舟Arknights'],skland_game_id=1,skland_cate_id=1,game='arknights',game_region='cn')
        self.item=dict(item=dict(id='123',gameId=1,cateId=1,title='游戏更新',publishedAtTs='1793246401',imageList=[dict(url='https://bbs.hycdn.cn/test.webp')]),user=dict(id='42',nickname='明日方舟Arknights',identity=2))

    def test_original_time_author_and_images_preserved(self):
        item=parse_rows([self.item],self.source)[0]
        self.assertEqual(item['published'],'2026-10-29T04:00:01+00:00')
        self.assertEqual(item['original_author'],'明日方舟Arknights')
        self.assertEqual(item['images'],['https://bbs.hycdn.cn/test.webp'])
        self.assertFalse(item['body_complete'])
        self.assertEqual(item['author_profile'],'https://www.skland.com/profile?id=42')

    def test_common_user_with_official_name_rejected(self):
        self.item['user']['identity']=1;self.assertEqual(parse_rows([self.item],self.source),[])

    def test_unlisted_official_and_wrong_game_rejected(self):
        self.item['user']['nickname']='周边商城';self.assertEqual(parse_rows([self.item],self.source),[])
        self.item['user']['nickname']='明日方舟Arknights';self.item['item']['gameId']=3
        self.assertEqual(parse_rows([self.item],self.source),[])

    def test_missing_time_never_replaced_with_collection_clock(self):
        self.item['item'].pop('publishedAtTs');self.assertEqual(parse_rows([self.item],self.source),[])

    def test_auth_or_rate_limit_stops_without_second_backend(self):
        reader=BrowserReader.__new__(BrowserReader);reader.session='fixture'
        reader.call=Mock(return_value=dict(requests=[dict(status=401)]))
        with self.assertRaisesRegex(SourceStopped,'NEED_USER'):reader.responses('/web/v2/home/index')
        self.assertEqual(reader.call.call_count,1)

    def test_partial_response_not_treated_as_complete_body(self):
        reader=BrowserReader.__new__(BrowserReader);reader.session='fixture'
        reader.call=Mock(return_value=dict(request=dict(response_body=dict(state='truncated'))))
        with self.assertRaisesRegex(SourceStopped,'incomplete'):reader.body('request','/data')

    def test_debug_start_failure_closes_owned_session(self):
        reader=BrowserReader.__new__(BrowserReader);reader.local=dict(instance_id='fixture');reader.session=None
        reader.call=Mock(side_effect=[dict(session_id='owned'),SourceStopped('capture unavailable'),{}])
        with self.assertRaises(SourceStopped):reader.__enter__()
        self.assertEqual(reader.call.call_args.args,('session','stop','owned'))

    def test_exit_closes_session_even_when_capture_stop_fails(self):
        reader=BrowserReader.__new__(BrowserReader);reader.session='owned';reader.call=Mock(side_effect=[SourceStopped('capture unavailable'),{}])
        with self.assertRaises(SourceStopped):reader.__exit__(None,None,None)
        self.assertEqual(reader.call.call_args.args,('session','stop','owned'))

class SklandCaptureChecks(unittest.TestCase):
    """Built-in browser captures (skland_capture.js) import like collected items."""
    def run_import(self,capture):
        import tempfile,datetime as dt
        from pathlib import Path
        from unittest.mock import patch
        import news_video as n,skland_sources as s
        with tempfile.TemporaryDirectory() as tmp,patch.object(n,'ROOT',Path(tmp)),patch('news_video.fetch',side_effect=OSError('offline')):
            root=Path(tmp)
            n.dump(root/'sources.json',[dict(id='skland-arknights',name='森空岛',publisher='明日方舟Arknights',group='games',type='skland_capture',
                url='https://www.skland.com/game/arknights?cateId=1',game='arknights',game_region='cn',skland_game_id=1,skland_cate_id=1,
                official_authors=['明日方舟Arknights'],enabled=True)])
            path=root/'data/skland-captures/cap.json';n.dump(path,capture)
            result=s.import_capture(path)
            db=n.database();rows=[dict(r) for r in db.execute('SELECT * FROM items')];db.close()
            articles=[n.load(p) for p in (root/'data/articles').glob('*.json')] if (root/'data/articles').is_dir() else []
            status=s.capture_status(root,dict(id='skland-arknights',url='u'),dt.datetime.now(dt.timezone.utc))
            return result,rows,articles,n.load(path),status

    def capture(self,text='SideStory 现已开启',truncated=False,page='https://www.skland.com/game/arknights?cateId=1'):
        return dict(page=page,captured_at='2026-11-02T00:00:00Z',rows=[
            dict(item=dict(id='9',title='SideStory开启',gameId=1,cateId=1,publishedAtTs='1793505636',imageList=[],text=text,text_truncated=truncated),
                 user=dict(id='1',nickname='明日方舟Arknights',identity=2)),
            dict(item=dict(id='10',title='同名冒充',gameId=1,cateId=1,publishedAtTs='1793505636',imageList=[],text='x'),
                 user=dict(id='2',nickname='路人',identity=2))])

    def test_official_rows_stored_with_exact_time_and_complete_body(self):
        result,rows,articles,saved,status=self.run_import(self.capture())
        self.assertEqual((result['official'],result['skipped_non_official'],result['complete_bodies']),(1,1,1))
        self.assertEqual(rows[0]['published'],'2026-11-01T04:00:36+00:00')
        self.assertTrue(articles[0]['body_complete']);self.assertEqual(articles[0]['text'],'SideStory 现已开启')
        self.assertEqual(saved['source_id'],'skland-arknights');self.assertTrue(status['ok'])

    def test_truncated_or_empty_text_needs_article_capture(self):
        for text,truncated in [('长公告前半',True),('',False)]:
            result,rows,articles,_,_=self.run_import(self.capture(text,truncated))
            self.assertEqual(result['complete_bodies'],0);self.assertEqual(articles,[]);self.assertEqual(len(rows),1)

    def test_unregistered_page_rejected(self):
        with self.assertRaisesRegex(ValueError,'not a registered'):self.run_import(self.capture(page='https://www.skland.com/game/endfield?cateId=99'))

    def test_missing_capture_reported_not_silent(self):
        import datetime as dt,tempfile
        import skland_sources as s
        with tempfile.TemporaryDirectory() as tmp:
            status=s.capture_status(tmp,dict(id='skland-endfield',url='https://www.skland.com/game/endfield?cateId=12'),dt.datetime.now(dt.timezone.utc))
        self.assertFalse(status['ok']);self.assertIn('CAPTURE_REQUIRED',status['error'])

if __name__=='__main__':unittest.main()
