import unittest
from copy import deepcopy
from temporary_editions import validate_temporary

class TemporaryChecks(unittest.TestCase):
    def episode(self):
        return dict(edition_type='temporary',counts_toward_daily_main_limit=False,temporary_kind='user_requested',publication_authorized_by_user=True,authorization_evidence='User explicitly requested this event and upload',temporary_event_id='a'*20,edition_timestamp='2026-10-27T02:34:00+08:00',footer_tag='临时新闻',event_key='one-event',scenes=[dict(section='临时新闻',event_key='one-event',item_id='123')])
    def test_explicit_commission_and_two_pages(self):
        ep=self.episode();ep['scenes']*=2;validate_temporary(ep)
    def test_rejects_unauthorized_or_unrelated(self):
        for patch in [dict(publication_authorized_by_user=False),dict(temporary_event_id='bad'),dict(counts_toward_daily_main_limit=True),dict(scenes=[dict(section='临时新闻',event_key='other',item_id='123')])]:
            with self.assertRaises(ValueError):validate_temporary(dict(self.episode(),**patch))
    def test_reset_guard_is_not_relaxed(self):
        ep=self.episode();ep['alert_id']='a'*20
        with self.assertRaises(ValueError):validate_temporary(ep)
