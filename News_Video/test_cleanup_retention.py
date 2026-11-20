import datetime as dt,json,os,tempfile,time,unittest
from pathlib import Path
from unittest.mock import patch
import cleanup_retention as c

NOW=dt.datetime(2026,11,19,20,0,tzinfo=c.BEIJING).timestamp()

class RetentionChecks(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)/'News_Video';self.rel=Path(self.tmp.name)/'release'
        self.root.mkdir();self.rel.mkdir()
    def tearDown(self):self.tmp.cleanup()
    def make(self,path,receipt=None,age_hours=48):
        path.mkdir(parents=True);(path/'x.bin').write_bytes(b'x')
        if receipt is not None:(path/'release.json').write_text(json.dumps(receipt),encoding='utf-8')
        old=NOW-age_hours*3600
        for p in [path/'x.bin',path/'release.json',path]:
            if p.exists():os.utime(p,(old,old))
        return path
    def run_plan(self):
        with patch.object(c,'release_root',return_value=self.rel):return c.plan(self.root,3,NOW)
    def test_keeps_window_and_unpublished_deletes_old_published(self):
        old=self.make(self.rel/'2026_11_16_morning',dict(published=True))
        pending=self.make(self.rel/'2026_11_15_night_arknights',dict(published=False,state='reviewing'))
        recent=self.make(self.rel/'2026_11_17_morning',dict(published=True))
        ep_old=self.make(self.root/'episodes/daily-20261116-morning');ep_new=self.make(self.root/'episodes/daily-20261118-morning')
        cutoff,delete,kept=self.run_plan()
        self.assertEqual(cutoff,'20261117')
        self.assertIn(old,delete);self.assertIn(ep_old,delete)
        for path in (pending,recent,ep_new):self.assertNotIn(path,delete)
        self.assertEqual([d for d,_ in kept],[pending])
    def test_recently_modified_old_folder_is_left_alone(self):
        busy=self.make(self.root/'episodes/daily-20261110-morning',age_hours=1)
        _,delete,_=self.run_plan()
        self.assertNotIn(busy,delete)

    def test_git_tracked_fixture_folders_are_never_deleted(self):
        fixture=self.make(self.root/'episodes/sample-20261026')
        with patch.object(c,'tracked_tops',return_value={fixture.resolve()}):
            _,delete,_=self.run_plan()
        self.assertNotIn(fixture,delete)
    def test_tracked_tops_finds_the_real_sample_fixtures(self):
        names={p.name for p in c.tracked_tops(c.ROOT)}
        self.assertIn('sample-20261026',names)

if __name__=='__main__':unittest.main()
