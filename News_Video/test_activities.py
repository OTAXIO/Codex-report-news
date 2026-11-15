"""2026-11-10: one activity per page with a countdown, minor activities last, picture choice.
2026-11-15: the activity calendar (official windows, phases, days left) behind the 活动日历 page."""
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

# Excerpts in the shape of the official notices (终末地 6094 版本说明, 方舟 0787 感谢庆典公告).
EF_TEXT="""「丹青渡」版本更新说明
■ 「丹青渡」版本更新维护时间
2026/10/15 06:00 - 2026/10/15 12:00（UTC+8）
1.「百趣演武」挑战活动
· 活动时间：2026/10/29 12:00 - 2026/11/19 04:00（服务器时间）
· 活动内容更新时间：2026/11/11 04:00（服务器时间）
2.「烟火生缘」趣味活动
· 活动时间：「丹青渡」版本更新后 - 版本更新维护前
3.「密境行者」空间组更新
· 更新时间：2026/11/12 12:00（服务器时间）
· 更新说明：「密境行者」解谜活动将更新新空间组「画外遗光」，率先开放3个协议空间，并在2026/11/19 04:00（服务器时间）开放后续3个协议空间。
4.【特惠武库配额包】限时礼包
· 售卖时间：2026/10/29 12:00 - 2026/11/19 04:00（服务器时间）"""
AK_TEXT="""SideStory「时间啊，向前！」活动
<第一段>
开放时间：11月01日 12:00 - 11月22日 03:59
<第二段>
开放时间：11月08日 16:00 - 11月22日 03:59
<第三段>
开放时间：11月15日 16:00 - 11月22日 03:59
◆ 维护补偿发放时间：11月01日 12:00 - 11月08日 03:59
【活动时间】
11月01日 12:00 - 11月29日 03:59"""

def calendar_root(tmp,items):
    root=Path(tmp);(root/'data/game-items').mkdir(parents=True);(root/'data/articles').mkdir(parents=True)
    (root/'config.json').write_text(json.dumps(dict(activity_calendar=dict(regions=dict(endfield=['cn'],arknights=['cn']),max_sync_age_hours=12,rows_per_page=12,upcoming_days=3))),encoding='utf-8')
    for key,game,title,text in items:
        (root/'data/game-items'/(key+'.json')).write_text(json.dumps(dict(game=game,game_region='cn',title=title,summary=text[:80],url='https://example.test/'+key,published=at(1).isoformat() if game=='endfield' else '2026-10-24T20:30:00+08:00',source_type='official_game_page')),encoding='utf-8')
        (root/'data/articles'/(key+'.json')).write_text(json.dumps(dict(item_id=key,text=text)),encoding='utf-8')
    return root

def calendar_root_add(root,key,title,text,published=None):
    (Path(root)/'data/game-items'/(key+'.json')).write_text(json.dumps(dict(game='endfield',game_region='cn',title=title,summary=text[:80],url='https://example.test/'+key,
        published=(published or at(20)).isoformat(),source_type='official_game_page')),encoding='utf-8')
    (Path(root)/'data/articles'/(key+'.json')).write_text(json.dumps(dict(item_id=key,text=text)),encoding='utf-8')

class CalendarTests(unittest.TestCase):
    def test_version_note_gives_windows_phases_and_open_drops(self):
        found,starts=a.extract(EF_TEXT,'endfield','cn',at(1),'v1')
        by={a.key_name(e['name']):e for e in found}
        self.assertEqual(starts['丹青渡']['start_at'],'2026-10-15T12:00:00+08:00')
        self.assertEqual(set(by),{'百趣演武','烟火生缘','密境行者','特惠武库配额包'})
        self.assertEqual((by['百趣演武']['end_at'],[(p['label'],p['start_at']) for p in by['百趣演武']['phases']]),
                         ('2026-11-19T04:00:00+08:00',[('内容更新','2026-11-11T04:00:00+08:00')]))
        self.assertEqual((by['烟火生缘']['start_at'],by['烟火生缘']['end_at'],by['烟火生缘']['end_rule']),('2026-10-15T12:00:00+08:00',None,'version_end'))
        self.assertEqual((by['密境行者']['end_rule'],[p['start_at'] for p in by['密境行者']['phases']]),('open',['2026-11-19T04:00:00+08:00']))
        self.assertEqual(by['特惠武库配额包']['category'],'pack')
    def test_stage_labels_become_phases_of_one_activity(self):
        found,_=a.extract(AK_TEXT,'arknights','cn',at(1),'ak')
        self.assertEqual([e['name'] for e in found],['SideStory「时间啊，向前！」活动'])
        self.assertEqual([(p['label'],p['start_at']) for p in found[0]['phases']],
                         [('第一段','2026-11-01T12:00:00+08:00'),('第二段','2026-11-08T16:00:00+08:00'),('第三段','2026-11-15T16:00:00+08:00')])
        self.assertEqual(found[0]['end_at'],'2026-11-22T03:59:00+08:00')
    def test_reminders_say_days_left_and_phases_due(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=calendar_root(tmp,[('v1','endfield','「丹青渡」版本更新说明',EF_TEXT),('ak','arknights','「感谢庆典」活动公告',AK_TEXT)])
            a.sync(root,'endfield',at(16,10),fetch=False);a.sync(root,'arknights',at(16,10),fetch=False)
            rows={r['name']:r for r in a.reminders(root,'endfield',at(17,10))}
            self.assertNotIn('【特惠武库配额包】限时礼包',rows)   # purchases are not activities
            self.assertEqual((rows['「百趣演武」挑战活动']['state'],rows['「百趣演武」挑战活动']['label']),('ending','还剩2天'))
            self.assertEqual(rows['「烟火生缘」趣味活动']['label'],'版本更新前结束')
            self.assertEqual([p['when'] for p in rows['「密境行者」空间组更新']['phases_due']],['11月19日04:00'])
            self.assertFalse(a.must_mention(rows['「密境行者」空间组更新']))
            tomorrow={r['name']:r for r in a.reminders(root,'endfield',at(18,10))}
            self.assertEqual(tomorrow['「密境行者」空间组更新']['phases_due'][0]['when'],'明天04:00')
            self.assertTrue(a.must_mention(tomorrow['「密境行者」空间组更新']))
            self.assertNotIn('「密境行者」空间组更新',{r['name'] for r in a.reminders(root,'endfield',at(21,10))})   # dropped after its last part opened
            ss=a.reminders(root,'arknights',at(15,10))[0]
            self.assertEqual((ss['name'],[p['when']+' '+p['label'] for p in ss['phases_due']]),('SideStory「时间啊，向前！」活动',['今天16:00 第三段']))
    def test_calendar_page_must_name_due_items_with_their_day(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=calendar_root(tmp,[('v1','endfield','「丹青渡」版本更新说明',EF_TEXT)])
            a.sync(root,'endfield',at(18,9),fetch=False)
            ep=dict(id='e',edition_series='endfield',edition_slot='night',scenes=[])
            with self.assertRaisesRegex(ValueError,'ACTIVITY_CALENDAR_REQUIRED'):a.require_calendar(ep,root,at(18,10))
            with self.assertRaisesRegex(ValueError,'ACTIVITY_CALENDAR_STALE'):a.require_calendar(ep,root,at(19,10))
            keys={r['name']:r['key'] for r in a.reminders(root,'endfield',at(18,10))}
            scene=dict(id='cal',scene_type='activity_calendar',game='endfield',narration='终末地活动日历。百趣演武明天四点结束。')
            with self.assertRaisesRegex(ValueError,'ACTIVITY_CALENDAR_SPOKEN'):a.bind_calendar(dict(scene),ep,root,at(18,10))
            spoken={keys['「百趣演武」挑战活动']:'百趣演武',keys['「密境行者」空间组更新']:'密境行者'}
            with self.assertRaisesRegex(ValueError,'ACTIVITY_CALENDAR_SPOKEN'):
                a.bind_calendar(dict(scene,spoken=spoken),ep,root,at(18,10))   # 密境行者 is mapped but never said
            with self.assertRaisesRegex(ValueError,'ACTIVITY_CALENDAR_DAY'):
                a.bind_calendar(dict(scene,spoken=spoken,narration=scene['narration']+'密境行者还会开放新空间。'),ep,root,at(18,10))
            ok=dict(scene,spoken=spoken,narration=scene['narration']+'密境行者明天再开三个空间。')
            result=a.bind_calendar(ok,ep,root,at(18,10))
            self.assertEqual((result['basis'],ok['badge'],ok['event_key'],ok['source_url']),('activity_calendar','活动日历','endfield-activity-calendar','https://example.test/v1'))
            self.assertEqual(sorted(r['big'] for r in ok['calendar_rows'] if r['urgent']),['!','明天'])
            news=[dict(id=f'n{i}',item_id=f'n{i}',narration='消息') for i in range(5)]
            a.require_calendar(dict(ep,scenes=news+[ok]),root,at(18,10))
    def test_short_edition_is_filled_with_the_most_pressing_activities(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=calendar_root(tmp,[('v1','endfield','「丹青渡」版本更新说明',EF_TEXT),('v2','endfield','「远山行」版本更新说明',
                               '「远山行」版本更新说明\n■ 「远山行」版本更新维护时间\n2026/11/25 06:00 - 2026/11/25 12:00（UTC+8）')])
            a.sync(root,'endfield',at(16,10),fetch=False)
            cal=dict(id='cal',scene_type='activity_calendar',game='endfield',narration='活动日历。')
            news=[dict(id='n1',item_id='n1',narration='消息'),dict(id='talk',item_id='community-x',segment='community',narration='玩家热议')]
            ep=dict(id='e',edition_series='endfield',edition_slot='night',scenes=news+[cal])
            # One message page (玩家热议 is not counted): 4 short; only rows with a deadline qualify, most pressing first.
            plan=a.fill_plan(ep,root,at(16,10),'endfield')
            self.assertEqual((plan['news_pages'],plan['need'],plan['keys']),(1,4,['endfield|cn|百趣演武','endfield|cn|烟火生缘']))
            with self.assertRaisesRegex(ValueError,'ACTIVITY_FILL: 1 message pages'):a.require_calendar(ep,root,at(16,10))
            fills=[dict(id='f2',calendar_key='endfield|cn|烟火生缘',narration='烟火生缘11月25日结束。',facts=[dict(title='参与方式',detail='登录参加')]),
                   dict(id='f1',calendar_key='endfield|cn|百趣演武',narration='百趣演武11月19日截止。',facts=[dict(title='参与方式',detail='挑战关卡')])]
            ep['scenes']=news+[cal]+fills
            a.fill_from_calendar(ep,root,at(16,10))
            item=fills[0]['activity_items'][0]
            self.assertEqual((fills[0]['item_id'],fills[0]['freshness_basis'],item['end_at'],item['end_basis']),('v1','active_window','2026-11-25T12:00:00+08:00','next_version_start'))
            check=a.calendar_check(root,item,at(16,10))
            self.assertEqual((check['ok'],check['state']),(True,'ongoing'))
            for s in fills:s['activity']=a.describe(s,s['activity_items'][0],a.calendar_check(root,s['activity_items'][0],at(16,10)),at(16,10),EF_TEXT)
            a.arrange(ep)
            self.assertEqual([s['id'] for s in ep['scenes']],['n1','talk','f1','f2','cal'])   # fills, then the full calendar
            a.validate_pages(ep,6)
            a.require_calendar(ep,root,at(16,10))
            self.assertEqual(ep['calendar_fill']['keys'],['endfield|cn|百趣演武','endfield|cn|烟火生缘'])
            # Five message pages: no fill page is asked for, and an extra one is refused.
            full=dict(ep,scenes=[dict(id=f'n{i}',item_id=f'n{i}',narration='消息') for i in range(5)]+[cal])
            a.require_calendar(full,root,at(16,10))
            with self.assertRaisesRegex(ValueError,'ACTIVITY_FILL'):a.require_calendar(dict(full,scenes=full['scenes']+fills),root,at(16,10))
    def test_editor_corrections_survive_a_resync(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=calendar_root(tmp,[('v1','endfield','「丹青渡」版本更新说明',EF_TEXT)])
            a.sync(root,'endfield',at(16,10),fetch=False)
            a.hide(root,'endfield|cn|烟火生缘','测试')
            with self.assertRaisesRegex(ValueError,'ACTIVITY_FIX_QUOTE'):a.fix(root,'endfield|cn|密境行者',dict(name='x'))
            a.fix(root,'endfield|cn|密境行者',dict(name='「密境行者」画外遗光',quote='· 更新时间：2026/11/12 12:00（服务器时间）'))
            a.sync(root,'endfield',at(16,11),fetch=False)
            names={r['name'] for r in a.reminders(root,'endfield',at(16,12))}
            self.assertIn('「密境行者」画外遗光',names);self.assertNotIn('「烟火生缘」趣味活动',names)
    def test_sync_deletes_finished_activities_from_the_file(self):
        nxt="「远山行」版本更新说明\n■ 「远山行」版本更新维护时间\n2026/11/25 06:00 - 2026/11/25 12:00（UTC+8）"
        with tempfile.TemporaryDirectory() as tmp:
            root=calendar_root(tmp,[('v1','endfield','「丹青渡」版本更新说明',EF_TEXT)])
            a.sync(root,'endfield',at(16,10),fetch=False)
            a.hide(root,'endfield|cn|特惠武库配额包','礼包')
            report=a.sync(root,'endfield',at(20,10),fetch=False)
            stored=json.loads(a.calendar_path(root).read_text(encoding='utf-8'))['activities']
            # 百趣演武 ended 11-19 04:00; 密境行者 has no end and its last part opened over a day ago; the hidden pack ended too.
            self.assertEqual(sorted(g['key'] for g in report['expired']),['endfield|cn|密境行者','endfield|cn|特惠武库配额包','endfield|cn|百趣演武'])
            self.assertEqual(sorted(stored),['endfield|cn|烟火生缘'])   # ends with a version whose end is not known yet
            self.assertEqual(report['added'],[])
            # The next version's maintenance time ends the version-bound activity.
            calendar_root_add(root,'v2','「远山行」版本更新预告',nxt)
            a.sync(root,'endfield',at(21,10),fetch=False)
            row=a.reminders(root,'endfield',at(23,10))[0]
            self.assertEqual((row['name'],row['end_at'],row['end_basis'],row['label']),('「烟火生缘」趣味活动','2026-11-25T12:00:00+08:00','next_version_start','还剩2天'))
            self.assertEqual([g['key'] for g in a.prune(root,'endfield',at(25,13))['expired']],['endfield|cn|烟火生缘'])
            self.assertEqual(json.loads(a.calendar_path(root).read_text(encoding='utf-8'))['activities'],{})
    def test_editor_adds_a_missed_activity_from_the_official_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=calendar_root(tmp,[('v1','endfield','「丹青渡」版本更新说明',EF_TEXT)])
            a.sync(root,'endfield',at(16,10),fetch=False)
            args=dict(game='endfield',region='cn',name='「画外遗光」探索奖励',start_at='2026-11-12T12:00:00+08:00',item_id='v1',end_at='2026-11-26T04:00:00+08:00')
            with self.assertRaisesRegex(ValueError,'ACTIVITY_QUOTE'):a.add(root,quote='编造的句子',reference=at(16,11),**args)
            with self.assertRaisesRegex(ValueError,'ACTIVITY_END'):a.add(root,quote='· 更新时间：2026/11/12 12:00（服务器时间）',open_end=True,reference=at(16,11),**args)
            with self.assertRaisesRegex(ValueError,'ACTIVITY_SOURCE'):a.add(root,quote='x',reference=at(16,11),**dict(args,item_id='nope'))
            with self.assertRaisesRegex(ValueError,'ACTIVITY_EXISTS'):
                a.add(root,quote='· 更新时间：2026/11/12 12:00（服务器时间）',reference=at(16,11),**dict(args,name='「百趣演武」挑战活动'))
            with self.assertRaisesRegex(ValueError,'ACTIVITY_ENDED'):
                a.add(root,quote='· 更新时间：2026/11/12 12:00（服务器时间）',reference=at(27),**args)
            added=a.add(root,quote='· 更新时间：2026/11/12 12:00（服务器时间）',reference=at(16,11),**args)
            self.assertEqual((added['origin'],added['end_rule'],added['category']),('editor_added','fixed','event'))
            a.sync(root,'endfield',at(20,10),fetch=False)   # kept across a resync
            self.assertIn('「画外遗光」探索奖励',{r['name'] for r in a.reminders(root,'endfield',at(20,11))})
            self.assertIn(added['key'],[g['key'] for g in a.sync(root,'endfield',at(26,5),fetch=False)['expired']])
    def test_reported_single_activity_page_enters_the_calendar(self):
        with tempfile.TemporaryDirectory() as tmp:
            a.record(dict(id='e1',scenes=[bound('签到',20),bound('网页投稿',12,scale='minor')]),tmp)
            self.assertEqual([(r['name'],r['label']) for r in a.running(tmp,'endfield',NOW)],[('网页投稿','还剩2天'),('签到','还剩10天')])
            self.assertEqual([r['name'] for r in a.running(tmp,'endfield',at(15))],['签到'])
            self.assertEqual(a.running(tmp,'arknights',NOW),[])

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
