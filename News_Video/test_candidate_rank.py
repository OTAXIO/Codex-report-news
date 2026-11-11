"""2026-11-11: audience-relevance ranking, same-event groups and the review-coverage gate."""
import datetime as dt,unittest
import candidate_rank as cr

NOW=dt.datetime(2026,11,11,10,tzinfo=dt.timezone.utc)
def row(i,title,source='openai',tier=1,hours=2,kind='ai'):
    return dict(id=i,kind=kind,title=title,source_id=source,priority_tier=tier,published=(NOW-dt.timedelta(hours=hours)).isoformat())

class RankTests(unittest.TestCase):
    def rows(self):
        return [row('merch','Get your Codex edition handheld while supplies last'),
                row('reset','Pro users get one reset, and Max users get up to three resets of their weekly limits',source='x-leader-bcherny'),
                row('fable','Claude Fable 5.2 is now available',source='x-official-claudeai'),
                row('fable-media','Anthropic launches new Claude Fable 5.2 models',source='techcrunch-ai',tier=3),
                row('fable-vs','Fable 5.2 beats Gemini 4 Carbon on SimpleQA',source='reddit-singularity',tier=3),
                row('carbon','Gemini 4 Carbon is now available in the Gemini API',source='google-ai'),
                row('ember','Meta releases Muse Ember, a new lightweight model',source='techcrunch-ai',tier=3),
                row('ember2','First release of the day: Meta’s new Muse Ember beats Claude Haiku 5.5',source='rumor-x-kimmonismus',tier=3),
                row('game','明日方舟 新活动',kind='games')]

    def test_resets_and_releases_rank_above_merch(self):
        rows=cr.ordered(cr.rank(self.rows(),NOW));ai=[r['id'] for r in rows if r['kind']=='ai']
        self.assertLess(ai.index('reset'),ai.index('merch'));self.assertEqual(ai[-1],'merch')
        self.assertIn('quota_reset_or_limits',next(r for r in rows if r['id']=='reset')['rank_reasons'])
        self.assertEqual(rows[0]['kind'],'games','games keep their own order in front')

    def test_same_event_is_grouped_by_its_subject_model(self):
        rows={r['id']:r for r in cr.rank(self.rows(),NOW)}
        self.assertEqual(rows['fable']['cluster'],rows['fable-media']['cluster'])
        self.assertEqual(rows['fable-vs']['cluster'],rows['fable']['cluster'],'"X beats Y" belongs to X')
        self.assertNotEqual(rows['carbon']['cluster'],rows['fable']['cluster'])
        self.assertEqual(rows['ember']['cluster'],rows['ember2']['cluster'])
        self.assertEqual(rows['fable']['cluster_size'],3)

    def test_generic_platform_names_do_not_join_events(self):
        rows={r['id']:r for r in cr.rank([row('a','Claude Code adds hooks for teams'),row('b','Claude Code outage resolved')],NOW)}
        self.assertNotEqual(rows['a']['cluster'],rows['b']['cluster'])

class CoverageTests(unittest.TestCase):
    def test_every_top_group_needs_a_decision_and_one_reason_covers_the_group(self):
        rows=cr.ordered(cr.rank(RankTests.rows(None),NOW))
        top=cr.must_review(rows,3)
        episode=dict(scenes=[dict(item_id=top[0])],rejections={})
        with self.assertRaisesRegex(ValueError,'REVIEW_COVERAGE: 2 of the top 3'):cr.check_coverage(episode,rows,3)
        members={r['cluster']:[] for r in rows if r.get('cluster')}
        for r in rows:
            if r.get('cluster'):members[r['cluster']].append(r['id'])
        # a reason on any report of the group (not only its representative) counts
        episode['rejections']={members[c][-1]:'reason' for c in top[1:]}
        self.assertEqual(cr.check_coverage(episode,rows,3)['top_n'],3)

if __name__=='__main__':unittest.main()
