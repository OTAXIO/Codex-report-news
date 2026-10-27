import json,math,shutil,tempfile,unittest,wave
from pathlib import Path
import numpy as np
from audio_mix import ensure_soundtrack,loop_music,read_pcm,speech_first_mix,write_pcm,digest,validate_release_mix

class MusicChecks(unittest.TestCase):
    def test_intro_plays_once_then_repeat_starts_at_three_seconds(self):
        # Five-second track with a distinct one-second label in each channel.
        source=np.repeat(np.repeat(np.arange(5),48000)[:,None],2,axis=1)
        looped=loop_music(source,12*48000,3)
        actual=looped[::48000,0].tolist()
        self.assertEqual(actual,[0,1,2,3,4,3,4,3,4,3,4,3])
        np.testing.assert_array_equal(loop_music(source,48000,3),source[:48000])
        with self.assertRaises(ValueError):loop_music(source,48000,5)
    def test_speech_dominates_soft_and_loud_phrases_without_changing_timing(self):
        sr=48000;t=np.arange(sr*3)/sr
        amplitude=np.where(t<1,.12,np.where(t<2,0,.012))
        voice=np.repeat((amplitude*np.sin(2*np.pi*220*t))[:,None],2,axis=1)
        music=np.repeat((.1*np.sin(2*np.pi*440*t))[:,None],2,axis=1)
        mixed,bed,r=speech_first_mix(voice.copy(),music,dict(reference_voice_gap_db=18,music_peak_dbfs=-24))
        self.assertEqual(mixed.shape,voice.shape)
        np.testing.assert_allclose(mixed-bed,voice,atol=1e-12)
        self.assertGreaterEqual(r['reference_measured_voice_gap_db'],17.99)
        self.assertLessEqual(r['music_peak_dbfs'],-23.99)
        self.assertGreater(r['constant_music_gain'],.08)
        self.assertTrue(np.any(bed[sr:sr*2]))
        self.assertFalse(r['ducking'])
        # A pause and a quiet sentence use the same gain as the loud sentence.
        ratios=[]
        for start in [int(.5*sr),int(1.5*sr),int(2.3*sr)]:
            ratios.append(float(np.sqrt(np.mean(bed[start:start+1000]**2)/np.mean(music[start:start+1000]**2))))
        np.testing.assert_allclose(ratios,[ratios[0]]*3,atol=1e-12)
    def test_music_only_news_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'No audible narration'):
            speech_first_mix(np.zeros((4800,2)),np.ones((4800,2))*.01,{})
    def test_real_ffmpeg_loop_cache_and_configured_failure(self):
        ff=Path('D:/others/TOOLS/GPT-SoVITS-v2pro-20250604/runtime/ffmpeg.exe')
        if not ff.exists():
            found=shutil.which('ffmpeg')
            if not found:self.skipTest('FFmpeg unavailable; real audio integration not verified')
            ff=Path(found)
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);episode=root/'episode';episode.mkdir()
            def tone(seconds,hz,level):
                t=np.arange(round(48000*seconds))/48000
                return np.repeat((level*np.sin(2*np.pi*hz*t))[:,None],2,axis=1)
            write_pcm(episode/'narration.wav',tone(1.1,220,.12))
            write_pcm(root/'music.wav',tone(.17,440,.2))
            policy=dict(enabled=True,file='music.wav',target_lufs=-32,reference_voice_gap_db=18,music_peak_dbfs=-24,repeat_from_seconds=.03)
            (root/'config.json').write_text(json.dumps(dict(background_music=policy)))
            result=ensure_soundtrack(root,episode,1.2,ff)
            self.assertEqual(len(read_pcm(result)),57600)
            self.assertGreater(np.max(np.abs(read_pcm(result)[48000:])),0)
            r=json.loads((episode/'audio-mix.json').read_text())
            self.assertTrue(r['loop_to_video_end']);self.assertGreaterEqual(r['reference_measured_voice_gap_db'],17.99)
            self.assertEqual(r['repeat_from_seconds'],.03);self.assertEqual(r['intro_play_count'],1)
            requirement=dict(sha256=digest(root/'music.wav'),repeat_from_seconds=.03,reference_voice_gap_db=18,voice_gap_measure='active_window_median',music_peak_dbfs=-24)
            validate_release_mix(episode,requirement,1.2)
            with self.assertRaisesRegex(ValueError,'requirements'):
                validate_release_mix(episode,dict(requirement,repeat_from_seconds=3),1.2)
            stamp=result.stat().st_mtime_ns
            self.assertEqual(ensure_soundtrack(root,episode,1.2,ff).stat().st_mtime_ns,stamp)
            (root/'music.wav').unlink()
            with self.assertRaises(FileNotFoundError):ensure_soundtrack(root,episode,1.2,ff)
            policy['enabled']=False
            (root/'config.json').write_text(json.dumps(dict(background_music=policy)))
            self.assertEqual(ensure_soundtrack(root,episode,1.2,ff),episode/'narration.wav')

if __name__=='__main__':unittest.main()
