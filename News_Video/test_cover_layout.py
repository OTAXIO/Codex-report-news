import unittest
from PIL import Image,ImageDraw
import cover_generator as c

EP=dict(edition_slot='night',edition_series='endfield',edition_date='2026-11-12')
BRIEF=dict(headline_top='危机合约',headline_main='浸蓝测试作战',highlight='更新第二阶段',
           image='assets/logos/endfield-identity.png',image_label='终末地官方',footnote='终末地情报')

class PersonaCoverLayoutChecks(unittest.TestCase):
    def test_both_ratios_render_with_date_bottom_right(self):
        for height in (1080,1440):
            image=c.persona_canvas(EP,BRIEF,height)
            self.assertEqual(image.size,(1920,height))
            # The date is drawn once, on the white band in the bottom-right corner.
            corner=image.crop((1500,height-150,1820,height-20)).convert('L')
            self.assertLess(corner.getextrema()[0],60)

    def test_text_is_upright_on_a_slanted_plate(self):
        f=c.font(80);plain=Image.new('RGBA',(400,120),(0,0,0,0))
        ImageDraw.Draw(plain).text((0,0),'测试',font=f,fill='white')
        layer=c.tag('测试',f,'white',None)
        # No background: the glyphs are drawn exactly as plain text, i.e. not sheared.
        self.assertEqual(layer.getchannel('A').getbbox()[2]-layer.getchannel('A').getbbox()[0],
                         plain.getchannel('A').getbbox()[2]-plain.getchannel('A').getbbox()[0])
        plated=c.tag('测试',f,'white','black',padx=20,pady=10)
        alpha=plated.getchannel('A')
        # The plate leans: its top row starts further right than its bottom row.
        first=lambda y:next(x for x in range(plated.width) if alpha.getpixel((x,y)))
        self.assertGreater(first(0),first(plated.height-1))

    def test_minimum_sizes_refuse_instead_of_shrinking(self):
        with self.assertRaisesRegex(ValueError,'does not fit at 138px'):
            c.persona_canvas(EP,dict(BRIEF,headline_top='这是一条非常非常非常长的第一行标题'),1080)
        with self.assertRaisesRegex(ValueError,'does not fit at 166px'):
            c.persona_canvas(EP,dict(BRIEF,highlight='这是一条超过画面宽度的第三行重点'),1080)

if __name__=='__main__':unittest.main()
