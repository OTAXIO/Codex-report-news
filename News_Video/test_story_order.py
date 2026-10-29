import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import production_policy as p
from layout_policy import prepare_overview
import news_video as n

def ai(identity='ai',**kw):
    return dict(id=identity,event_key=identity,section='AI 动态',narration='公司发布了消息。',title=identity,**kw)

def game(identity='game',**kw):
    return dict(id=identity,event_key=identity,item_id=identity,section='游戏资讯',game='arknights',
                game_region='cn',game_topic='update',narration='明日方舟公布更新。',title=identity,**kw)

def major(scene):
    scene['source_url']='https://example.org/'+scene['id']
    scene['importance_review']=dict(verified=True,category='game_update' if scene.get('game') else 'model_release',
                                   reason='Verified formal release, not a preview or teaser',quote='official release',source_url=scene['source_url'])
    return scene

def episode(scenes,**kw):
    return dict(edition_slot=kw.pop('edition_slot','night'),production_policy_version=4,scenes=scenes,**kw)

class StoryOrderChecks(unittest.TestCase):
    def test_morning_ai_first_guide_transitions_and_navigation(self):
        ep=episode([game(),ai(),ai('second')],edition_slot='morning')
        p.apply_story_order(ep);prepare_overview(ep);p.validate_content(ep)
        self.assertEqual([s['id'] for s in ep['scenes']],['overview','ai','second','game'])
        self.assertEqual(ep['scenes'][0]['facts'][0]['scene_id'],'ai')
        self.assertEqual(ep['story_order']['default_order'],['ai','games'])
        self.assertTrue(ep['scenes'][1]['narration'].startswith('先来看AI动态。'))
        self.assertTrue(ep['scenes'][-1]['narration'].startswith('接下来是游戏资讯。'))
        self.assertEqual(p.modules(ep,[dict(start=i*10) for i in range(4)],40),
                         [('ai','AI 动态',0,30),('games','游戏资讯',30,40)])
        snapshot=copy.deepcopy(ep);p.apply_story_order(ep);prepare_overview(ep);self.assertEqual(ep,snapshot)

    def test_morning_major_game_then_ai_then_remaining_games(self):
        ep=episode([game(),ai(),major(game('release'))],edition_slot='morning',lead_event_id='release')
        p.apply_story_order(ep);prepare_overview(ep);p.validate_content(ep)
        self.assertEqual([s['id'] for s in ep['scenes']],['overview','release','ai','game'])
        self.assertEqual(p.modules(ep,[dict(start=i*10) for i in range(4)],40),
                         [('headline','头条',0,20),('ai','AI 动态',20,30),('games','游戏资讯',30,40)])

    def test_morning_company_then_leader_before_games(self):
        ep=episode([ai('leader',source_type='leader_x',company='OpenAI'),game(),ai(company='OpenAI'),ai('other',company='Google')],edition_slot='morning')
        p.apply_story_order(ep)
        self.assertEqual([s['id'] for s in ep['scenes']],['ai','leader','other','game'])

    def test_slot_lead_eligibility_scarcity_and_frozen_plan(self):
        ep=episode([game(),ai()],edition_slot='morning',lead_event_id='game')
        with self.assertRaisesRegex(ValueError,'lead_event_id'):p.apply_story_order(ep)
        ep=episode([game()],edition_slot='morning');p.apply_story_order(ep)
        self.assertEqual(ep['lead_event_id'],'game')
        ep=episode([ai(),game()],edition_slot='morning',story_order=dict(version=3,default_order=['games','ai']))
        p.apply_story_order(ep)
        self.assertEqual([s['id'] for s in ep['scenes']],['game','ai'])

    def test_morning_selected_ai_lead_keeps_its_leader_adjacent(self):
        ep=episode([ai('other',company='Google'),game(),ai('company',company='OpenAI'),
                    ai('leader',source_type='leader_x',company='OpenAI')],edition_slot='morning',lead_event_id='company')
        p.apply_story_order(ep)
        self.assertEqual([s['id'] for s in ep['scenes']],['company','leader','other','game'])

    def test_slot_config_and_invalid_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            n.dump(root/'config.json',dict(editorial=dict(story_order=dict(by_slot=dict(morning=['ai','games'],night=['games','ai'])))))
            for slot,first in [('morning','ai'),('night','game')]:
                ep=episode([game(),ai()],edition_slot=slot);p.apply_story_order(ep,root)
                self.assertEqual(ep['lead_event_id'],first)
            n.dump(root/'config.json',dict(editorial=dict(story_order=dict(by_slot=dict(morning=['ai','ai'])))))
            with self.assertRaisesRegex(ValueError,'exactly once'):p.apply_story_order(episode([ai(),game()],edition_slot='morning'),root)

    def test_games_first_guide_and_idempotent_transitions(self):
        ep=episode([ai(),game(),game('another')]);p.apply_story_order(ep);prepare_overview(ep)
        p.validate_content(ep)
        self.assertEqual([s['id'] for s in ep['scenes']],['overview','game','another','ai'])
        self.assertEqual(ep['scenes'][0]['facts'][0]['scene_id'],'game')
        self.assertTrue(ep['scenes'][1]['narration'].startswith('先来看游戏资讯。'))
        self.assertTrue(ep['scenes'][-1]['narration'].startswith('接下来是AI动态。'))
        snapshot=copy.deepcopy(ep);p.apply_story_order(ep);prepare_overview(ep);self.assertEqual(ep,snapshot)

    def test_ai_headline_then_games_then_ai_and_three_navigation_groups(self):
        ep=episode([ai('normal'),game(),major(ai('release'))],lead_event_id='release')
        p.apply_story_order(ep);prepare_overview(ep);p.validate_content(ep)
        self.assertEqual([s['id'] for s in ep['scenes']],[ 'overview','release','game','normal'])
        ranges=p.modules(ep,[dict(start=i*10) for i in range(4)],40)
        self.assertEqual(ranges,[('headline','头条',0,20),('games','游戏资讯',20,30),('ai','AI 动态',30,40)])
        p.validate_lead_contract(ep,dict(lead_event_id='release'),dict(lead_event_id='release'))
        with self.assertRaisesRegex(ValueError,'cover'):p.validate_lead_contract(ep,dict(lead_event_id='release'),dict(lead_event_id='normal'))

    def test_game_headline_other_majors_and_no_duplicate_events(self):
        ep=episode([ai(),game(),major(game('update')),major(ai('model'))],lead_event_id='update')
        p.apply_story_order(ep)
        self.assertEqual([s['id'] for s in ep['scenes']],['update','model','game','ai'])
        self.assertEqual(len(ep['story_order']['event_ids']),4)

    def test_multiple_pages_and_more_than_four_games_not_capped(self):
        games=[game(str(i)) for i in range(7)]
        second=dict(games[0],id='page2',page_number=2);games[0]['page_number']=1
        ep=episode([ai()]+games+[second]);p.apply_story_order(ep);p.validate_content(ep)
        self.assertEqual([s['id'] for s in ep['scenes']][:2],['0','page2'])
        self.assertEqual(len(ep['story_order']['event_ids']),8)
        self.assertEqual(len(ep['scenes']),9)

    def test_keywords_do_not_grant_priority_and_invalid_lead_rejected(self):
        ep=episode([dict(ai(),title='重大新模型即将发布'),game()]);p.apply_story_order(ep)
        self.assertEqual(ep['lead_event_id'],'game')
        ep['lead_event_id']='ai'
        with self.assertRaisesRegex(ValueError,'lead_event_id'):p.apply_story_order(ep)

    def test_major_review_bound_to_archived_quote(self):
        scene=major(ai(item_id='post'))
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);folder=root/'data/articles';folder.mkdir(parents=True)
            (folder/'post.json').write_text(json.dumps(dict(text='A speculative teaser.')))
            with self.assertRaisesRegex(ValueError,'archived'):p.apply_story_order(episode([scene,game()]),root)
            (folder/'post.json').write_text(json.dumps(dict(text='An official release today.')))
            ep=episode([scene,game()]);p.apply_story_order(ep,root);self.assertEqual(ep['lead_event_id'],'ai')

    def test_leaders_follow_corresponding_company_after_games(self):
        ep=episode([ai('leader',source_type='leader_x',company='OpenAI'),ai('other',company='Google'),
                    ai('company',company='OpenAI'),game()])
        p.apply_story_order(ep)
        self.assertEqual([s['id'] for s in ep['scenes']],['game','other','company','leader'])

    def test_scarcity_and_temporary_keep_original_scope(self):
        ep=episode([ai()]);p.apply_story_order(ep);self.assertEqual(ep['lead_event_id'],'ai')
        temp=episode([ai()],alert_id='reset');temp['edition_slot']='temporary';before=copy.deepcopy(temp)
        p.apply_story_order(temp);self.assertEqual(temp,before)

    def test_post_plan_reordering_is_rejected_before_cover_or_release(self):
        ep=episode([game(),game('second'),ai()]);p.apply_story_order(ep)
        ep['scenes'][1:]=list(reversed(ep['scenes'][1:]))
        with self.assertRaisesRegex(ValueError,'canonical'):p.validate_lead_contract(ep)

    def test_upload_boundary_blocks_mismatched_cover_before_browser(self):
        import upload_bridge
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);ep=episode([game(),ai()]);p.apply_story_order(ep)
            n.dump(root/'episode.json',ep);n.dump(root/'publication.json',dict(lead_event_id='game'))
            n.dump(root/'cover.json',dict(lead_event_id='ai'))
            with patch.object(upload_bridge,'settings',return_value=dict(enabled=True)),patch.object(upload_bridge,'call') as browser:
                with self.assertRaisesRegex(ValueError,'cover'):upload_bridge.prepare(root,root)
                browser.assert_not_called()

    def test_recaps_merged_before_authoritative_order(self):
        import important_events as events
        event=dict(kind='model',episode_id='tmp',url='https://example.org/post',event_key='recap',scene=ai('recap',item_id='original'))
        ep=episode([ai(),game()],id='new',edition_date='2026-10-29')
        with patch.object(events,'recap_candidates',return_value=[event]),patch.object(events,'recap_allowed_for_event',return_value=True):
            events.prepare_main_recaps(ep,Path('.'));p.apply_story_order(ep)
        self.assertEqual([s['id'] for s in ep['scenes']],['game','ai','recap-tmp'])
        self.assertIn('回顾',ep['scenes'][-1]['narration'])

    def test_candidates_games_first_without_model_calls(self):
        stamp='2026-10-29T00:00:00+00:00'
        rows=[dict(id='ai',kind='ai',title='model',published=stamp),dict(id='game',kind='games',published=stamp,game_topic='update')]
        self.assertEqual(sorted(rows,key=n.candidate_order)[0]['id'],'game')

    def test_real_import_orders_after_merge_and_persists_canonical_plan(self):
        for slot,order in [('morning',['ai','game']),('night',['game','ai'])]:
            with self.subTest(slot=slot):self.check_real_import(slot,order)

    def check_real_import(self,slot,order):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);n.dump(root/'config.json',dict(editorial=dict(include_important_recaps=False),publication_preset={}))
            s=game(source_url='https://example.org/game',evidence=['Official announcement'],selection_reason='Fresh meaningful update')
            n.dump(root/'data/game-items/game.json',s)
            n.dump(root/'input.json',dict(episode([ai(),s],edition_slot=slot),id='fixture',producer='Codex current conversation'))
            with patch.object(n,'ROOT',root):
                db=n.database();db.execute('INSERT INTO items VALUES(?,?,?,?,?,?,?,?,?,?,?)',('game','official','Official','games','Update',s['source_url'],'2026-10-29T00:00:00+00:00','body','','','hash'));db.commit();db.close()
                n.import_editorial(root/'input.json')
            saved=n.load(root/'episodes/fixture/episode.json')
            self.assertEqual([s['id'] for s in saved['scenes']],['overview']+order)
            self.assertEqual(saved['story_order']['event_ids'],order)
            self.assertEqual(saved['story_order']['edition_slot'],slot)
            self.assertEqual(saved['scenes'][0]['facts'][0]['scene_id'],order[0])

if __name__=='__main__':unittest.main()
