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

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--leaders-only',action='store_true');p.add_argument('--handle')
    a=p.parse_args();print(json.dumps(run(a.leaders_only,a.handle),ensure_ascii=False,indent=2))
