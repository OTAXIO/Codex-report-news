import copy,tempfile,unittest,wave
from pathlib import Path
from scene_pauses import apply_scene_holds

class SceneHoldChecks(unittest.TestCase):
    def test_short_context_groups_keep_original_sentence_and_scene_pauses(self):
        rate=1000;speech=b'\x01\0'*100
        ep=dict(normalize_context_pauses=True,voice_scene_pause_seconds=.6,scenes=[dict(id='one',narration='甲。乙。'),dict(id='two',narration='丙。')])
        meta=dict(sentences=[dict(processed_samples=100,pause_after_samples=600),dict(processed_samples=100,pause_after_samples=600),dict(processed_samples=100)])
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'voice.wav'
            with wave.open(str(p),'wb') as w:w.setparams((1,2,rate,0,'NONE','not compressed'));w.writeframes(speech+b'\0'*1200+speech+b'\0'*1200+speech)
            result=apply_scene_holds(p,meta,ep,.4)
            self.assertEqual([s.get('pause_after_samples') for s in result['sentences'][:2]],[400,600])
            with wave.open(str(p),'rb') as w:self.assertEqual(w.readframes(w.getnframes()),speech+b'\0'*800+speech+b'\0'*1200+speech)

    def test_hold_is_exact_preserves_speech_and_is_idempotent(self):
        rate=1000;intro=b'\x01\0'*500;body=b'\x02\0'*700
        meta={'seconds':1.4,'sentences':[{'sentence':'导览。','processed_samples':500},{'sentence':'正文。','processed_samples':700}]}
        episode={'scenes':[{'id':'intro','narration':'导览。','hold_after_seconds':2.0},{'id':'body','narration':'正文。'}]}
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as folder:
            p=Path(folder)/'voice.wav'
            with wave.open(str(p),'wb') as w:w.setparams((1,2,rate,0,'NONE','not compressed'));w.writeframes(intro+b'\0'*400+body)
            result=apply_scene_holds(p,copy.deepcopy(meta),episode,.2)
            with wave.open(str(p),'rb') as w:data=w.readframes(w.getnframes())
            self.assertEqual(data,intro+b'\0'*4000+body)
            self.assertEqual(result['seconds'],3.2)
            before=p.read_bytes();apply_scene_holds(p,result,episode,.2);self.assertEqual(p.read_bytes(),before)

if __name__=='__main__':unittest.main()
