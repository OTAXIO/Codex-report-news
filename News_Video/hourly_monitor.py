"""Hourly source cache + reset queue. No model, TTS, render or upload API calls."""
import argparse,datetime as dt,hashlib,json
import news_video as n
import leader_sources,reset_alerts

def run(leaders_only=False,handle=None):
    report=dict(started=dt.datetime.now(n.UTC).isoformat(),model_calls=0)
    # Arm before first collection so old cached posts never become new alerts.
    report['reset_baseline']=reset_alerts.scan()
    # Social RSS and company X are refreshed only during video production.
    report['leaders']=leader_sources.collect(only=handle,scope='hourly')
    report['resets']=reset_alerts.scan()
    report['finished']=dt.datetime.now(n.UTC).isoformat()
    n.dump(n.ROOT/'data/hourly-monitor-last.json',report)
    return report

def compact_report(report):
    """Expose action/stop signals; keep collection detail in the existing log."""
    leaders=report.get('leaders',{})
    sources=leaders.get('sources',[])
    errors=[{k:s[k] for k in ('handle','error_code','error_stage') if k in s}
            for s in sources if not s.get('ok')]
    reason=leaders.get('reason')
    signature=hashlib.sha256(json.dumps(dict(reason=reason,errors=errors),sort_keys=True).encode()).hexdigest()[:16] if reason or errors else None
    return dict(source_ok=bool(sources) and not errors and not leaders.get('stopped'),
                stopped=bool(leaders.get('stopped')),reason=reason,
                requires_user_resolution=bool(leaders.get('requires_user_resolution')),
                retry_after_utc=leaders.get('retry_after_utc'),error_fingerprint=signature,
                full_report='data/hourly-monitor-last.json',
                new_items=leaders.get('new_items',0),
                new_alerts=report.get('resets',{}).get('new_alerts',[]),
                pending=report.get('resets',{}).get('pending',[]),source_errors=errors)


def compact_with_change(report,root=None):
    """Persist only the action signature so unchanged hourly failures stay quiet."""
    root=root or n.ROOT
    brief=compact_report(report)
    signal={k:brief[k] for k in ('source_ok','stopped','reason','requires_user_resolution','error_fingerprint','pending','source_errors')}
    # New alerts enter pending; do not notify again when new_alerts clears on
    # the following hour while the same review item remains queued.
    signature=hashlib.sha256(json.dumps(signal,sort_keys=True,ensure_ascii=False).encode()).hexdigest()[:20]
    path=root/'data/hourly-monitor-signal.json'
    previous=n.load(path) if path.is_file() else {}
    brief['changed']=previous.get('signature')!=signature
    actionable_stop=brief['stopped'] and brief['reason'] not in {'BUSY','COOLDOWN'}
    actionable_error=any(e.get('error_code') not in {'BUSY','COOLDOWN'} for e in brief['source_errors'])
    brief['notification_worthy']=brief['changed'] and bool(actionable_stop or actionable_error or brief['pending'] or brief['new_alerts'])
    path.parent.mkdir(parents=True,exist_ok=True)
    n.dump(path,dict(signature=signature,updated_at=report.get('finished')))
    return brief

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--leaders-only',action='store_true');p.add_argument('--handle')
    p.add_argument('--compact',action='store_true',help='Print only source health, new IDs and pending work; retain the full local report')
    a=p.parse_args();report=run(a.leaders_only,a.handle)
    print(json.dumps(compact_with_change(report) if a.compact else report,ensure_ascii=False,indent=None if a.compact else 2))
