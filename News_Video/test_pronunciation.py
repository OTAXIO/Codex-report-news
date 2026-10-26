import unittest
from pronunciation import spoken_text

class PronunciationChecks(unittest.TestCase):
    def test_brand_spoken_form_without_changing_names_containing_it(self):
        self.assertEqual(spoken_text('OpenAI 与 AI、DeepSeek。',{'OpenAI':'Open AI'}),'Open AI 与 AI、DeepSeek。')
        self.assertEqual(spoken_text('SomeOpenAIProduct。',{'OpenAI':'Open AI'}),'SomeOpenAIProduct。')
        self.assertEqual(spoken_text('Open A I 与 A I。',{}),'Open AI 与 AI。')

if __name__=='__main__':unittest.main()
