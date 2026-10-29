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

if __name__=='__main__':unittest.main()
