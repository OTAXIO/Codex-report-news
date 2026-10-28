"""Hourly source cache + reset queue. No model, TTS, render or upload API calls."""
import argparse,datetime as dt,json
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
    sources=report.get('leaders',{}).get('sources',[])
    errors=[{k:s[k] for k in ('handle','error_code','error_stage') if k in s}
            for s in sources if not s.get('ok')]
    return dict(source_ok=bool(sources) and not errors,
                new_items=report.get('leaders',{}).get('new_items',0),
                new_alerts=report.get('resets',{}).get('new_alerts',[]),
                pending=report.get('resets',{}).get('pending',[]),source_errors=errors)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--leaders-only',action='store_true');p.add_argument('--handle')
    p.add_argument('--compact',action='store_true',help='Print only source health, new IDs and pending work; retain the full local report')
    a=p.parse_args();report=run(a.leaders_only,a.handle)
    print(json.dumps(compact_report(report) if a.compact else report,ensure_ascii=False,indent=None if a.compact else 2))
