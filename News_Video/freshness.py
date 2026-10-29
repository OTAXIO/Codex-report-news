"""Original-publication time gates, shared by selection, export and upload."""
import datetime as dt
import json,re,email.utils
from pathlib import Path

UTC=dt.timezone.utc

def stamp(value):
    result=dt.datetime.fromisoformat(str(value).replace('Z','+00:00'))
    if result.tzinfo is None:raise ValueError('Publication time needs an explicit timezone')
    return result.astimezone(UTC)

def time_evidence(item,source=None):
    source=source or {}
    raw=item.get('raw_published',item.get('published'))
    precision=item.get('published_precision',source.get('published_precision','date' if re.fullmatch(r'\d{4}-\d{2}-\d{2}',str(raw)) else 'second'))
    zone=item.get('source_timezone',source.get('timezone'))
    if not zone and precision!='date' and raw:
        try:original=dt.datetime.fromisoformat(str(raw).replace('Z','+00:00'))
        except ValueError:
            try:original=email.utils.parsedate_to_datetime(str(raw))
            except (ValueError,TypeError):original=None
        if original and original.tzinfo is not None:
            offset=int(original.utcoffset().total_seconds()/60);sign='+' if offset>=0 else '-';zone=f'{sign}{abs(offset)//60:02d}:{abs(offset)%60:02d}'
    return dict(original_published_at=item.get('original_published_at',item.get('published')),
                raw_time=raw,precision=precision,source_timezone=zone,
                source_url=item.get('url',item.get('source_url')),
                time_basis=item.get('time_basis','original_publication'))

def check(evidence,reference,hours=48):
    """Date-only evidence is a conservative full local-day interval."""
    try:
        if evidence.get('time_basis')!='original_publication':raise ValueError('Not an original publication timestamp')
        precision=evidence.get('precision','second')
        if precision=='date':
            zone=evidence.get('source_timezone')
            if not zone:raise ValueError('Date-only source timezone is unknown')
            if re.fullmatch(r'[+-]\d{2}:\d{2}',zone):tz=dt.datetime.fromisoformat('2000-01-01T00:00:00'+zone).tzinfo
            else:
                from zoneinfo import ZoneInfo
                tz=ZoneInfo(zone)
            day=dt.date.fromisoformat(str(evidence['original_published_at'])[:10])
            low=dt.datetime.combine(day,dt.time.min,tzinfo=tz).astimezone(UTC)
            high=dt.datetime.combine(day+dt.timedelta(days=1),dt.time.min,tzinfo=tz).astimezone(UTC)-dt.timedelta(microseconds=1)
        else:
            low=stamp(evidence.get('original_published_at'));high=low
            if precision not in {'second','minute'}:raise ValueError('Unknown publication precision')
        if precision=='minute':high=low+dt.timedelta(minutes=1)-dt.timedelta(microseconds=1)
        cutoff=reference-dt.timedelta(hours=min(48,hours))
        if low<cutoff:return dict(ok=False,reason='expired_or_boundary_uncertain')
        if high>reference:return dict(ok=False,reason='future_or_boundary_uncertain')
        return dict(ok=True,reason='within_window')
    except (ValueError,TypeError,KeyError) as error:return dict(ok=False,reason='missing_or_invalid_original_time',detail=str(error))

def enabled(root):
    path=Path(root)/'config.json'
    return path.is_file() and json.loads(path.read_text(encoding='utf-8')).get('freshness',{}).get('enabled',False)

def evidence_for(root,scene):
    key=scene.get('item_id');root=Path(root)
    # Never trust an editor-supplied timestamp when the collected original exists.
    for folder in ['time-evidence','leader-posts','game-items']:
        path=root/'data'/folder/(str(key)+'.json')
        if key and path.is_file():
            value=json.loads(path.read_text(encoding='utf-8'))
            return value if folder=='time-evidence' else time_evidence(value)
    # Legacy collected records remain usable when their original feed/DB time
    # and registered precision are available. Never use the scene's own clock.
    dbpath=root/'data/news.sqlite3'
    if key and dbpath.exists():
        import sqlite3
        from contextlib import closing
        with closing(sqlite3.connect(dbpath)) as db:
            db.row_factory=sqlite3.Row
            row=db.execute('SELECT * FROM items WHERE id=?',(key,)).fetchone()
        if row:
            catalog=root/'sources.json'
            source=next((s for s in json.loads(catalog.read_text(encoding='utf-8')) if s['id']==row['source_id']),{}) if catalog.exists() else {}
            return time_evidence(dict(row),source)
    raise ValueError('FRESHNESS: archived original time missing for '+str(key))

def audit_episode(episode,root,reference=None,bind=False):
    if not enabled(root):return None
    reference=reference or dt.datetime.now(UTC);results=[]
    from layout_policy import is_overview
    cfg=json.loads((Path(root)/'config.json').read_text(encoding='utf-8'))
    for scene in episode['scenes']:
        if is_overview(scene):continue
        evidence=evidence_for(root,scene)
        hours=48
        if scene.get('editorial_role')=='recap':hours=24
        elif episode.get('edition_slot')=='temporary':
            policy='reset_alerts' if episode.get('alert_id') else 'model_alerts'
            hours=min(hours,cfg.get(policy,{}).get('max_age_hours',6))
        result=dict(item_id=scene.get('item_id'),hours=hours,evidence=evidence,**check(evidence,reference,hours))
        results.append(result)
        if not result['ok']:raise ValueError('FRESHNESS: '+str(scene.get('item_id'))+': '+result['reason'])
        if bind:
            scene['published']=evidence['original_published_at'];scene['published_precision']=evidence['precision']
            scene['publication_time_evidence']=evidence
            # The registered publisher/product supplies the overview subject;
            # an editor's clock or arbitrary company name cannot replace it.
            catalog=Path(root)/'sources.json'
            if catalog.is_file() and scene.get('source_type') not in {'leader_x','official_x'}:
                sources=json.loads(catalog.read_text(encoding='utf-8'))
                src=next((s for s in sources if s.get('url')==scene.get('source_url') or scene.get('source_url','').startswith(s.get('article_base','__no_match__').rstrip('/')+'/')),None)
                if src:
                    scene['company']=src.get('vendor',src.get('publisher'))
                    if src.get('product'):scene['product']=src['product']
    audit=dict(reference_time=reference.isoformat(),cutoff=(reference-dt.timedelta(hours=48)).isoformat(),items=results,ok=True)
    if bind:episode['freshness_audit']=audit
    return audit
