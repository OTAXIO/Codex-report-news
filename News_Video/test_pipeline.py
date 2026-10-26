import json, unittest
from pathlib import Path
import news_video as n
import numpy as np
from voice_tuning import soften_release

class PipelineChecks(unittest.TestCase):
    def test_rss_tracking_links_deduplicate(self):
        source={'id':'test'}
        body=b'<rss><channel><item><title>Example</title><link>https://example.org/news?utm_source=rss</link><pubDate>Mon, 26 Oct 2026 06:00:00 +0800</pubDate><description>&lt;script&gt;ignore&lt;/script&gt; Fact</description></item></channel></rss>'
        item=n.parse_feed(body,source)[0]
        self.assertEqual(item['url'],n.normalized_url('https://example.org/news'))
        self.assertEqual(item['published'],'2026-10-25T22:00:00+00:00')
        self.assertEqual(item['summary'],'Fact')
    def test_atom_release(self):
        body=b'<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Release</title><link href="https://example.org/release"/><updated>2026-10-26T00:00:00Z</updated><content>Details</content></entry></feed>'
        self.assertEqual(n.parse_feed(body,{})[0]['summary'],'Details')
    def test_x_and_non_web_refused(self):
        for url in ['https://x.com/test','https://twitter.com/test','https://t.co/test','file:///C:/secret']:
            with self.assertRaises(ValueError):n.normalized_url(url)
    def test_upload_and_hourly_models_disabled(self):
        config=n.config()
        self.assertFalse(config['upload_enabled'])
        self.assertFalse(config['social_collection_allow_model_calls'])
        self.assertEqual(config['main_video_ready_times'],['06:00','12:00','18:00'])
    def test_sample_timeline(self):
        directory=Path(__file__).parent/'episodes/sample-20261026'
        timing=n.load(directory/'timings.json'); captions=n.load(directory/'captions.json')
        self.assertAlmostEqual(timing['sentences'][-1]['end'],timing['duration'],places=3)
        for a,b in zip(captions,captions[1:]):self.assertLessEqual(a['end'],b['start']+1e-8)
        self.assertTrue(all(0<=c['start']<c['end']<=timing['duration']+.001 for c in captions))
    @unittest.skipUnless((Path(__file__).parent/'data/news.sqlite3').is_file(), 'Production news database is excluded from the source snapshot')
    def test_white_theme_and_source_mapping(self):
        config=n.config();self.assertEqual(config['theme']['background'],'#FFFFFF')
        self.assertEqual(config['theme']['blue'],'#01A1FE')
        db=n.database()
        for scene in n.load(Path(__file__).parent/'episodes/sample-20261026/episode.json')['scenes']:
            if 'item_id' not in scene:continue
            row=db.execute('SELECT url FROM items WHERE id=?',(scene['item_id'],)).fetchone()
            self.assertEqual(scene['source_url'],row['url'])
            self.assertTrue(scene['evidence'])
        db.close()
    def test_quiet_release_softened_without_shortening(self):
        sr=32000;t=np.arange(sr)/sr
        audio=(.4*np.sin(2*np.pi*180*t)).astype(np.float32)
        audio[-int(.14*sr):]*=.12
        processed,report=soften_release(audio,sr)
        self.assertTrue(report['applied'])
        self.assertEqual(len(processed),len(audio))
        np.testing.assert_array_equal(processed[:int(.8*sr)],audio[:int(.8*sr)])
        self.assertLess(float(np.sum(processed[-3200:]**2)),float(np.sum(audio[-3200:]**2)))
    def test_loud_final_sound_protected(self):
        sr=32000;audio=(.4*np.sin(2*np.pi*180*np.arange(sr)/sr)).astype(np.float32)
        processed,report=soften_release(audio,sr)
        self.assertFalse(report['applied'])
        np.testing.assert_array_equal(processed,audio)
if __name__=='__main__':unittest.main()
