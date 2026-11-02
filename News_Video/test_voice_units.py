import json,tempfile,unittest,wave
from pathlib import Path
import voice_units as v

class VoiceUnitCacheChecks(unittest.TestCase):
    def write_run(self,root,units):
        run=Path(root)/'context-source';run.mkdir()
        job=dict(model_path='m',reference='r',reference_text='t',seed=42,consistent_unit_seed=True,speech_rate=1.0,max_new_tokens=1024,pause=0,text_file='x')
        frames=b'';entries=[]
        for i,u in enumerate(units):
            samples=100*(i+1);frames+=bytes([i+1])*2*samples
            entries.append(dict(sentence=u,raw_samples=samples,processed_samples=samples,mode='off'))
        with wave.open(str(run/'context.wav'),'wb') as w:
            w.setnchannels(1);w.setsampwidth(2);w.setframerate(24000);w.writeframes(frames)
        (run/'context.json').write_text(json.dumps(dict(job=job,sentences=entries,sample_rate=24000)),encoding='utf-8')
        return run,job

    def test_seeded_units_round_trip_exact_audio(self):
        with tempfile.TemporaryDirectory() as tmp:
            run,job=self.write_run(tmp,['第一段。','第二段。'])
            self.assertEqual(v.seed_cache(run,Path(tmp)/'cache'),2)
            _,frames=v.read_wav(Path(tmp)/'cache'/(v.unit_key('第二段。',job)+'.wav'))
            self.assertEqual(frames,bytes([2])*400)

    def test_key_changes_with_text_or_voice_settings_not_paths(self):
        job=dict(model_path='m',seed=42,temperature=.7,text_file='a',output_file='b')
        base=v.unit_key('同一段。',job)
        self.assertEqual(base,v.unit_key('同一段。',dict(job,text_file='other',output_file='other')))
        self.assertNotEqual(base,v.unit_key('改过一段。',job))
        self.assertNotEqual(base,v.unit_key('同一段。',dict(job,temperature=.8)))

if __name__=='__main__':unittest.main()
