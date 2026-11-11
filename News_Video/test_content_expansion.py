"""2026-11-09 content expansion: rumors, media, GitHub trending, activity window,
community topics, titles, descriptions and segment order. All offline."""
import datetime as dt,json,shutil,subprocess,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import news_video as n
import content_rules as c
import rumor_sources as r
import github_trending as g
import community_sources as cs
import freshness as f
import publication_policy as pp
import production_policy as prod

HERE=Path(__file__).resolve().parent
NOW=dt.datetime(2026,11,9,9,tzinfo=dt.timezone.utc)

class Root:
    """Temporary project root with the real registries."""
    def __enter__(self):
        self.tmp=tempfile.TemporaryDirectory();root=Path(self.tmp.name)
        for name in ['config.json','sources.json','rumor_sources.json','content_filter.json','game_glossary.json']:shutil.copy2(HERE/name,root/name)
        self.patch=patch.object(n,'ROOT',root);self.patch.start();self.root=root;return root
    def __exit__(self,*a):self.patch.stop();self.tmp.cleanup()

def post(handle,text,minutes=30,likes=50):
    return dict(author=handle,url='https://x.com/i/status/'+str(abs(hash((handle,text)))%10**18),text=text,
                published_at=(NOW-dt.timedelta(minutes=minutes)).strftime('%a %b %d %H:%M:%S +0000 %Y'),raw=dict(likes=likes,views=1000))

class RumorTests(unittest.TestCase):
    def store(self,root,handle,text,likes=50):
        p=r.normalize(post(handle,text,likes=likes),NOW,root=root,source_id='rumor-x-'+handle if r.tier_of(handle,root)!='C' else r.SEARCH_ID)
        db=n.database();r.store(db,p,root);db.commit();db.close();return p

    def scene(self,item_id,**kw):
        base=dict(id='s1',item_id=item_id,scene_type='rumor',title='曝GPT-6.2 Sol已在灰度测试',claim='OpenAI 正在灰度测试 GPT-6.2 Sol 模型',
                  evidence_type='tierA_source',credibility='较可信',unknowns=['发布时间'],official_status='未回应',rumor_safety_checked=True,
                  narration='X 上爆料账号 btibor91 称，ChatGPT 网页代码里出现了 GPT-6.2 Sol 的字样。目前 OpenAI 官方尚未回应。')
        base.update(kw);return base

    def test_tier_a_source_passes_and_attribution_is_required(self):
        with Root() as root:
            p=self.store(root,'btibor91','ChatGPT web app now references "gpt-6.2-sol" in its model picker code')
            audit=r.validate_scene(self.scene(p['id']),root)
            self.assertEqual(audit['sources'][0]['tier'],'A')
            with self.assertRaisesRegex(ValueError,'RUMOR_ATTRIBUTION_REQUIRED'):
                r.validate_scene(self.scene(p['id'],narration='ChatGPT 网页代码里出现了 GPT-6.2 Sol。目前 OpenAI 官方尚未回应。'),root)
            with self.assertRaisesRegex(ValueError,'RUMOR_OFFICIAL_STATUS_REQUIRED'):
                r.validate_scene(self.scene(p['id'],narration='X 上爆料账号 btibor91 称，代码里出现了 GPT-6.2 Sol。大家可以期待一下。'),root)

    def test_rumor_cannot_be_stated_as_fact(self):
        with Root() as root:
            p=self.store(root,'btibor91','gpt-6.2-sol string found in ChatGPT')
            bad='X 上爆料账号 btibor91 称，GPT-6.2 Sol 已经确认上线，消息实锤。目前 OpenAI 官方尚未回应。'
            with self.assertRaisesRegex(ValueError,'RUMOR_STATED_AS_FACT'):r.validate_scene(self.scene(p['id'],narration=bad),root)
            self.assertEqual(c.rumor_affirmations('目前官方尚未确认，也未经证实。'),[])

    def test_single_low_tier_source_needs_corroboration(self):
        with Root() as root:
            p=self.store(root,'someone','GPT-6.2 Sol leaked, coming next week',likes=500)
            self.assertEqual(p['tier'],'C')
            narration='X 用户 someone 爆料称，GPT-6.2 Sol 下周发布。目前 OpenAI 官方尚未回应。'
            with self.assertRaisesRegex(ValueError,'no tier-A source'):r.validate_scene(self.scene(p['id'],narration=narration),root)
            with self.assertRaisesRegex(ValueError,'two independent authors'):
                r.validate_scene(self.scene(p['id'],narration=narration,evidence_type='two_independent',credibility='待观察'),root)
            q=self.store(root,'another','Hearing GPT-6.2 Sol ships next week',likes=300)
            with self.assertRaisesRegex(ValueError,'two C-tier posts cannot be 较可信'):
                r.validate_scene(self.scene(p['id'],narration=narration,evidence_type='two_independent',rumor_sources=[q['id']]),root)
            r.validate_scene(self.scene(p['id'],narration=narration,evidence_type='two_independent',credibility='待观察',rumor_sources=[q['id']]),root)

    def test_artifact_quote_and_quote_card_come_from_the_post(self):
        with Root() as root:
            p=self.store(root,'legit_api','New model id spotted in API list: gemini-4-pro-preview')
            narration='X 上爆料账号 legit_api 称，API 模型列表里出现了 gemini-4-pro-preview。目前 Google 官方尚未回应。'
            with self.assertRaisesRegex(ValueError,'artifact'):
                r.validate_scene(self.scene(p['id'],narration=narration,evidence_type='artifact',artifact=dict(kind='api_list',quote='gemini-5')),root)
            scene=self.scene(p['id'],narration=narration,evidence_type='artifact',artifact=dict(kind='api_list',quote='gemini-4-pro-preview'),
                             quote_card=dict(account='@legit_api',time_label='11月9日 16:30',excerpt='New model id spotted in API list',translation='API 列表中发现新模型 ID'),facts=[])
            r.validate_scene(scene,root)
            self.assertTrue(scene['facts'][0]['quote_card']);self.assertIn('译：',scene['facts'][0]['detail'])
            with self.assertRaisesRegex(ValueError,'RUMOR_QUOTE_CARD'):
                r.validate_scene(self.scene(p['id'],narration=narration,evidence_type='artifact',artifact=dict(kind='api_list',quote='gemini-4-pro-preview'),quote_card=dict(excerpt='invented text')),root)

    def test_collect_stops_on_block_and_filters_noise(self):
        with Root() as root:
            calls=[]
            def runner(args):
                calls.append(args)
                if args[1]=='tweets':return dict(ok=True,items=[post(args[2],'GPT-6.2 Sol model picker string spotted in the app')])
                return dict(ok=False,error=dict(code='RATE_LIMITED',retry_after_seconds=600))
            report=r.collect(runner=runner,sleep=lambda s:None,root=root,now=NOW)
            self.assertTrue(report['stopped']);self.assertEqual(report['reason'],'RATE_LIMITED')
            self.assertEqual(sum(1 for a in calls if a[1]=='search'),1,'stop the channel on the first block')
            self.assertEqual(report['accepted'],len(r.accounts(root)))
            again=r.collect(runner=runner,sleep=lambda s:None,root=root,now=NOW)
            self.assertEqual(again['reason'],'COOLDOWN')

    def test_ledger_blocks_repeats_without_new_evidence(self):
        with Root() as root:
            p=self.store(root,'btibor91','gpt-6.2-sol in ChatGPT code')
            ep=dict(id='daily-20261109-morning',scenes=[self.scene(p['id'])])
            r.record_ledger(r.check_ledger(ep,root,NOW),root,NOW)
            later=dict(id='daily-20261110-morning',scenes=[self.scene(p['id'])])
            with self.assertRaisesRegex(ValueError,'RUMOR_REPEATED'):r.check_ledger(later,root,NOW+dt.timedelta(days=1))
            key=ep['scenes'][0]['rumor_key']
            follow=dict(id='daily-20261111-morning',scenes=[dict(item_id='x',scene_type='official',narration='此前的传闻今天官宣了，OpenAI 发布 GPT-6.2 Sol。',resolves_rumor=dict(key=key,status='confirmed'))])
            r.record_ledger(r.check_ledger(follow,root,NOW),root,NOW)
            self.assertEqual(r.ledger(root)[key]['status'],'confirmed')

class GitHubTests(unittest.TestCase):
    PAGE='''<article class="Box-row"><h2><a href="/sherlock-project/sherlock">x</a></h2><p class="col-9 color-fg-muted">Hunt down social media accounts by username across social networks</p>
    <span itemprop="programmingLanguage">Python</span><a href="/sherlock-project/sherlock/stargazers">70,100</a> 1,900 stars today</article>
    <article class="Box-row"><h2><a href="/anthropics/skills">x</a></h2><p class="col-9 color-fg-muted">Public repository for Agent Skills</p>
    <span itemprop="programmingLanguage">Python</span><a href="/anthropics/skills/stargazers">30,000</a> 1,200 stars today</article>'''

    def test_parse_and_safety_filter(self):
        rows=g.parse(self.PAGE)
        self.assertEqual([x['repo'] for x in rows],['sherlock-project/sherlock','anthropics/skills'])
        self.assertEqual(rows[0]['stars_today'],1900)
        self.assertEqual(g.judge(rows[0]),(False,'unsafe_or_harmful_purpose'))
        self.assertEqual(g.judge(rows[1]),(True,'ai'))
        self.assertEqual(g.judge(dict(repo='x/cooking-recipes',description='family recipes')),(False,'not_ai_or_developer_tool'))

    def test_collect_picks_the_safe_ai_repo(self):
        with Root() as root:
            def fetch(url):
                if 'trending' in url:return self.PAGE.encode(),url,'utf-8'
                if 'api.github.com' in url:return json.dumps(dict(license=dict(spdx_id='MIT'),topics=['agents'],stargazers_count=30000)).encode(),url,'utf-8'
                if 'raw.githubusercontent' in url:return b'# Skills\nAgent skills for Claude.',url,'utf-8'
                raise OSError('no card offline')
            report=g.collect(root,fetch,NOW)
            self.assertEqual([x['repo'] for x in report['chosen']],['anthropics/skills'])
            self.assertIn('unsafe_or_harmful_purpose',[s['reason'] for s in report['skipped']])
            item=report['chosen'][0]['id']
            scene=dict(item_id=item,scene_type='github_trending',repo='anthropics/skills',stars_today=1200,title='今日 GitHub 热门：Agent Skills',
                       narration='最后来看今天 GitHub 上最热门的 AI 项目 skills，它由 Anthropic 发布，今天新增了一千二百颗星。'+'这个仓库收录了一批可以直接给智能体使用的技能模板，包括文档处理、表格和演示文稿等，开发者可以按 README 的说明把技能装进自己的工作流里。')
            g.validate_scene(scene,root,NOW,'daily-20261109-morning')
            g.record_featured(dict(id='daily-20261109-morning',scenes=[scene]),root,NOW)
            with self.assertRaisesRegex(ValueError,'GITHUB_REPEATED'):g.validate_scene(dict(scene),root,NOW+dt.timedelta(days=2),'daily-20261111-morning')
            with self.assertRaisesRegex(ValueError,'GITHUB_STARS_MISMATCH'):g.validate_scene(dict(scene,stars_today=5000),root,NOW,'x')

class ActivityWindowTests(unittest.TestCase):
    def test_window_overlap_quotes_and_order(self):
        with Root() as root:
            (root/'data/game-items').mkdir(parents=True)
            text='活动时间：11月5日 16:00 - 11月11日 03:59'
            n.dump(root/'data/game-items/a.json',dict(summary=text,title='活动'))
            ev=dict(original_published_at=(NOW-dt.timedelta(days=5)).isoformat())
            ok=f.window_check(root,'a','2026-11-05T16:00:00+08:00','2026-11-11T03:59:00+08:00',text,NOW,7,30,ev,'official_game_page')
            self.assertTrue(ok['ok']);self.assertEqual(ok['state'],'ending')
            self.assertEqual(f.window_check(root,'a','2026-11-05T16:00:00+08:00','2026-11-11T03:59:00+08:00','活动时间：11月5日',NOW,7,30,ev,'official_game_page')['reason'],'active_window_quote_lacks_start_and_end_dates')
            old=dict(original_published_at=(NOW-dt.timedelta(days=40)).isoformat())
            self.assertEqual(f.window_check(root,'a','2026-11-05T16:00:00+08:00','2026-11-11T03:59:00+08:00',text,NOW,7,30,old,'official_game_page')['reason'],'announcement_too_old_for_active_window')
            self.assertEqual(f.window_check(root,'a','2026-11-05T16:00:00+08:00','2026-11-11T03:59:00+08:00',text,NOW,7,30,ev,'community')['reason'],'active_window_not_official_game_source')
            later='活动时间：11月20日 16:00 - 11月30日 03:59'
            n.dump(root/'data/game-items/b.json',dict(summary=later))
            self.assertEqual(f.window_check(root,'b','2026-11-20T16:00:00+08:00','2026-11-30T03:59:00+08:00',later,NOW,7,30,ev,'official_game_page')['reason'],'activity_outside_window')

class CommunityTests(unittest.TestCase):
    def snapshot(self,root,series='endfield',titles=('明河配队心得【终末地】',),texts=None):
        texts=texts if texts is not None else ['明河真的强']*0+[f'明河第{i}条讨论' for i in range(8)]+[f'活动奖励不错{i}' for i in range(30)]
        videos=[dict(bvid=f'BV{i}',title=t,plays=9000,published=NOW.isoformat(),comments_hot=[dict(text=x,likes=1,sort='hot') for x in texts],comments_newest=[],danmaku=[]) for i,t in enumerate(titles)]
        snap=dict(id='snap1',source_id='community-'+series,game=series,videos=videos,collected_at=NOW.isoformat())
        n.dump(root/'data/community/snap1.json',snap);return snap

    def scene(self,**kw):
        base=dict(item_id='snap1',scene_type='community_pulse',game='endfield',subject=dict(game='endfield',entity_type='character',entity_name='明河'),
                  videos=['BV0'],sample_count=38,quotes=['明河第1条讨论'],title='明河强度讨论',
                  narration='B站玩家最近在聊明河：38条样本里，不少高赞评论认为明河很强，也有人觉得还要再观察。')
        base.update(kw);return base

    def episode(self,scenes):return dict(edition_series='endfield',scenes=scenes)

    def test_topic_must_belong_to_this_game(self):
        with Root() as root:
            self.snapshot(root)
            sc=self.scene();cs.validate_scene(sc,self.episode([sc]),root)
            self.assertEqual(sc['community_audit']['mentions'],8)
            with self.assertRaisesRegex(ValueError,'COMMUNITY_SUBJECT_MISMATCH'):
                bad=self.scene(subject=dict(game='endfield',entity_type='character',entity_name='阿米娅'));cs.validate_scene(bad,self.episode([bad]),root)
            with self.assertRaisesRegex(ValueError,'COMMUNITY_SUBJECT_MISMATCH'):
                bad=self.scene(subject=dict(game='endfield',entity_type='character',entity_name='弭弗'));cs.validate_scene(bad,self.episode([bad]),root)
            with self.assertRaisesRegex(ValueError,'COMMUNITY_SUBJECT_MISMATCH'):
                bad=self.scene(game='arknights',subject=dict(game='arknights',entity_type='character',entity_name='阿米娅'));cs.validate_scene(bad,self.episode([bad]),root)

    def test_page_picture_is_the_discussed_video_cover(self):
        from PIL import Image
        with Root() as root:
            snap=self.snapshot(root,titles=('明河配队心得【终末地】','终末地活动奖励一览'),
                               texts=None)
            snap['videos'][1]['comments_hot']=[dict(text=f'明河第{i}条讨论',likes=1,sort='hot') for i in range(20)]
            for v in snap['videos']:
                path=root/'assets/community'/(v['bvid']+'.jpg');path.parent.mkdir(parents=True,exist_ok=True)
                Image.new('RGB',(640,360),'red').save(path)
                v.update(cover='assets/community/'+v['bvid']+'.jpg',cover_sha256=cs.hashlib.sha256(path.read_bytes()).hexdigest())
            n.dump(root/'data/community/snap1.json',snap)
            sc=self.scene(videos=['BV0','BV1'])
            self.assertEqual(cs.assign_image(sc,root),'BV1')  # most mentions of 明河
            self.assertEqual((sc['image'],sc['image_source_url']),('assets/community/BV1.jpg','https://www.bilibili.com/video/BV1'))
            with self.assertRaisesRegex(ValueError,'COMMUNITY_IMAGE'):cs.assign_image(self.scene(image='assets/logos/endfield-identity.png'),root)
            (root/'assets/community/BV0.jpg').write_bytes(b'x')
            with self.assertRaisesRegex(ValueError,'COMMUNITY_IMAGE'):cs.assign_image(self.scene(videos=['BV0'],image='assets/community/BV0.jpg'),root)

    def test_wrong_game_video_and_thin_samples_are_rejected(self):
        with Root() as root:
            self.snapshot(root,titles=('危机合约新赛季【明日方舟】',))
            with self.assertRaisesRegex(ValueError,'not about endfield'):cs.validate_scene(self.scene(),self.episode([self.scene()]),root)
            self.snapshot(root,texts=[f'明河第{i}条' for i in range(6)])
            with self.assertRaisesRegex(ValueError,'COMMUNITY_SAMPLES'):cs.validate_scene(self.scene(),self.episode([self.scene()]),root)

    def test_quotes_labels_and_filter(self):
        with Root() as root:
            self.snapshot(root)
            for kw,code in [(dict(quotes=['编造的一句话']),'COMMUNITY_QUOTE_INVALID'),(dict(quotes=['明河第1条讨论'*3]),'COMMUNITY_QUOTE_INVALID'),
                            (dict(narration='明河很强。38条。'),'COMMUNITY_OPINION_LABEL'),(dict(sample_count=10),'COMMUNITY_SAMPLE_COUNT')]:
                with self.assertRaisesRegex(ValueError,code):sc=self.scene(**kw);cs.validate_scene(sc,self.episode([sc]),root)
        self.assertEqual(c.screen('我裤子爆炸了'),['vulgar'])
        self.assertIn('abuse',c.screen('你就是个SB'))
        self.assertEqual(c.screen('USB 接口和爬塔攻略'),[])

    def test_video_choice_window_topic_and_floor(self):
        with Root() as root:
            searches=[dict(label='hot',cards=[dict(title='明河：我已悟出最强一剑【终末地】',bvid='BV1',stats=['9126','31'],date='40分钟前'),
                                              dict(title='朋友查电表，发现媳妇出轨了',bvid='BV2',stats=['802','0'],date='57分钟前'),
                                              dict(title='【终末地】我裤子爆炸了！',bvid='BV3',stats=['878','4'],date='1小时前'),
                                              dict(title='终末地定档PV',bvid='BV4',stats=['1384.3万','8.3万'],date='2025年12月11日')]),
                      dict(label='newest',cards=[dict(title='终末地剧情截取2039',bvid='BV5',stats=['0','0'],date='刚刚'),
                                                 dict(title='终末地1.6新版本打击感',bvid='BV6',stats=['350','2'],date='5分钟前')])]
            chosen,report=cs.choose_videos('endfield',searches,NOW,root)
            self.assertEqual([v['bvid'] for v in chosen],['BV1','BV6'])
            reasons={x['bvid']:x['reason'] for x in report}
            self.assertEqual((reasons['BV2'],reasons['BV3'],reasons['BV4'],reasons['BV5']),('other_topic','content_filter','outside_48h','below_engagement_floor'))
            self.assertFalse(cs.title_matches('arknights','明日方舟：终末地 新版本',root))
            self.assertEqual(cs.count('1.2万'),12000)
            self.assertEqual(cs.card_time('2天前',NOW),NOW-cs.dt.timedelta(days=2))

    def test_hot_search_keeps_the_48h_filter(self):
        """B站 drops pubtime_* under order=click, so hot pages must use the default order."""
        with Root() as root:
            jobs=cs.search_jobs('endfield',NOW,root)
            hot=[j['url'] for j in jobs if j['label']=='hot']
            self.assertGreaterEqual(len(hot),2)
            self.assertTrue(all('pubtime_begin_s=' in u and 'order=click' not in u for u in hot))
            self.assertEqual(len(set(hot)),len(hot))
            self.assertEqual([j['label'] for j in jobs][-1],'newest')

class TitleAndDescriptionTests(unittest.TestCase):
    def episode(self,lead_type=None,lead_title='曝GPT-6.2 Sol灰度'):
        scenes=[dict(id='overview',scene_type='overview',title='导览'),
                dict(id='a',item_id='a',title=lead_title,scene_type=lead_type,narration='爆料称 GPT-6.2 Sol 正在灰度。官方尚未回应。',source_url='https://x.com/a/status/1'),
                dict(id='b',item_id='b',title='Claude 新功能上线',narration='Anthropic 发布新功能。',source_url='https://anthropic.com/news/x')]
        return dict(edition_series='ai',edition_date='2026-11-09',lead_event_id='a',scenes=scenes)

    def test_rumor_marker_hook_and_banned_words(self):
        ep=self.episode('rumor')
        pub=dict(title_groups=[dict(kind='ai',event_ids=['a','b'])])
        self.assertEqual(pp.title_for(ep,pub),'曝GPT-6.2 Sol灰度、Claude 新功能上线｜AI早报 11.9')
        with self.assertRaisesRegex(ValueError,'TITLE_RUMOR_MARKER'):pp.title_for(self.episode('rumor','GPT-6.2 Sol灰度'),pub)
        with self.assertRaisesRegex(ValueError,'RUMOR_STATED_AS_FACT'):pp.title_for(self.episode('rumor','曝GPT-6.2 Sol实锤'),pub)
        with self.assertRaisesRegex(ValueError,'PUBLIC_WORD_BANNED'):pp.title_for(self.episode(None,'震惊！新模型'),pub)
        hooked=dict(pub,title_hook='OpenAI还没认',title_hook_evidence=['OpenAI'])
        with self.assertRaisesRegex(ValueError,'TITLE_HOOK_UNSUPPORTED'):pp.title_for(ep,hooked)
        hooked=dict(pub,title_hook='官方还没回应',title_hook_evidence=['官方'])
        self.assertTrue(pp.title_for(ep,hooked).startswith('官方还没回应 曝GPT-6.2 Sol灰度'))
        with self.assertRaisesRegex(ValueError,'TITLE_HOOK_INVALID'):pp.title_for(ep,dict(pub,title_hook='这是一个非常非常非常长的标题钩子短语',title_hook_evidence=['官方']))

    def test_description_is_generated_and_never_empty(self):
        ep=self.episode('rumor')
        text=pp.describe(ep,{},dict(sentences=[dict(scene_id='a',start=3.2),dict(scene_id='b',start=65)]))
        self.assertIn('00:03 曝GPT-6.2 Sol灰度',text);self.assertIn('01:05 Claude 新功能上线',text)
        self.assertIn('https://anthropic.com/news/x',text);self.assertIn('传闻内容未经官方证实',text)
        self.assertEqual(pp.describe(ep,dict(description='自己写的简介')),'自己写的简介')
        with self.assertRaisesRegex(ValueError,'DESCRIPTION_REQUIRED'):pp.describe(ep,dict(description='x'*2001))

class SegmentOrderTests(unittest.TestCase):
    def test_ai_series_runs_rumor_media_official_github(self):
        scenes=[dict(id='o',item_id='o',segment='official',company='OpenAI',narration='官方。',title='官方'),
                dict(id='g',item_id='g',segment='github',narration='GitHub。',title='GitHub'),
                dict(id='m',item_id='m',segment='media',narration='据报道。',title='媒体'),
                dict(id='r',item_id='r',segment='rumor',narration='爆料称。',title='传闻')]
        ep=dict(edition_slot='morning',edition_series='ai',scenes=scenes)
        prod.apply_story_order(ep)
        self.assertEqual(ep['story_order']['event_ids'],['r','m','o','g'])
        self.assertEqual([s['navigation_group'] for s in ep['scenes']],['rumor','media','ai','github'])
        modules=prod.modules(ep,[dict(start=i*10) for i in range(4)],40)
        self.assertEqual([m[1] for m in modules],['传闻','媒体报道','AI 动态','GitHub热门'])
        with self.assertRaisesRegex(ValueError,'LEAD_SEGMENT'):prod.apply_story_order(dict(edition_slot='morning',edition_series='ai',lead_event_id='g',scenes=[dict(s) for s in scenes]))

    def test_game_series_runs_official_activities_community(self):
        base=dict(game='endfield',game_region='cn',game_topic='event')
        scenes=[dict(id='c',item_id='c',segment='community',narration='玩家。',title='热议',**base),dict(id='a',item_id='a',segment='activities',narration='活动。',title='活动',**base),
                dict(id='o',item_id='o',segment='official',narration='官方。',title='官方',**base)]
        ep=dict(edition_slot='night',edition_series='endfield',scenes=scenes)
        prod.apply_story_order(ep)
        self.assertEqual(ep['story_order']['event_ids'],['o','a','c'])

class ReaderFixtureTest(unittest.TestCase):
    def test_shadow_dom_reader(self):
        try:rt=cs.runtime(HERE)
        except Exception as error:self.skipTest('no runtime: '+str(error))
        if not rt.get('puppeteer_module') or not Path(rt['puppeteer_module']).is_file() or not rt.get('browser_executable'):self.skipTest('puppeteer/Chrome not installed here')
        result=subprocess.run([rt['node'] if shutil.which(rt['node']) or Path(rt['node']).is_file() else 'node',str(HERE/'test_community_reader.mjs'),rt['puppeteer_module'],rt['browser_executable']],
                              capture_output=True,text=True,encoding='utf-8',timeout=180)
        self.assertEqual(result.returncode,0,result.stderr[-800:])

if __name__=='__main__':unittest.main()
