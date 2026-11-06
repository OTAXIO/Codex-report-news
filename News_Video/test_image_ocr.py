"""OCR fallback for image-only official posts: text cleanup and id handling (no OCR engine needed)."""
import unittest
from image_ocr import clean,is_prose,item_key


class ImageOcrChecks(unittest.TestCase):
    def test_cjk_spacing_is_removed_but_latin_words_keep_spaces(self):
        self.assertEqual(clean('卫 戍 协 议 将 以 周 期 形 式 常 驻 。'),'卫戍协议将以周期形式常驻。')
        self.assertEqual(clean('在 PC 端 进行'),'在 PC 端进行')

    def test_prose_filter_drops_screenshot_fragments(self):
        self.assertTrue(is_prose('每周期中包含两个序列，每序列中包含开放期、修订期、终止期三阶段。'))
        for noise in ['P E 「 n ^ M E H T','剩余可放置角色：6','LEVEL','B 吉47E8']:self.assertFalse(is_prose(noise),noise)

    def test_skland_article_id_maps_to_candidate_item_id(self):
        self.assertEqual(item_key('6458403'),'201b186c44806b7073b8')
        self.assertEqual(item_key('201b186c44806b7073b8'),'201b186c44806b7073b8')


if __name__=='__main__':unittest.main()
