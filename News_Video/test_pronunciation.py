import unittest
from pronunciation import spoken_text

class PronunciationChecks(unittest.TestCase):
    def test_clock_time_reads_cardinal_number_without_changing_display_source(self):
        display='北京时间10月26日13点48分。'
        self.assertEqual(spoken_text(display,{}),'北京时间10月26日十三点四十八分。')
        self.assertEqual(display,'北京时间10月26日13点48分。')
        self.assertEqual(spoken_text('06:05，12点30分，18点00分。',{}),'六点零五分，十二点三十分，十八点整。')
        self.assertEqual(spoken_text('版本1.48，25:90。',{}),'版本1.48，25:90。')
    def test_latest_tibo_chinese_pronunciation_guide(self):
        self.assertEqual(spoken_text('tibo 表示。',{'tibo':'梯啵'}),'梯啵 表示。')

    def test_tibo_uses_two_requested_syllables_only_in_speech(self):
        self.assertEqual(spoken_text('tibo 表示，tibo。',{'tibo':'ti bo'}),'ti bo 表示，ti bo。')
        self.assertEqual(spoken_text('table 与 antibo。',{'tibo':'ti bo'}),'table 与 antibo。')

    def test_brand_spoken_form_without_changing_names_containing_it(self):
        self.assertEqual(spoken_text('OpenAI 与 AI、DeepSeek。',{'OpenAI':'Open AI'}),'Open AI 与 AI、DeepSeek。')
        self.assertEqual(spoken_text('SomeOpenAIProduct。',{'OpenAI':'Open AI'}),'SomeOpenAIProduct。')
        self.assertEqual(spoken_text('Open A I 与 A I。',{}),'Open AI 与 AI。')

if __name__=='__main__':unittest.main()
