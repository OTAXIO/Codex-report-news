"""AI regional coverage targets: audit real fresh events, never manufacture filler."""
from __future__ import annotations
import datetime as dt

REGIONS=('domestic','international')
UTC=dt.timezone.utc

def region_of(row,sources,editorial):
    source=sources.get(row.get('source_id'),{})
    return source.get('region') or editorial.get('vendor_regions',{}).get(source.get('vendor') or row.get('company') or row.get('publisher'),'unknown')

def fresh(row,now,hours):
    try:
        stamp=dt.datetime.fromisoformat((row.get('published') or '').replace('Z','+00:00'))
        return stamp.tzinfo is not None and dt.timedelta(0)<=now-stamp<=dt.timedelta(hours=hours)
    except (ValueError,TypeError):return False

def event_identity(row):
    return row.get('event_key') or row.get('url') or row['id']

def coverage(items,sources,editorial,now=None):
    """Candidate counts are availability, not AI-verified newsworthiness."""
    now=now or dt.datetime.now(UTC);policy=editorial.get('ai_coverage',{})
    hours=policy.get('fresh_hours',24);targets=policy.get('targets',{'domestic':3,'international':3})
    buckets={r:[] for r in (*REGIONS,'unknown')};seen=set()
    for row in items:
        if row.get('kind')!='ai' or not fresh(row,now,hours):continue
        key=event_identity(row)
        if key in seen:continue
        seen.add(key);region=region_of(row,sources,editorial)
        buckets[region if region in buckets else 'unknown'].append(row['id'])
    return dict(target_total=policy.get('target_total',6),targets=targets,fresh_hours=hours,
                available={r:len(buckets[r]) for r in REGIONS},candidate_ids=buckets,
                raw_candidate_counts_require_editorial_review=True,
                shortfall={r:max(0,targets.get(r,3)-len(buckets[r])) for r in REGIONS},
                maximum_items=policy.get('maximum_items'),advisory_only=True,enforce_minimum=False,
                policy='Suggested 3 domestic + 3 international fresh distinct events, never a minimum; no stale, repeated, fabricated or low-value filler; recaps separate; additional qualified AI news allowed.')

def audit_selection(episode,selected,available,sources,editorial,now=None):
    if episode.get('edition_slot') not in {'morning','noon','night'}:return None
    if not editorial.get('ai_coverage'):return None
    now=now or dt.datetime.now(UTC)
    result=coverage(available,sources,editorial,now);chosen=coverage(selected,sources,editorial,now)
    result['selected']=chosen['available'];result['selected_ids']=chosen['candidate_ids']
    result['shortfall']={r:max(0,result['targets'].get(r,3)-result['selected'][r]) for r in REGIONS}
    result['reasons']={};reasons=episode.get('ai_shortfall_reasons',{})
    for region in REGIONS:
        if not result['shortfall'][region]:continue
        count=result['available'][region];target=result['targets'].get(region,3)
        if isinstance(reasons.get(region),str) and reasons[region].strip():result['reasons'][region]=reasons[region].strip()
        elif count==0:result['reasons'][region]='No fresh unused candidates in the configured 24-hour window.'
        elif count<target:result['reasons'][region]='Fewer fresh unused candidates than the regional target; no filler added.'
        else:result['reasons'][region]='Advisory count only; raw candidates are not verified news. No minimum or filler is required.'
    result['status']='target_met' if not any(result['shortfall'].values()) else 'partial_with_reason'
    result['recaps_count_separately']=True
    return result
