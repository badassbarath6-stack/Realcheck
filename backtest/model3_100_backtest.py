#!/usr/bin/env python3
"""Model 3-100 BTCUSDT two-year historical replay.
Pinned strategy source supplies the 100 configurations. Hourly impulse is confirmed
at close; entry is searched only in subsequent 1m candles. One selected trade per
impulse (lowest PF rank among configurations whose entry is reached first).
"""
import csv, io, json, math, os, re, sys, time, zipfile
from datetime import datetime, timezone
from urllib.request import urlopen, Request

START = int(datetime(2024,11,16,tzinfo=timezone.utc).timestamp()*1000)
END = int(datetime(2026,11,16,tzinfo=timezone.utc).timestamp()*1000)
BASE = "https://data.binance.vision/data/futures/um/monthly/klines/BTCUSDT"
SOURCE = "Model_3-100_Google_Apps_Script.gs"
FEE_SIDE_BPS = 5.0
SLIP_SIDE_BPS = 7.0  # live evaluator's documented fill assumption
MAX_HOLD_HOURS = 24

def get(url):
    req=Request(url,headers={"User-Agent":"Model-3-100-historical-research/1.0"})
    with urlopen(req,timeout=60) as r: return r.read()

def months():
    y,m=2024,11
    while (y,m)<=(2026,11):
        yield y,m
        m+=1
        if m==13:y,m=y+1,1

def load_tf(tf):
    rows=[]
    for y,m in months():
        name=f"BTCUSDT-{tf}-{y}-{m:02d}.zip"
        url=f"{BASE}/{tf}/{name}"
        try: raw=get(url)
        except Exception as e:
            # November 2026 is partial; use daily archives for current month.
            if (y,m)==(2026,11):
                for d in range(1,17):
                    dn=f"BTCUSDT-{tf}-{y}-{m:02d}-{d:02d}.zip"
                    try: z=zipfile.ZipFile(io.BytesIO(get(f"https://data.binance.vision/data/futures/um/daily/klines/BTCUSDT/{tf}/{dn}")))
                    except Exception: continue
                    for line in io.TextIOWrapper(z.open(z.namelist()[0]),encoding="utf-8"):
                        a=line.strip().split(",")
                        if len(a)>=6:
                            if not a[0].isdigit(): continue  # Binance Vision CSV header row\n            t=int(a[0])
                            if START<=t<END: rows.append((t,*map(float,a[1:6])))
                continue
            raise RuntimeError(f"Could not download {url}: {e}")
        z=zipfile.ZipFile(io.BytesIO(raw))
        for line in io.TextIOWrapper(z.open(z.namelist()[0]),encoding="utf-8"):
            a=line.strip().split(",")
            if len(a)>=6:
                t=int(a[0])
                if START<=t<END: rows.append((t,*map(float,a[1:6])))
    rows.sort()
    if not rows: raise RuntimeError(f"No {tf} data downloaded")
    # de-duplicate timestamps
    return [dict(t=r[0],o=r[1],h=r[2],l=r[3],c=r[4],v=r[5]) for r in {r[0]:r for r in rows}.values()]

def wilder(vals,n):
    out=[None]*len(vals); acc=None; count=0
    for i,x in enumerate(vals):
        if x is None or not math.isfinite(x): continue
        if acc is None: acc=x;count=1
        else: acc=(1-1/n)*acc+x/n;count+=1
        if count>=n:out[i]=acc
    return out

def indicators(bars, n):
    size=len(bars); tr=[None]*size; pdm=[0.0]*size; mdm=[0.0]*size; delta=[None]*size
    for i in range(1,size):
        b,p=bars[i],bars[i-1]
        tr[i]=max(b['h']-b['l'],abs(b['h']-p['c']),abs(b['l']-p['c']))
        up=b['h']-p['h']; down=p['l']-b['l']
        pdm[i]=up if up>down and up>0 else 0.0
        mdm[i]=down if down>up and down>0 else 0.0
        delta[i]=b['c']-p['c']
    atr=wilder(tr,n); atrprior=[atr[i-1] if i else None for i in range(size)]
    ag=wilder([None if x is None else max(x,0) for x in delta],14)
    al=wilder([None if x is None else max(-x,0) for x in delta],14)
    rsi=[None if a is None or b is None else (100 if b==0 else 100-100/(1+a/b)) for a,b in zip(ag,al)]
    a14=wilder(tr,14); p=wilder(pdm,14); m=wilder(mdm,14); dx=[]
    for i,a in enumerate(a14):
        if a is None or p[i] is None or m[i] is None or a==0: dx.append(None);continue
        pi,mi=100*p[i]/a,100*m[i]/a
        dx.append(None if pi+mi==0 else 100*abs(pi-mi)/(pi+mi))
    return atrprior,rsi,wilder(dx,14)

def main():
    source=open(SOURCE,encoding="utf-8").read()
    mt=re.search(r"const M3_CONFIGS = (\[[\s\S]*?\]);",source)
    if not mt: raise RuntimeError("Could not extract M3_CONFIGS from pinned source")
    configs=json.loads(mt.group(1))
    if len(configs)!=100 or any(c["symbol"]!="BTCUSDT" or c["timeframe"]!="1h" for c in configs):
        raise RuntimeError("Source does not contain exactly 100 BTCUSDT/1h configurations")
    hourly=load_tf("1h"); minute=load_tf("1m")
    if len(hourly)<1000 or len(minute)<100000: raise RuntimeError("Downloaded data unexpectedly incomplete")
    # Reject missing hourly candles; missing minute data is recorded and not silently interpolated.
    for a,b in zip(hourly,hourly[1:]):
        if b["t"]-a["t"]!=3600000: raise RuntimeError(f"Hourly data gap at {b['t']}")
    min_index={b["t"]:i for i,b in enumerate(minute)}
    for a,b in zip(minute,minute[1:]):
        if b["t"]-a["t"]!=60000: raise RuntimeError(f"1m data gap at {b['t']}")
    cache={}
    for c in configs:
        n=c["atr_period"]
        if n not in cache: cache[n]=indicators(hourly,n)
    trades=[]; used_impulses=set()
    # Evaluate every configuration, collect first touch per config; choose best PF rank
    # for each originating hourly impulse. No same-impulse duplicate portfolio entries.
    candidates={}
    for c in configs:
        atr,rsi,adx=cache[c["atr_period"]]
        for i,b in enumerate(hourly):
            if i==0 or b["t"]<START or b["t"]>=END: continue
            if atr[i] is None or adx[i] is None or adx[i]<c["adx_min"] or adx[i]>c["adx_max"]: continue
            side=1 if b["c"]>b["o"] else -1 if b["c"]<b["o"] else 0
            span=b["h"]-b["l"]
            if not side or span<c["impulse_atr"]*atr[i]: continue
            rv=rsi[i]
            if c["rsi_mode"]=="exact" and not ((side==1 and rv is not None and 50<=rv<=70) or (side==-1 and rv is not None and 30<=rv<=50)): continue
            if c["rsi_mode"]=="loose" and not ((side==1 and rv is not None and 50<=rv<=75) or (side==-1 and rv is not None and 25<=rv<=50)): continue
            level=b["h"]-c["retracement"]*span if side==1 else b["l"]+c["retracement"]*span
            stop=b["l"] if side==1 else b["h"]
            start_t=b["t"]+3600000; end_t=b["t"]+(c["pending_bars"]+1)*3600000
            j=min_index.get(start_t)
            if j is None: raise RuntimeError(f"Missing first eligible minute {start_t}")
            found=None
            while j<len(minute) and minute[j]["t"]<end_t:
                m=minute[j]
                touched=(m["l"]<=level if side==1 else m["h"]>=level)
                stopped=(m["l"]<=stop if side==1 else m["h"]>=stop)
                if stopped:
                    # Stop is outside impulse extreme; if entry and stop both touch
                    # in the same minute, preserve source stop-first conservative ordering.
                    if touched: found={"immediate_stop":True,"minute":m}
                    break
                if touched:
                    raw=min(m["o"],level) if side==1 else max(m["o"],level)
                    fill=raw*(1+side*SLIP_SIDE_BPS/10000)
                    risk=abs(fill-stop)
                    if risk>0 and (stop<fill if side==1 else stop>fill):
                        found={"fill":fill,"risk":risk,"stop":stop,"side":side,"entry_t":m["t"],"minute":m}
                    break
                j+=1
            if found is None: continue
            if found.get("immediate_stop"):
                continue
            key=b["t"]
            candidates.setdefault(key,[]).append((c,found,b))
    for impulse, hits in sorted(candidates.items()):
        c,x,imp=sorted(hits,key=lambda z:z[0]["pf_rank"])[0]
        side=x["side"]; fill=x["fill"]; risk=x["risk"]; stop=x["stop"]
        target=fill+side*c["rr"]*risk
        entry_i=min_index[x["entry_t"]]
        exit_price=None; exit_t=None; outcome="TIME"
        last_i=min(len(minute)-1,entry_i+MAX_HOLD_HOURS*60)
        for k in range(entry_i,len(minute)):
            m=minute[k]
            if k>last_i: break
            st=m["l"]<=stop if side==1 else m["h"]>=stop
            tg=m["h"]>=target if side==1 else m["l"]<=target
            if st: exit_price=stop*(1-side*SLIP_SIDE_BPS/10000);exit_t=m["t"];outcome="LOSS";break
            if tg: exit_price=target*(1-side*SLIP_SIDE_BPS/10000);exit_t=m["t"];outcome="WIN";break
        if exit_price is None:
            m=minute[last_i];exit_price=m["c"]*(1-side*SLIP_SIDE_BPS/10000);exit_t=m["t"]
        gross=side*(exit_price-fill)/fill*10000
        fees=2*FEE_SIDE_BPS
        net=gross-fees
        trades.append({"impulse_utc":datetime.fromtimestamp(impulse/1000,timezone.utc).isoformat(),"entry_utc":datetime.fromtimestamp(x["entry_t"]/1000,timezone.utc).isoformat(),"exit_utc":datetime.fromtimestamp(exit_t/1000,timezone.utc).isoformat(),"rank":c["pf_rank"],"group_id":c["group_id"],"side":"LONG" if side==1 else "SHORT","entry":fill,"stop":stop,"target":target,"rr":c["rr"],"outcome":outcome,"gross_bps":gross,"fees_bps":fees,"funding_bps":0.0,"net_bps":net,"net_r":net/(risk/fill*10000)})
    # CSV outputs
    with open("trades.csv","w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(trades[0]) if trades else ["impulse_utc"]);w.writeheader();w.writerows(trades)
    grosswins=sum(max(0,t["net_bps"]) for t in trades); grossloss=sum(abs(min(0,t["net_bps"])) for t in trades)
    equity=peak=0.0; maxdd=0.0
    for t in trades:
        equity+=t["net_bps"];peak=max(peak,equity);maxdd=min(maxdd,equity-peak)
    summary={"status":"COMPLETE","period_utc":{"start":"2024-11-16T00:00:00Z","end_exclusive":"2026-11-16T00:00:00Z"},"symbol":"BTCUSDT USDT-M perpetual","configs":len(configs),"hourly_candles":len(hourly),"minute_candles":len(minute),"selected_trades":len(trades),"wins":sum(t["net_bps"]>0 for t in trades),"losses":sum(t["net_bps"]<=0 for t in trades),"win_rate_pct":100*sum(t["net_bps"]>0 for t in trades)/len(trades) if trades else 0,"profit_factor":grosswins/grossloss if grossloss else None,"net_bps":sum(t["net_bps"] for t in trades),"net_r":sum(t["net_r"] for t in trades),"max_drawdown_bps":maxdd,"fee_bps_round_trip":10,"slippage_bps_per_side":SLIP_SIDE_BPS,"funding":"NOT INCLUDED - funding history not yet incorporated","exit_rule":"1m OHLC; stop-first if stop and target both touched; 24h max hold","selection_rule":"one trade per originating impulse; lowest original PF rank among configs with an eligible entry touch","entry_timing":"completed 1H impulse; subsequent 1m touch only","source_config_count":len(configs)}
    with open("summary.json","w") as f:json.dump(summary,f,indent=2)
    # Per-rank descriptive config-level hit counts (not independent portfolio trades).
    with open("per_config.csv","w",newline="") as f:
        w=csv.writer(f);w.writerow(["pf_rank","group_id","oos_pf","oos_trades","selected_portfolio_trades"])
        counts={}
        for t in trades:counts[t["rank"]]=counts.get(t["rank"],0)+1
        for c in sorted(configs,key=lambda z:z["pf_rank"]):w.writerow([c["pf_rank"],c["group_id"],c["oos_profit_factor"],c["oos_trades"],counts.get(c["pf_rank"],0)])
    print(json.dumps(summary,indent=2))
if __name__=="__main__":main()
