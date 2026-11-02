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

# --- Game effective-time basis (user decision 2026-11-02) -------------------
# An official game announcement older than 48h may still lead a scene when the
# thing it announces (launch, event/banner start, maintenance) takes effect in
# the edition window. The time must be quoted from the archived official text.
EFFECTIVE_SOURCES={'official_game_page','skland_capture','skland_browser','official_x'}

def date_tokens(moment):
    m,d=moment.month,moment.day
    names=['January','February','March','April','May','June','July','August','September','October','November','December']
    return {f'{m}月{d}日',f'{m:02d}月{d:02d}日',f'{m}月{d:02d}日',f'{m}/{d}',f'{m:02d}/{d:02d}',f'{moment.year}/{m}/{d}',
            f'{moment.year}-{m:02d}-{d:02d}',f'{moment.year}年{m}月{d}日',f'{m}.{d}',f'{m:02d}.{d:02d}',
            f'{names[m-1]} {d}',f'{names[m-1][:3]} {d}',f'{names[m-1][:3]}. {d}',f'{d} {names[m-1]}'}

def official_text(root,item_id):
    """Archived official wording for an item (inspected article, game record or X post)."""
    root=Path(root);parts=[]
    for folder,keys in [('articles',('text','summary')),('game-items',('summary','title','official_body')),('leader-posts',('original_text','summary'))]:
        path=root/'data'/folder/(str(item_id)+'.json')
        if path.is_file():
            value=json.loads(path.read_text(encoding='utf-8'))
            for k in keys:
                v=value.get(k)
                parts.extend(v if isinstance(v,list) else [v] if v else [])
    return '\n'.join(map(str,parts))

def effective_check(root,item_id,effective_at,quote,reference,before_hours,after_hours,max_age_days,evidence,source_type,cfg_types=None):
    """Window check for an announced effective time; returns dict(ok, reason)."""
    try:
        if source_type not in (cfg_types or EFFECTIVE_SOURCES):return dict(ok=False,reason='effective_basis_not_official_game_source')
        when=dt.datetime.fromisoformat(str(effective_at))
        if when.tzinfo is None:return dict(ok=False,reason='effective_time_needs_timezone')
        text=official_text(root,item_id)
        if not quote or quote not in text:return dict(ok=False,reason='effective_quote_not_in_official_text')
        if not any(t in quote for t in date_tokens(when)):return dict(ok=False,reason='effective_quote_lacks_effective_date')
        published=stamp(evidence['original_published_at'])
        if published<reference-dt.timedelta(days=max_age_days):return dict(ok=False,reason='announcement_too_old_for_effective_basis')
        if published>reference:return dict(ok=False,reason='future_announcement')
        utc=when.astimezone(UTC)
        if not reference-dt.timedelta(hours=before_hours)<=utc<=reference+dt.timedelta(hours=after_hours):
            return dict(ok=False,reason='effective_time_outside_window')
        return dict(ok=True,reason='effective_time_within_window',effective_at=utc.isoformat())
    except (ValueError,TypeError,KeyError) as error:return dict(ok=False,reason='invalid_effective_evidence',detail=str(error))

def effective_policy(root):
    path=Path(root)/'config.json'
    cfg=json.loads(path.read_text(encoding='utf-8')) if path.is_file() else {}
    return cfg.get('freshness',{}).get('effective_window',{})

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
    schedules=[s for s in episode['scenes'] if s.get('freshness_basis')=='schedule']
    if len(schedules)>effective_policy(root).get('max_schedule_scenes',1):raise ValueError('FRESHNESS: at most one schedule page per edition')
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
        basis=scene.get('freshness_basis')
        if basis in {'effective_time','schedule'}:
            policy=effective_policy(root)
            if not policy.get('enabled') or scene.get('editorial_role')=='recap' or episode.get('edition_slot')=='temporary' or not scene.get('game'):
                raise ValueError('FRESHNESS: '+str(scene.get('item_id'))+': effective/schedule basis is only for main-edition game scenes')
        if basis=='effective_time' and not result['ok']:
            # The original publication time is still recorded; the window applies to the announced effective time.
            effective=effective_check(root,scene.get('item_id'),scene.get('effective_at'),scene.get('effective_quote'),reference,
                                      policy.get('before_hours',24),policy.get('after_hours',24),policy.get('max_announcement_age_days',14),
                                      evidence,scene.get('source_type'),set(policy.get('source_types',EFFECTIVE_SOURCES)))
            result.update(effective,basis='effective_time',publication_check=result['reason'])
        if basis=='schedule':
            # One page listing official start/end times within the next 72h; each entry quotes its own announcement.
            entries=scene.get('schedule_items') or []
            checks=[]
            for entry in entries:
                ev=evidence_for(root,dict(item_id=entry.get('item_id')))
                c=effective_check(root,entry.get('item_id'),entry.get('effective_at'),entry.get('effective_quote'),reference,
                                  0,policy.get('schedule_hours',72),policy.get('schedule_max_announcement_age_days',30),ev,entry.get('source_type'),
                                  set(policy.get('source_types',EFFECTIVE_SOURCES)))
                checks.append(dict(item_id=entry.get('item_id'),**c))
            ok=bool(entries) and all(c['ok'] for c in checks)
            result.update(ok=ok,reason='schedule_entries_within_window' if ok else 'schedule_entry_invalid',basis='schedule',schedule_checks=checks)
        results.append(result)
        if not result['ok']:raise ValueError('FRESHNESS: '+str(scene.get('item_id'))+': '+result['reason'])
        if bind:
            if result.get('basis'):scene['freshness_basis_audit']={k:v for k,v in result.items() if k not in {'evidence'}}
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
