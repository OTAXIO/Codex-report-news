import json,tempfile,unittest
from pathlib import Path
from verify_speech_content import compare_sentence,validate_review
from caption_layout import sentence_captions
class SpeechContentChecks(unittest.TestCase):
    def test_original_48_second_noise_failure_is_blocked(self):
        self.assertIn('abnormally_long_sentence',compare_sentence('亚指数时间不等于多项式时间，这项结果也不等于证明所有难题都能高效解决。','亚指数时间不等于多项式时间',48)['problems'])
        self.assertIn('missing_or_changed_speech',compare_sentence('这是必须实际读出的完整句子。','',4)['problems'])
    def test_normal_short_sentence_passes(self):
        self.assertEqual(compare_sentence('相关论文和验证材料已经公开。','相关论文和验证材料已经公开',3)['problems'],[])
    def test_actual_caption_times_are_used_and_corruption_is_rejected(self):
        s=dict(text='这是第一句，随后第二句。',start=0,end=5,aligned_cues=[dict(text='这是第一句，',start=.2,end=1),dict(text='随后第二句。',start=1,end=4.8)])
        self.assertEqual(sentence_captions(s)[0]['end'],1)
        s['aligned_cues'][1]['start']=.8
        with self.assertRaises(ValueError):sentence_captions(s)
        s['aligned_cues'][1]['start']=1;s['aligned_cues'][1]['text']='伪造字幕。'
        with self.assertRaises(ValueError):sentence_captions(s)
    def test_review_is_bound_to_audio_script_and_caption_timing(self):
        from verify_speech_content import digest
        with tempfile.TemporaryDirectory(dir='.cache') as folder:
            target=Path(folder);(target/'narration.wav').write_bytes(b'unit-test PCM hash fixture');(target/'spoken_script.txt').write_text('original',encoding='utf-8')
            cue=dict(text='原文',start=0,end=1)
            def save(name,value):(target/name).write_text(json.dumps(value),encoding='utf-8')
            save('timings.json',dict(sentences=[dict(aligned_cues=[cue])]))
            save('audio-content-review.json',dict(ok=True,narration_sha256=digest(target/'narration.wav'),script_sha256=digest(target/'spoken_script.txt'),sentences=[{}]))
            save('caption-alignment.json',dict(narration_sha256=digest(target/'narration.wav'),sentences=[dict(cues=[cue])]))
            self.assertTrue(validate_review(target)['ok'])
            save('timings.json',dict(sentences=[dict(aligned_cues=[dict(cue,end=.8)])]))
            with self.assertRaises(ValueError):validate_review(target)
            (target/'spoken_script.txt').write_text('Changed after verification',encoding='utf-8')
            with self.assertRaises(ValueError):validate_review(target)
if __name__=='__main__':unittest.main()
