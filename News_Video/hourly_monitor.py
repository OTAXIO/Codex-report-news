"""Hourly source cache + reset queue. No model, TTS, render or upload API calls."""
import argparse,datetime as dt,json,io
from contextlib import redirect_stdout
import news_video as n
import leader_sources,reset_alerts

def run(leaders_only=False,handle=None):
    report=dict(started=dt.datetime.now(n.UTC).isoformat(),model_calls=0)
    # Arm before first collection so old cached posts never become new alerts.
    report['reset_baseline']=reset_alerts.scan()
    if not leaders_only:
        with redirect_stdout(io.StringIO()):report['social']=n.collect('social')
    report['leaders']=leader_sources.collect(only=handle)
    report['resets']=reset_alerts.scan()
    report['finished']=dt.datetime.now(n.UTC).isoformat()
    n.dump(n.ROOT/'data/hourly-monitor-last.json',report)
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--leaders-only',action='store_true');p.add_argument('--handle')
    a=p.parse_args();print(json.dumps(run(a.leaders_only,a.handle),ensure_ascii=False,indent=2))
