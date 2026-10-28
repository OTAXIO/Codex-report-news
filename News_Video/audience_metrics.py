"""Read-only, non-causal import of Bilibili video analytics CSV."""
import argparse,csv,json
from pathlib import Path

FIELDS={'episode_id','edition_type','window_hours','impressions','clicks',
        'reported_ctr_percent','retention_3s_percent','retention_30s_percent',
        'average_watch_seconds','duration_seconds','ai_start_seconds',
        'games_start_seconds','traffic_source'}

def optional_number(value,field):
    if value is None or not str(value).strip():return None
    try:number=float(value)
    except ValueError:raise ValueError('Invalid number in '+field)
    if number<0 or (field.endswith('_percent') and number>100):raise ValueError('Out-of-range '+field)
    if field in {'impressions','clicks'} and not number.is_integer():raise ValueError('Expected whole count in '+field)
    return number

def read_csv(path):
    rows=[]
    with Path(path).open(encoding='utf-8-sig',newline='') as stream:
        reader=csv.DictReader(stream)
        if not reader.fieldnames or not FIELDS.issubset(reader.fieldnames):
            raise ValueError('Analytics CSV missing required columns: '+', '.join(sorted(FIELDS-set(reader.fieldnames or []))))
        for raw in reader:
            if not raw.get('episode_id','').strip():continue
            slot=raw.get('edition_type','').strip()
            if slot not in {'main','reset','model_temporary'}:raise ValueError('Invalid edition_type')
            hours=optional_number(raw.get('window_hours'),'window_hours')
            if hours not in {24.0,72.0}:raise ValueError('Only same-age 24/72h windows are comparable')
            numbers={key:optional_number(raw.get(key),key) for key in sorted(FIELDS-{'episode_id','edition_type','window_hours','traffic_source'})}
            if numbers['clicks'] is not None and numbers['impressions'] is not None and numbers['clicks']>numbers['impressions']:
                raise ValueError('Clicks exceed impressions')
            calculated=100*numbers['clicks']/numbers['impressions'] if numbers['clicks'] is not None and numbers['impressions'] else None
            rows.append(dict(episode_id=raw['episode_id'].strip(),edition_type=slot,window_hours=int(hours),
                             traffic_source=raw.get('traffic_source','').strip() or None,
                             ctr_calculated_percent=round(calculated,4) if calculated is not None else None,
                             ctr_basis='clicks/impressions' if calculated is not None else 'reported_only' if numbers['reported_ctr_percent'] is not None else None,
                             **numbers))
    return dict(rows=rows,count=len(rows),comparison_policy='Group by edition_type, window_hours and traffic_source; low samples are observational, not causal A/B.',
                missing_value_policy='null; never infer exposure or CTR denominator from reported percentage')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('csv');a=p.parse_args()
    print(json.dumps(read_csv(a.csv),ensure_ascii=False,indent=2))
