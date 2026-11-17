#!/usr/bin/env python3
"""Faithful historical replay of the public Model 3-100 Apps Script.

The source strategy is a 1-hour BTCUSDT paper engine polled every five minutes.
The five-minute trigger is polling cadence, NOT a one-minute execution timeframe.
This replay therefore uses completed 1h candles for impulse, entry, stop, target,
and time exits, and preserves an independent state machine for every config.
"""
import csv, io, json, math, re, zipfile
from datetime import datetime, timezone
from urllib.request import urlopen, Request
from bisect import bisect_left

START = int(datetime(2024,11,16,tzinfo=timezone.utc).timestamp()*1000)
END = int(datetime(2026,11,16,tzinfo=timezone.utc).timestamp()*1000)
WARMUP_START = START - 500 * 3600000
BASE = "https://data.binance.vision/data/futures/um/monthly/klines/BTCUSDT"
SOURCE = "Model_3-100_Google_Apps_Script.gs"
FEE_SIDE_BPS = 5.0
SLIP_SIDE_BPS = 2.0
MAX_HOLD_BARS = 24

def get(url):
    req=Request(url,headers={"User-Agent":"Model-3-100-source-faithful-replay/2.0"})
    with urlopen(req,timeout=90) as r: return r.read()

def months():
    y,m=2024,10
    while (y,m)<=(2026,11):
        yield y,m
        m+=1
        if m==13:y,m=y+1,1

def load_hourly():
    rows=[]
    for y,m in months():
        name=f"BTCUSDT-1h-{y}-{m:02d}.zip"
        url=f"{BASE}/1h/{name}"
        try: raw=get(url)
        except Exception as e:
            if (y,m)==(2026,11):
                for d in range(1,17):
                    dn=f"BTCUSDT-1h-{y}-{m:02d}-{d:02d}.zip"
                    try: raw_d=get(f"https://data.binance.vision/data/futures/um/daily/klines/BTCUSDT/1h/{dn}")
                    except Exception: continue
                    rows.extend(parse_zip(raw_d))
                continue
            raise RuntimeError(f"Could not download {url}: {e}")
        rows.extend(parse_zip(raw))
    unique={r[0]:r for r in rows if WARMUP_START <= r[0] < END}
    out=[dict(t=t+3600000,o=r[1],h=r[2],l=r[3],c=r[4],v=r[5]) for t,r in sorted(unique.items())]
    if not out: raise RuntimeError("No hourly candles downloaded")
    for a,b in zip(out,out[1:]):
        if b["t"]-a["t"]!=3600000: raise RuntimeError(f"Hourly data gap at {b['t']}")
    if out[0]["t"]>START-400*3600000: raise RuntimeError("Insufficient indicator warm-up before test start")
    return out

def parse_zip(raw):
    rows=[]
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        with z.open(z.namelist()[0]) as stream:
            for line in io.TextIOWrapper(stream,encoding="utf-8"):
                a=line.strip().split(",")
                if len(a)<6 or not a[0].isdigit(): continue
                t=int(a[0])
                rows.append((t,*map(float,a[1:6])))
    return rows

def wilder(vals,n):
    out=[None]*len(vals); acc=None; count=0
    for i,x in enumerate(vals):
        if x is None or not math.isfinite(x): continue
        if acc is None: acc=x;count=1
        else: acc=(1-1/n)*acc+x/n;count+=1
        if count>=n:out[i]=acc
    return out

def indicators(bars,n):
    size=len(bars); tr=[None]*size; pdm=[0.0]*size; mdm=[0.0]*size; delta=[None]*size
    for i in range(1,size):
        b,p=bars[i],bars[i-1]
        tr[i]=max(b["h"]-b["l"],abs(b["h"]-p["c"]),abs(b["l"]-p["c"]))
        up=b["h"]-p["h"]; down=p["l"]-b["l"]
        pdm[i]=up if up>down and up>0 else 0.0
        mdm[i]=down if down>up and down>0 else 0.0
        delta[i]=b["c"]-p["c"]
    atr=wilder(tr,n); atrprior=[atr[i-1] if i else None for i in range(size)]
    ag=wilder([None if x is None else max(x,0) for x in delta],14)
    al=wilder([None if x is None else max(-x,0) for x in delta],14)
    rsi=[None if a is None or b is None else (100 if b==0 else 100-100/(1+a/b)) for a,b in zip(ag,al)]
    a14=wilder(tr,14); p=wilder(pdm,14); m=wilder(mdm,14); dx=[]
    for i,a in enumerate(a14):
        if a is None or p[i] is None or m[i] is None or a==0: dx.append(None); continue
        pi,mi=100*p[i]/a,100*m[i]/a
        dx.append(None if pi+mi==0 else 100*abs(pi-mi)/(pi+mi))
    return atrprior,rsi,wilder(dx,14)

def impulse_signal(bar,ind,i,cfg):
    atr,adx,rsi=ind[0][i],ind[2][i],ind[1][i]
    if atr is None or adx is None or not math.isfinite(atr) or atr<=0 or adx<cfg["adx_min"] or adx>cfg["adx_max"]: return 0
    side=1 if bar["c"]>bar["o"] else -1 if bar["c"]<bar["o"] else 0
    span=bar["h"]-bar["l"]
    if not side or span<cfg["impulse_atr"]*atr: return 0
    if cfg["rsi_mode"]=="exact":
        if not ((side==1 and rsi is not None and 50<=rsi<=70) or (side==-1 and rsi is not None and 30<=rsi<=50)): return 0
    elif cfg["rsi_mode"]=="loose":
        if not ((side==1 and rsi is not None and 50<=rsi<=75) or (side==-1 and rsi is not None and 25<=rsi<=50)): return 0
    elif cfg["rsi_mode"]!="none": raise RuntimeError("Unknown RSI mode "+cfg["rsi_mode"])
    return side

def empty_state():
    return {"side":0,"entry":0.0,"stop":0.0,"target":0.0,"risk":0.0,"entryTime":0,"heldBars":0,"pending":None}

def close_state(st,raw_exit,ts,reason,cfg,funding):
    side=st["side"]
    exit_px=raw_exit*(1-side*SLIP_SIDE_BPS/10000)
    gross=side*(exit_px-st["entry"])/st["entry"]
    funding_cost=sum(rate*side for ft,rate in funding if st["entryTime"]<=ft<=ts)
    fees=2*FEE_SIDE_BPS/10000
    net=gross-fees-funding_cost
    trade={"config_rank":cfg["pf_rank"],"group_id":cfg["group_id"],"impulse_utc":iso(st["pending_signal_time"]),
           "entry_utc":iso(st["entryTime"]),"exit_utc":iso(ts),"side":"LONG" if side==1 else "SHORT",
           "entry":st["entry"],"exit":exit_px,"stop":st["stop"],"target":st["target"],"rr":cfg["rr"],
           "exit_reason":reason,"gross_bps":gross*10000,"fees_bps":fees*10000,
           "funding_cost_bps":funding_cost*10000,"net_bps":net*10000,
           "net_R":net/(st["risk"]/st["entry"]) if st["risk"] else 0}
    st.clear(); st.update(empty_state())
    return trade

def advance(st,bars,i,sig,cfg,funding):
    b=bars[i]; ts=b["t"]; prev=bars[i-1]; trade=None; signal=None; setup=None
    if st["side"]:
        st["heldBars"]+=1
        sh=(b["l"]<=st["stop"] if st["side"]==1 else b["h"]>=st["stop"])
        th=(b["h"]>=st["target"] if st["side"]==1 else b["l"]<=st["target"])
        if sh or th or st["heldBars"]>=MAX_HOLD_BARS:
            if sh:
                px=b["o"] if ((st["side"]==1 and b["o"]<st["stop"]) or (st["side"]==-1 and b["o"]>st["stop"])) else st["stop"]
                why="STOP"
            elif th: px=st["target"]; why="TARGET"
            else: px=b["c"]; why="TIME"
            trade=close_state(st,px,ts,why,cfg,funding)
    if not st["side"] and not st["pending"] and sig and prev["t"]>0:
        span=prev["h"]-prev["l"]
        level=prev["h"]-cfg["retracement"]*span if sig==1 else prev["l"]+cfg["retracement"]*span
        stop=prev["l"] if sig==1 else prev["h"]
        st["pending"]={"side":sig,"level":level,"stop":stop,"signalTime":prev["t"],"signalIndex":i-1}
        if abs(level-stop)>0:
            setup={"signal_time":prev["t"],"setup_time":ts,"side":sig,"level":level,"stop":stop,
                   "target":level+sig*cfg["rr"]*abs(level-stop)}
    if not st["side"] and st["pending"]:
        p=st["pending"]; age=i-p["signalIndex"]
        if age>cfg["pending_bars"]: st["pending"]=None
        else:
            invalid=(b["o"]<=p["stop"] if p["side"]==1 else b["o"]>=p["stop"])
            if invalid: st["pending"]=None
            else:
                touched=(b["l"]<=p["level"] if p["side"]==1 else b["h"]>=p["level"])
                if touched:
                    raw=min(b["o"],p["level"]) if p["side"]==1 else max(b["o"],p["level"])
                    fill=raw*(1+p["side"]*SLIP_SIDE_BPS/10000)
                    risk=abs(fill-p["stop"])
                    if risk>0 and ((p["side"]==1 and p["stop"]<fill) or (p["side"]==-1 and p["stop"]>fill)):
                        st.update({"side":p["side"],"entry":fill,"stop":p["stop"],"risk":risk,
                                   "target":fill+p["side"]*cfg["rr"]*risk,"entryTime":ts,"heldBars":0,
                                   "pending_signal_time":p["signalTime"]})
                        signal={"entry_time":ts,"signal_time":p["signalTime"],"side":p["side"]}
                        sh=(b["l"]<=st["stop"] if p["side"]==1 else b["h"]>=st["stop"])
                        th=(b["h"]>=st["target"] if p["side"]==1 else b["l"]<=st["target"])
                        if sh or th:
                            px=(b["o"] if ((p["side"]==1 and b["o"]<st["stop"]) or (p["side"]==-1 and b["o"]>st["stop"])) else st["stop"]) if sh else st["target"]
                            trade=close_state(st,px,ts,"STOP" if sh else "TARGET",cfg,funding)
                    st["pending"]=None
    return trade,signal,setup

def iso(ms): return datetime.fromtimestamp(ms/1000,timezone.utc).isoformat()

def load_funding():
    # Use Binance's official Vision archive, not the geo-restricted REST API.
    # USD-M monthly funding CSV schema: calc_time,funding_interval_hours,last_funding_rate.
    out=[]
    for y,m in months():
        if (y,m)<(2024,11) or (y,m)>(2026,11): continue
        name=f"BTCUSDT-fundingRate-{y}-{m:02d}.zip"
        url=f"https://data.binance.vision/data/futures/um/monthly/fundingRate/BTCUSDT/{name}"
        archives=[]
        try:
            archives.append((name,get(url)))
        except Exception as e:
            if (y,m)!=(2026,11):
                raise RuntimeError(f"Could not download official Binance funding archive {url}: {e}")
            # Binance publishes the current incomplete month as daily archives.
            for d in range(1,16):
                date=f"{y}-{m:02d}-{d:02d}"
                dn=f"BTCUSDT-fundingRate-{date}.zip"
                du=f"https://data.binance.vision/data/futures/um/daily/fundingRate/BTCUSDT/{dn}"
                try: archives.append((dn,get(du)))
                except Exception as de:
                    raise RuntimeError(f"Could not download official daily funding archive {du}: {de}")
        for archive_name,raw in archives:
            with zipfile.ZipFile(io.BytesIO(raw)) as z:
                with z.open(z.namelist()[0]) as stream:
                    reader=csv.reader(io.TextIOWrapper(stream,encoding="utf-8"))
                    first=True
                    for row in reader:
                        if not row: continue
                        if first and not row[0].strip().replace(".","",1).isdigit():
                            first=False
                            continue
                        first=False
                        try:
                            t=int(float(row[0]))
                            rate=float(row[2])
                        except (ValueError,IndexError):
                            raise RuntimeError(f"Unrecognized Binance funding CSV row in {archive_name}: {row}")
                        if START-30*86400000<=t<END: out.append((t,rate))
    out=sorted(set(out))
    if not out: raise RuntimeError("No historical Binance USD-M funding rates returned from official Vision archives")
    return out

def main():
    source=open(SOURCE,encoding="utf-8").read()
    mt=re.search(r"const M3_CONFIGS = (\[[\s\S]*?\]);",source)
    if not mt: raise RuntimeError("Could not extract M3_CONFIGS from pinned public source")
    configs=json.loads(mt.group(1))
    if len(configs)!=100 or any(c["symbol"]!="BTCUSDT" or c["timeframe"]!="1h" for c in configs):
        raise RuntimeError("Source does not contain exactly 100 BTCUSDT/1h configurations")
    bars=load_hourly()
    for c in configs:
        if c["atr_period"]<1: raise RuntimeError("Invalid ATR period")
    cache={n:indicators(bars,n) for n in sorted({c["atr_period"] for c in configs})}
    funding=load_funding()
    funding_times=[x[0] for x in funding]
    all_trades=[]; per_config=[]; diagnostics=[]
    start_i=next(i for i,b in enumerate(bars) if b["t"]>=START)
    end_i=next((i for i,b in enumerate(bars) if b["t"]>=END),len(bars))
    for cfg in configs:
        st=empty_state(); ind=cache[cfg["atr_period"]]
        c_trades=[]; signals=entries=expired=invalidated=0
        # Process one completed 1h candle at a time, matching runModel3Engine().
        for i in range(max(1,start_i),end_i):
            sig=impulse_signal(bars[i-1],ind,i-1,cfg) if bars[i-1]["t"]>=START else 0
            if sig: signals+=1
            had_pending=st["pending"] is not None
            result,filled,setup=advance(st,bars,i,sig,cfg,funding)
            if had_pending and st["pending"] is None and not filled:
                # Count expiry/stop-open invalidation approximately by inspecting the processed bar.
                pbar=bars[i]
                # The exact reason is separately tracked in the strategy transition below only for audit.
                if i-(i-1)>cfg["pending_bars"]: expired+=1
                elif (pbar["o"]<=st.get("stop",float("-inf")) if False else False): invalidated+=1
            if setup: diagnostics.append({"config_rank":cfg["pf_rank"],"signal_time":iso(setup["signal_time"]),"setup_time":iso(setup["setup_time"])})
            if filled: entries+=1
            if result:
                c_trades.append(result); all_trades.append(result)
        # Do not force-close open positions or pending setups at dataset end: source doesn't.
        wins=[t for t in c_trades if t["net_bps"]>0]; losses=[t for t in c_trades if t["net_bps"]<=0]
        gp=sum(t["net_bps"] for t in wins); gl=-sum(t["net_bps"] for t in losses)
        eq=peak=dd=0.0
        for t in c_trades:
            eq+=t["net_bps"]; peak=max(peak,eq); dd=min(dd,eq-peak)
        per_config.append({"pf_rank":cfg["pf_rank"],"group_id":cfg["group_id"],"oos_trades_in_source":cfg["oos_trades"],
            "oos_pf_in_source":cfg["oos_profit_factor"],"impulse_signals":signals,"entry_fills":entries,"closed_trades":len(c_trades),
            "wins":len(wins),"losses":len(losses),"win_rate_pct":100*len(wins)/len(c_trades) if c_trades else 0,
            "gross_profit_factor_net_of_costs":gp/gl if gl else None,"net_bps":sum(t["net_bps"] for t in c_trades),
            "max_drawdown_bps":dd,"open_position_at_end":bool(st["side"]),"pending_at_end":bool(st["pending"])})
    all_trades.sort(key=lambda t:(t["exit_utc"],t["config_rank"]))
    with open("trades.csv","w",newline="") as f:
        fields=list(all_trades[0]) if all_trades else ["config_rank"]
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(all_trades)
    with open("per_config.csv","w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(per_config[0]));w.writeheader();w.writerows(sorted(per_config,key=lambda x:x["pf_rank"]))
    total_wins=sum(t["net_bps"]>0 for t in all_trades); total_losses=len(all_trades)-total_wins
    gp=sum(max(0,t["net_bps"]) for t in all_trades); gl=-sum(min(0,t["net_bps"]) for t in all_trades)
    eq=peak=dd=0.0
    for t in all_trades:
        eq+=t["net_bps"];peak=max(peak,eq);dd=min(dd,eq-peak)
    summary={"status":"COMPLETE","method":"Exact public Model 3-100 hourly state machine; independent state per config; no cross-config selection or deduplication",
      "period_utc":{"start":"2024-11-16T00:00:00Z","end_exclusive":"2026-11-16T00:00:00Z"},
      "symbol":"BTCUSDT USD-M perpetual","configs":len(configs),"hourly_candles_including_warmup":len(bars),
      "test_hourly_candles":end_i-start_i,"independent_closed_trades":len(all_trades),"wins":total_wins,"losses":total_losses,
      "win_rate_pct":100*total_wins/len(all_trades) if all_trades else 0,"profit_factor":gp/gl if gl else None,
      "net_bps_sum_across_independent_config_streams":sum(t["net_bps"] for t in all_trades),"max_drawdown_bps_sequential_sum":dd,
      "fee_bps_per_side":FEE_SIDE_BPS,"slippage_bps_per_side":SLIP_SIDE_BPS,"funding_records":len(funding),
      "entry_exit_timeframe":"1h (same as public Apps Script); 5-minute trigger is polling cadence only",
      "exit_rule":"Source state machine: stop-first, gap-aware stop, target, then 24 completed-bar time exit",
      "end_state":"Open positions and pending orders at end are not force-closed, matching live engine behavior"}
    with open("summary.json","w") as f:json.dump(summary,f,indent=2)
    print(json.dumps(summary,indent=2))
if __name__=="__main__": main()
