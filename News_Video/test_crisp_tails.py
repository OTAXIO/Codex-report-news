import json, os, tempfile, unittest
from unittest.mock import patch
from pathlib import Path
os.environ['NUMBA_CACHE_DIR']=str(Path(__file__).parent/'.cache/numba')
import numpy as np
from crisp_tails import crisp_release,process,write_wav,read_wav

class CrispReleaseChecks(unittest.TestCase):
    def test_release_shorter_but_pitch_and_prefix_preserved(self):
        sr=32000;t=np.arange(sr*2)/sr
        x=(.3*np.sin(2*np.pi*180*t)).astype(np.float32)
        y,r=crisp_release(x,sr)
        self.assertTrue(r['applied']);self.assertLess(len(y),len(x))
        np.testing.assert_array_equal(x[:r['prefix_samples_unchanged']],y[:r['prefix_samples_unchanged']])
        n=round(r['processed_voiced_seconds']*sr);start=r['prefix_samples_unchanged']
        segment=y[start:start+n];frequency=np.fft.rfftfreq(len(segment),1/sr)[np.argmax(abs(np.fft.rfft(segment)))]
        self.assertLess(abs(frequency-180),9)
        self.assertGreater(r['processed_voiced_seconds'],.08)
    def test_silence_not_processed(self):
        x=np.zeros(32000,dtype=np.float32);y,r=crisp_release(x,32000)
        self.assertFalse(r['applied']);np.testing.assert_array_equal(x,y)
    def test_final_unvoiced_sound_retained(self):
        sr=32000;rng=np.random.default_rng(42)
        x=(.3*np.sin(2*np.pi*180*np.arange(sr)/sr)).astype(np.float32)
        x[-4800:]=rng.normal(0,.03,4800)
        y,r=crisp_release(x,sr)
        self.assertTrue(r['applied'])
        # Last ~150ms remain present after the compressed voiced part.
        post=len(y)-(r['prefix_samples_unchanged']+round(r['processed_voiced_seconds']*sr))
        self.assertGreater(post,.10*sr)
    def test_same_episode_uses_fresh_voice_not_stale_backup(self):
        cache=Path(__file__).parent/'.cache';cache.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=cache) as folder:
            root=Path(folder);d=root/'episodes/fixture';d.mkdir(parents=True)
            rate=32000;audio=(.3*np.sin(2*np.pi*180*np.arange(rate*2)/rate)).astype(np.float32)
            write_wav(d/'narration.wav',audio,rate)
            write_wav(d/'narration_strong.wav',np.zeros(rate,dtype=np.float32),rate)
            ep={'id':'fixture','scenes':[{'id':'news','narration':'测试收尾。'}]}
            meta={'job':{'pause':.22},'sample_rate':rate,'sentences':[{'sentence':'测试收尾。','raw_samples':len(audio),'processed_samples':len(audio),'mode':'strong'}]}
            for name,data in [('episode.json',ep),('narration.json',meta)]:
                (d/name).write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
            (d/'script.txt').write_text('测试收尾。',encoding='utf-8')
            with patch('crisp_tails.ROOT',root):process('fixture','fixture')
            saved,_=read_wav(d/'narration_source.wav')
            self.assertEqual(len(saved),len(audio))
            self.assertGreater(float(np.max(np.abs(saved))),.25)
            timings=json.loads((d/'timings.json').read_text(encoding='utf-8'))
            self.assertEqual(timings['sentences'][0]['scene_id'],'news')
if __name__=='__main__':unittest.main()
