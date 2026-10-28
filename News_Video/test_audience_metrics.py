import tempfile,unittest
from pathlib import Path
from audience_metrics import read_csv

HEADER='episode_id,edition_type,window_hours,impressions,clicks,reported_ctr_percent,retention_3s_percent,retention_30s_percent,average_watch_seconds,duration_seconds,ai_start_seconds,games_start_seconds,traffic_source\n'

class AudienceMetricsChecks(unittest.TestCase):
    def test_missing_denominator_stays_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            file=Path(tmp)/'metrics.csv'
            file.write_text(HEADER+'one,main,24,,,75,68,,45,120,3,74,recommendation\n',encoding='utf-8')
            row=read_csv(file)['rows'][0]
            self.assertIsNone(row['ctr_calculated_percent'])
            self.assertEqual(row['reported_ctr_percent'],75)
            self.assertEqual(row['ctr_basis'],'reported_only')

    def test_reject_inconsistent_clicks(self):
        with tempfile.TemporaryDirectory() as tmp:
            file=Path(tmp)/'metrics.csv'
            file.write_text(HEADER+'one,main,72,10,11,,,,,,,,\n',encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'exceed'):read_csv(file)

if __name__=='__main__':unittest.main()
