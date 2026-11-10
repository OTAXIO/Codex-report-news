"""2026-11-10: one activity per page with a countdown, minor activities last, picture choice."""
import datetime as dt,json,tempfile,unittest
from pathlib import Path
from PIL import Image
import activities as a
import scene_media as m

BJ=dt.timezone(dt.timedelta(hours=8))
NOW=dt.datetime(2026,11,10,10,tzinfo=BJ)
def at(day,hour=4,minute=0):return dt.datetime(2026,11,day,hour,minute,tzinfo=BJ)

def page(name,end_day,scale='main',kind='online',start_day=5,item=None,**extra):
    start,end=at(start_day,16),at(end_day,3,59)
    state='upcoming' if start>NOW else 'ending' if end<=NOW+dt.timedelta(days=3) else 'ongoing'
    entry=dict(item_id=item or name,name=name,kind=kind,scale=scale,start_at=start.isoformat(),end_at=end.isoformat(),window_quote='q',source_type='official_game_page',**extra)
    spoken=f'活动到11月{end_day}日截止。' if start<=NOW else f'活动11月{start_day}日开启。'
    scene=dict(id=name,item_id=item or name,game='endfield',narration=spoken,facts=[dict(title='参与方式',detail='登录即可参加')],activity_items=[entry])
    check=dict(start_at=start.isoformat(),end_at=end.isoformat(),state=state)
    return scene,entry,check

def bound(*args,text='',**kw):
    scene,entry,check=page(*args,**kw);scene['activity']=a.describe(scene,entry,check,NOW,text);return scene

class CountdownTests(unittest.TestCase):
    def test_days_left_today_tomorrow_and_upcoming(self):
        s=a.status(at(5,16),at(20,3,59),NOW)
        self.assertEqual((s['phase'],s['days'],s['label'],s['urgent']),('running',10,'还剩10天',False))
        self.assertEqual(s['countdown'],dict(lead='距截止还有',big='10',tail='天'))
        self.assertEqual(s['end_label'],'11月20日 03:59 截止')
        today=a.status(at(5,16),at(10,23,59),NOW)
        self.assertEqual((today['countdown'],today['label'],today['urgent']),(dict(lead='今天',big='23:59',tail='截止'),'今天截止',True))
        self.assertEqual(a.status(at(5,16),at(11,3,59),NOW)['label'],'明天截止')
        soon=a.status(at(13,16),at(25,3,59),NOW)
        self.assertEqual((soon['phase'],soon['label'],soon['countdown']['lead'],soon['urgent']),('upcoming','3天后开启','距开启还有',False))

class PageRuleTests(unittest.TestCase):
    def test_deadline_must_be_spoken_and_facts_stay_short(self):
        scene,entry,check=page('签到',20)
        self.assertEqual(a.describe(scene,entry,check,NOW,'')['kind_label'],'线上活动')
        for spoken in ['活动到十一月二十号截止。','活动到11月20号截止。']:
            a.describe(dict(scene,narration=spoken),entry,check,NOW,'')
        with self.assertRaisesRegex(ValueError,'ACTIVITY_DEADLINE_NOT_SPOKEN'):a.describe(dict(scene,narration='活动正在进行。'),entry,check,NOW,'')
        with self.assertRaisesRegex(ValueError,'ACTIVITY_FACTS'):a.describe(dict(scene,facts=[dict(title='t',detail='d')]*3),entry,check,NOW,'')
        with self.assertRaisesRegex(ValueError,'ACTIVITY_FACTS'):a.describe(dict(scene,facts=[dict(title='t',detail='长'*55)]),entry,check,NOW,'')
    def test_offline_needs_official_location_and_collab_its_partner(self):
        scene,entry,check=page('主题展',20,kind='offline')
        with self.assertRaisesRegex(ValueError,'ACTIVITY_LOCATION'):a.describe(scene,entry,check,NOW,'上海静安大悦城')
        entry['location']='北京三里屯'
        with self.assertRaisesRegex(ValueError,'not in the official text'):a.describe(scene,entry,check,NOW,'地点：上海静安大悦城')
        entry['location']='上海静安大悦城'
        self.assertEqual(a.describe(scene,entry,check,NOW,'地点：上海静安大悦城')['location'],'上海静安大悦城')
        scene,entry,check=page('联名',20,kind='collab')
        with self.assertRaisesRegex(ValueError,'ACTIVITY_PARTNER'):a.describe(scene,entry,check,NOW,'')
        with self.assertRaisesRegex(ValueError,'ACTIVITY_KIND'):a.describe(scene,dict(entry,kind='party'),check,NOW,'')

class OrderTests(unittest.TestCase):
    def test_main_first_minor_last_then_by_deadline(self):
        news=dict(id='news',item_id='news')
        scenes=[bound('网页投稿',12,scale='minor'),news,bound('大型活动',25),bound('即将结束',12),bound('未开始',25,start_day=13)]
        ep=dict(scenes=list(scenes));a.arrange(ep)
        self.assertEqual([s['id'] for s in ep['scenes']],['即将结束','news','大型活动','未开始','网页投稿'])
        a.validate_pages(ep,6)
        with self.assertRaisesRegex(ValueError,'ACTIVITY_PAGES'):a.validate_pages(ep,3)
        with self.assertRaisesRegex(ValueError,'ACTIVITY_ORDER'):a.validate_pages(dict(scenes=scenes),6)
    def test_same_activity_once_and_not_also_a_news_page(self):
        with self.assertRaisesRegex(ValueError,'ACTIVITY_DUPLICATE'):a.validate_pages(dict(scenes=[bound('签到',20),bound('签到',20)]),6)
        with self.assertRaisesRegex(ValueError,'already a news page'):a.validate_pages(dict(scenes=[dict(id='n',item_id='x'),bound('签到',20,item='x')]),6)
    def test_lead_activity_may_open_the_edition(self):
        late=bound('大型活动',25);late['event_key']='lead'
        a.validate_pages(dict(lead_event_id='lead',scenes=[late,bound('即将结束',12)]),6)

class LedgerAndScanTests(unittest.TestCase):
    def test_running_activities_are_reported_until_they_end(self):
        with tempfile.TemporaryDirectory() as tmp:
            a.record(dict(id='e1',scenes=[bound('签到',20),bound('网页投稿',12,scale='minor')]),tmp)
            self.assertEqual([(r['name'],r['label']) for r in a.running(tmp,'endfield',NOW)],[('签到','还剩10天'),('网页投稿','还剩2天')])
            self.assertEqual([r['name'] for r in a.running(tmp,'endfield',at(15))],['签到'])
            self.assertEqual(a.running(tmp,'arknights',NOW),[])
    def test_windows_are_found_in_official_text(self):
        found=a.windows('活动时间：11月5日 16:00 - 11月20日 03:59，另有 2026年12月28日~1月4日 线下展',at(1))
        self.assertEqual([w['start_at'] for w in found],['2026-11-05T16:00:00+08:00','2026-12-28T00:00:00+08:00'])
        self.assertEqual([w['end_at'] for w in found],['2026-11-20T03:59:00+08:00','2027-01-04T23:59:59+08:00'])
        with tempfile.TemporaryDirectory() as tmp:
            items=Path(tmp)/'data/game-items';items.mkdir(parents=True)
            rows=[('big','「终末回响」活动开启','活动时间：11月5日 16:00 - 11月20日 03:59'),('mini','同人投稿征集','11月8日 - 11月12日'),('show','线下主题展','11月7日 10:00 - 11月16日 22:00'),('done','旧活动','10月20日 - 11月2日')]
            for key,title,text in rows:(items/(key+'.json')).write_text(json.dumps(dict(game='endfield',title=title,summary=text,published=at(4).isoformat(),url='u',source_type='official_game_page')),encoding='utf-8')
            got=a.scan(tmp,'endfield',NOW)
            self.assertEqual([(r['item_id'],r['kind_guess'],r['scale_guess']) for r in got],[('show','offline','main'),('big','online','main'),('mini','online','minor')])

class PictureChoiceTests(unittest.TestCase):
    GATE=dict(min_short_side=240,min_long_side=480,max_flat=.88,min_entropy=3.0)
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        (self.root/'assets').mkdir();(self.root/'data/articles').mkdir(parents=True)
    def picture(self,name,size,flat=False):
        im=Image.new('RGB',size,'white') if flat else Image.effect_noise(size,64).convert('RGB')
        im.save(self.root/'assets'/name);return dict(file='assets/'+name,source_url='https://official.example/'+name)
    def article(self,*images):(self.root/'data/articles/post.json').write_text(json.dumps(dict(related_images=list(images))),encoding='utf-8')
    def test_gate_rejects_blank_and_tiny_pictures(self):
        self.assertEqual(m.quality(self.root/self.picture('blank.png',(1200,700),True)['file'],self.GATE)['reject'],'low_information')
        self.assertEqual(m.quality(self.root/self.picture('tiny.png',(200,120))['file'],self.GATE)['reject'],'too_small')
        self.assertIsNone(m.quality(self.root/self.picture('good.png',(1200,700))['file'],self.GATE)['reject'])
    def test_blank_picture_is_replaced_from_the_same_article(self):
        blank,good=self.picture('blank.png',(1200,700),True),self.picture('good.png',(1200,700));self.article(blank,good)
        scene=dict(id='s',game='endfield',item_id='post',image=blank['file'],image_source_url=blank['source_url'])
        report=m.select(scene,self.root,self.GATE)
        self.assertEqual((scene['image'],scene['image_source_url'],report['requested']),(good['file'],good['source_url'],blank['file']))
    def test_good_choice_is_kept_and_long_poster_gives_way(self):
        good,other,poster=self.picture('good.png',(1200,700)),self.picture('other.png',(1600,900)),self.picture('poster.png',(600,2400));self.article(good,other,poster)
        scene=dict(id='s',game='endfield',item_id='post',image=good['file'],image_source_url=good['source_url'])
        m.select(scene,self.root,self.GATE);self.assertEqual(scene['image'],good['file'])
        scene=dict(id='s',game='endfield',item_id='post',image=poster['file'],image_source_url=poster['source_url'])
        self.article(other,poster);m.select(scene,self.root,self.GATE);self.assertEqual(scene['image'],other['file'])
        empty=dict(id='s',game='endfield',item_id='post');m.select(empty,self.root,self.GATE);self.assertEqual(empty['image'],other['file'])
    def test_rejected_picture_without_alternative_falls_back_to_identity(self):
        blank=self.picture('blank.png',(1200,700),True)
        scene=dict(id='s',company='OpenAI',image=blank['file'],image_source_url=blank['source_url'])
        report=m.select(scene,self.root,self.GATE)
        self.assertEqual((report['rejected'],'image' in scene),('low_information',False))
        ai=dict(id='s',company='OpenAI',item_id='post');self.article(self.picture('good.png',(1200,700)))
        m.select(ai,self.root,self.GATE);self.assertNotIn('image',ai)   # only game pages take article pictures on their own

if __name__=='__main__':unittest.main()
