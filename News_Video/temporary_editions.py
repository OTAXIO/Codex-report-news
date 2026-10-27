"""Explicitly commissioned temporary stories; reset alerts keep their strict validator."""
import re
from datetime import datetime

def validate_temporary(ep):
    if ep.get('alert_id'):
        from reset_alerts import validate_temporary as validate_reset
        return validate_reset(ep)
    if ep.get('edition_type')!='temporary' or ep.get('counts_toward_daily_main_limit') is not False:
        raise ValueError('Temporary edition must not count as a daily main edition')
    if ep.get('temporary_kind') not in {'user_requested','official_model_release'} or ep.get('publication_authorized_by_user') is not True:
        raise ValueError('Non-reset temporary story requires explicit user authorization')
    if not ep.get('authorization_evidence') or not re.fullmatch(r'[a-f0-9]{12,64}',ep.get('temporary_event_id','')):
        raise ValueError('Missing authorization evidence or stable event ID')
    timestamp=datetime.fromisoformat(ep['edition_timestamp'])
    if timestamp.tzinfo is None:raise ValueError('Temporary timestamp requires timezone')
    from layout_policy import is_overview,folio_numbers
    all_scenes=ep.get('scenes',[]);folio_numbers(all_scenes)
    scenes=[s for s in all_scenes if not is_overview(s)]
    if not 1<=len(scenes)<=2 or ep.get('footer_tag')!='临时新闻':
        raise ValueError('A commissioned temporary story uses 1-2 news pages plus an optional first overview')
    event=ep.get('event_key')
    if not event or any(s.get('event_key')!=event or s.get('section')!='临时新闻' or not s.get('item_id') for s in scenes):
        raise ValueError('Temporary pages must concern the same sourced event')
