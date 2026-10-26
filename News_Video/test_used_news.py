import datetime as dt,json,tempfile,unittest
from pathlib import Path
from used_news import CN,exclude_used,recent_records

class UsedNewsChecks(unittest.TestCase):
    def test_ids_tracking_urls_and_republished_titles_are_excluded(self):
        records=[{'news':[{'item_id':'a','source_title':'Qwen Code 新版本','url':'https://example.com/a','event_key':'https://example.com/a'}]}]
        items=[{'id':'a','title':'changed','url':'https://example.com/new'},
               {'id':'b','title':'different','url':'https://example.com/a?utm_source=rss'},
               {'id':'c','title':'Qwen Code：新版本','url':'https://other.com/a'},
               {'id':'d','title':'A newer release','url':'https://example.com/b'}]
        fresh,excluded,context=exclude_used(items,records+records)
        self.assertEqual([x['id'] for x in fresh],['d']);self.assertEqual(len(excluded),3);self.assertEqual(len(context),1)
    def test_previous_evening_survives_beijing_midnight(self):
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as folder:
            root=Path(folder);logs=root/'logs/news-used';logs.mkdir(parents=True)
            (logs/'2026-10-26.jsonl').write_text(json.dumps({'news':[]})+'\n',encoding='utf-8')
            self.assertEqual(len(recent_records(root,days=2,now=dt.datetime(2026,10,27,0,5,tzinfo=CN))),1)
    def test_distinct_releases_on_same_changelog_page_remain_eligible(self):
        records=[{'news':[{'item_id':'old','title':'Release 1','url':'https://example.com/changelog','event_key':'vendor:1'}]}]
        fresh,excluded,_=exclude_used([{'id':'new','title':'Release 2','url':'https://example.com/changelog','event_key':'vendor:2'}],records)
        self.assertEqual(len(fresh),1);self.assertEqual(excluded,[])

if __name__=='__main__':unittest.main()
