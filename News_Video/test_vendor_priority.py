import unittest
import news_video as n
class VendorPriorityChecks(unittest.TestCase):
    def test_requested_brands_first_and_no_item_cap(self):
        cfg=n.config();self.assertEqual(cfg['editorial']['preferred_vendors'][:5],['OpenAI','Anthropic','DeepSeek','Qwen','Z.ai']);self.assertIsNone(cfg['ai_item_limit']);self.assertTrue({'Google','Kimi','MiniMax'}.issubset(cfg['editorial']['preferred_vendors']))
        sources={s['id']:s for s in n.load(n.ROOT/'sources.json')}
        for key in ['openai','claude-code','deepseek','qwen-code-releases','glm-zcode']:self.assertEqual(sources[key]['priority_tier'],1)
        self.assertEqual(sources['huggingface']['selection_policy'],'supplementary_research_review')
    def test_glm_releases_have_real_dates_and_distinct_ids(self):
        body=b'<html><body>3.16.3 Released Oct 23, 2026 Release v3.16.3 Improvements 3.16.2 Released Oct 20, 2026 Previous improvements</body></html>'
        source={'id':'glm-zcode','url':'https://zcode.z.ai/en/changelog'}
        entries=n.official_bridge(body,source,'utf-8')
        self.assertEqual(len(entries),2);self.assertNotEqual(entries[0]['entry_key'],entries[1]['entry_key'])
        self.assertEqual(entries[0]['url'],source['url']);self.assertTrue(entries[0]['published'].startswith('2026-10-23'))
if __name__=='__main__':unittest.main()
