#!/usr/bin/env python3
"""Model-3-100: 3y BTCUSDT perpetual replay; completed H1 impulse, M1 fills/exits.
Each of the 100 source configurations owns an independent state stream.
Binance Vision UM klines; costs include taker fees, slippage and archived funding.
"""
import csv,io,json,math,re,zipfile
from datetime import datetime,timezone
from urllib.request import Request,urlopen
from urllib.error import HTTPError
START=int(datetime(2023,11,16,tzinfo=timezone.utc).timestamp()*1000)
END=int(datetime(2026,11,16,tzinfo=timezone.utc).timestamp()*1000)
HOUR=3600000; MIN=60000
WARM=START-500*HOUR
BASE="https://data.binance.vision/data/futures/um"
SOURCE="Model_3-100_Google_Apps_Script.gs"
FEE=5.0; SLIP=2.0; MAX_HOLD_MIN=24*60

def get(url):
    with urlopen(Request(url,headers={"User-Agent":"Model3-100-M1-backtest/1.0"}),timeout=120) as r:return r.read()
def parse_zip(raw):
    out=[]
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        with z.open(z.namelist()[0]) as f:
            for line in io.TextIOWrapper(f,encoding="utf-8"):
                a=line.strip().split(",")
                if len(a)>=6 and a[0].isdigit():
                    out.append((int(a[0]),float(a[1]),float(a[2]),float(a[3]),float(a[4]),float(a[5])))
    return out
def month_iter():
    y,m=2023,10
    while (y,m)<=(2026,11):
        yield y,m
        m+=1
        if m==13:y,m=y+1,1
def load_m1():
    rows=[]
    for y,m in month_iter():
        if (y,m)<(2023,10) or (y,m)>(2026,11):continue
        name=f"BTCUSDT-1m-{y}-{m:02d}.zip"
        url=f"{BASE}/monthly/klines/BTCUSDT/1m/{name}"
        try: raw=get(url); rows.extend(parse_zip(raw))
        except Exception as e:
            if (y,m)!=(2026,11): raise RuntimeError(f"1m archive missing {name}: {e}")
            # Current incomplete month: load daily archives only through test end.
            for d in range(1,17):
                dn=f"BTCUSDT-1m-{y}-{m:02d}-{d:02d}.zip"
                du=f"{BASE}/daily/klines/BTCUSDT/1m/{dn}"
                try:rows.extend(parse_zip(get(du)))
                except Exception as de:raise RuntimeError(f"Missing current-month daily 1m archive {dn}: {de}")
    unique={r[0]:r for r in rows if WARM<=r[0]<END}
    bars=[(t+MIN,r[1],r[2],r[3],r[4],r[5]) for t,r in sorted(unique.items())]
    if not bars:raise RuntimeError("No 1m candles loaded")
    for a,b in zip(bars,bars[1:]):
        if b[0]-a[0]!=MIN:raise RuntimeError(f"1m data gap at {b[0]}")
    if bars[0][0]>WARM+MIN:raise RuntimeError("Insufficient 1m warmup")
    return bars
def wilder(v,n):
    out=[None]*len(v); acc=None; count=0
    for i,x in enumerate(v):
        if x is None:continue
        if acc is None:acc=x;count=1
        else:acc=(1-1/n)*acc+x/n;count+=1
        if count>=n:out[i]=acc
    return out
def indicators(bars,n):
    tr=[None]*len(bars);pdm=[0.0]*len(bars);mdm=[0.0]*len(bars);delta=[None]*len(bars)
    for i in range(1,len(bars)):
        b,p=bars[i],bars[i-1]
        tr[i]=max(b[2]-b[3],abs(b[2]-p[4]),abs(b[3]-p[4]))
        up=b[2]-p[2];dn=p[3]-b[3]
        pdm[i]=up if up>dn and up>0 else 0.;mdm[i]=dn if dn>up and dn>0 else 0.
        delta[i]=b[4]-p[4]
    atr=wilder(tr,n);ap=[atr[i-1] if i else None for i in range(len(bars))]
    ag=wilder([None if x is None else max(x,0) for x in delta],14)
    al=wilder([None if x is None else max(-x,0) for x in delta],14)
    rsi=[None if a is None or b is None else (100 if b==0 else 100-100/(1+a/b)) for a,b in zip(ag,al)]
    a14=wilder(tr,14);p=wilder(pdm,14);m=wilder(mdm,14);dx=[]
    for i,a in enumerate(a14):
        if a is None or p[i] is None or m[i] is None or a==0:dx.append(None);continue
        pi,mi=100*p[i]/a,100*m[i]/a
        dx.append(None if pi+mi==0 else 100*abs(pi-mi)/(pi+mi))
    return ap,rsi,wilder(dx,14)
def make_h1(m1):
    out=[]; bucket=None; agg=None
    for t,o,h,l,c,v in m1:
        hour=(t//HOUR)*HOUR
        if bucket is None or hour!=bucket:
            if agg and agg[0]==HOUR:out.append((bucket+HOUR,*agg[1:]))
            bucket=hour;agg=[0,o,h,l,c,v]
        agg[0]+=1;agg[2]=max(agg[2],h);agg[3]=min(agg[3],l);agg[4]=c;agg[5]+=v
    if agg and agg[0]==HOUR:out.append((bucket+HOUR,*agg[1:]))
    if not out:raise RuntimeError("Could not aggregate hourly bars")
    for a,b in zip(out,out[1:]):
        if b[0]-a[0]!=HOUR:raise RuntimeError(f"H1 aggregation gap at {b[0]}")
    return out
def impulse(b,ind,i,c):
    atr,adx,rsi=ind[0][i],ind[2][i],ind[1][i]
    if atr is None or adx is None or atr<=0 or adx<c["adx_min"] or adx>c["adx_max"]:return 0
    side=1 if b[4]>b[1] else -1 if b[4]<b[1] else 0
    if not side or b[2]-b[3]<c["impulse_atr"]*atr:return 0
    if c["rsi_mode"]=="exact" and not ((side==1 and rsi is not None and 50<=rsi<=70) or (side==-1 and rsi is not None and 30<=rsi<=50)):return 0
    if c["rsi_mode"]=="loose" and not ((side==1 and rsi is not None and 50<=rsi<=75) or (side==-1 and rsi is not None and 25<=rsi<=50)):return 0
    return side
def load_funding():
    out=[]
    for y,m in month_iter():
        if (y,m)<(2023,11) or (y,m)>(2026,11):continue
        n=f"BTCUSDT-fundingRate-{y}-{m:02d}.zip"
        u=f"{BASE}/monthly/fundingRate/BTCUSDT/{n}"
        try:raw=get(u)
        except Exception:
            if (y,m)==(2026,11):break # Binance has not published the incomplete current-month monthly archive yet.
            raise
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            with z.open(z.namelist()[0]) as f:
                rd=csv.reader(io.TextIOWrapper(f,encoding="utf-8"))
                for row in rd:
                    try:
                        t=int(float(row[0]));rate=float(row[2])
                        if START-30*86400000<=t<END:out.append((t,rate))
                    except (ValueError,IndexError):continue
    return sorted(out)
def iso(t):return datetime.fromtimestamp(t/1000,timezone.utc).isoformat()
def main():
    src=open(SOURCE,encoding="utf-8").read()
    mt=re.search(r"const M3_CONFIGS = (\[[\s\S]*?\]);",src)
    if not mt:raise RuntimeError("Could not extract M3_CONFIGS")
    configs=json.loads(mt.group(1))
    if len(configs)!=100 or any(c["symbol"]!="BTCUSDT" or c["timeframe"]!="1h" for c in configs):raise RuntimeError("Expected exactly 100 BTCUSDT/1h source configs")
    m1=load_m1();h1=make_h1(m1)
    cache={n:indicators(h1,n) for n in sorted({c["atr_period"] for c in configs})}
    funding=load_funding(); ft=[x[0] for x in funding]
    # Index completed H1 impulse bars by their close time; only act on the next minute.
    h1_by_close={b[0]:i for i,b in enumerate(h1)}
    first=next(i for i,b in enumerate(m1) if b[0]>=START)
    end=next((i for i,b in enumerate(m1) if b[0]>=END),len(m1))
    allrows=[]; per=[]
    for cfg in configs:
        ind=cache[cfg["atr_period"]]; state=None; pending=None; trades=[]; signals=0;fills=0;expired=0
        for j in range(first,end):
            t,o,hi,lo,cl,vol=m1[j]
            # Manage existing position using true 1m OHLC. Stop wins if both barriers touch in one minute.
            if state:
                state["held"]+=1;side=state["side"]
                sh=lo<=state["stop"] if side==1 else hi>=state["stop"]
                th=hi>=state["target"] if side==1 else lo<=state["target"]
                if sh or th or state["held"]>=MAX_HOLD_MIN:
                    if sh:px=o if ((side==1 and o<state["stop"]) or (side==-1 and o>state["stop"])) else state["stop"];why="STOP"
                    elif th:px=state["target"];why="TARGET"
                    else:px=cl;why="TIME"
                    exitpx=px*(1-side*SLIP/10000)
                    gross=side*(exitpx-state["entry"])/state["entry"]
                    k=bisect_left(ft,state["entry_t"]);fund=sum(rate*side for ts,rate in funding[k:] if ts<=t)
                    net=gross-2*FEE/10000-fund
                    tr={"config_rank":cfg["pf_rank"],"group_id":cfg["group_id"],"impulse_utc":iso(state["signal_t"]),"entry_utc":iso(state["entry_t"]),"exit_utc":iso(t),"side":"LONG" if side==1 else "SHORT","entry":state["entry"],"exit":exitpx,"stop":state["stop"],"target":state["target"],"rr":cfg["rr"],"exit_reason":why,"gross_bps":gross*10000,"fees_bps":2*FEE,"funding_cost_bps":fund*10000,"net_bps":net*10000,"net_R":net/(state["risk"]/state["entry"]) if state["risk"] else 0}
                    trades.append(tr);allrows.append(tr);state=None
            # Pending setup: three completed H1 bars max, but touch/fill is checked each minute.
            if not state and pending:
                age=t-pending["signal_t"]
                if age>cfg["pending_bars"]*HOUR or (pending["side"]==1 and o<=pending["stop"]) or (pending["side"]==-1 and o>=pending["stop"]):
                    pending=None;expired+=1
                else:
                    side=pending["side"];touch=lo<=pending["level"] if side==1 else hi>=pending["level"]
                    if touch:
                        raw=min(o,pending["level"]) if side==1 else max(o,pending["level"])
                        entry=raw*(1+side*SLIP/10000);risk=abs(entry-pending["stop"])
                        if risk>0 and ((side==1 and pending["stop"]<entry) or (side==-1 and pending["stop"]>entry)):
                            state={"side":side,"entry":entry,"stop":pending["stop"],"target":entry+side*cfg["rr"]*risk,"risk":risk,"entry_t":t,"signal_t":pending["signal_t"],"held":0};fills+=1
                        pending=None
            # Signal is confirmed only at a completed H1 close; next minute is eligible for entry.
            if t%HOUR==0 and not state and not pending:
                hi_idx=h1_by_close.get(t)
                if hi_idx is not None and h1[hi_idx][0]>=START:
                    sig=impulse(h1[hi_idx],ind,hi_idx,cfg)
                    if sig:
                        b=h1[hi_idx];span=b[2]-b[3]
                        level=b[2]-cfg["retracement"]*span if sig==1 else b[3]+cfg["retracement"]*span
                        stop=b[3] if sig==1 else b[2]
                        if abs(level-stop)>0:pending={"side":sig,"level":level,"stop":stop,"signal_t":t}
                        signals+=1
        wins=[x for x in trades if x["net_bps"]>0];loss=[x for x in trades if x["net_bps"]<=0]
        gp=sum(x["net_bps"] for x in wins);gl=-sum(x["net_bps"] for x in loss);eq=peak=dd=0
        for x in trades:eq+=x["net_bps"];peak=max(peak,eq);dd=min(dd,eq-peak)
        per.append({"pf_rank":cfg["pf_rank"],"group_id":cfg["group_id"],"source_oos_trades":cfg["oos_trades"],"source_oos_pf":cfg["oos_profit_factor"],"impulse_signals":signals,"entry_fills":fills,"closed_trades":len(trades),"wins":len(wins),"losses":len(loss),"win_rate_pct":100*len(wins)/len(trades) if trades else 0,"profit_factor":gp/gl if gl else None,"net_bps":sum(x["net_bps"] for x in trades),"max_drawdown_bps":dd,"pending_expired_or_invalidated":expired,"open_at_end":bool(state),"pending_at_end":bool(pending)})
    allrows.sort(key=lambda x:(x["exit_utc"],x["config_rank"]))
    for name,rows in [("trades.csv",allrows),("per_config.csv",sorted(per,key=lambda x:x["pf_rank"]))]:
        with open(name,"w",newline="") as f:
            fields=list(rows[0]) if rows else ["config_rank"];w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
    wins=sum(x["net_bps"]>0 for x in allrows);loss=len(allrows)-wins;gp=sum(max(0,x["net_bps"]) for x in allrows);gl=-sum(min(0,x["net_bps"]) for x in allrows)
    eq=peak=dd=0
    for x in allrows:eq+=x["net_bps"];peak=max(peak,eq);dd=min(dd,eq-peak)
    summary={"status":"COMPLETE","method":"3-year completed H1 impulse qualification; M1 pending-order fills and M1 stop/target/time exits; 100 independent config states","period_utc":{"start":"2023-11-16T00:00:00Z","end_exclusive":"2026-11-16T00:00:00Z"},"symbol":"BTCUSDT USD-M perpetual","configs":100,"m1_candles":len(m1),"h1_candles":len(h1),"test_m1_candles":end-first,"closed_trades_across_independent_streams":len(allrows),"wins":wins,"losses":loss,"win_rate_pct":100*wins/len(allrows) if allrows else 0,"profit_factor":gp/gl if gl else None,"net_bps_sum_across_independent_streams":sum(x["net_bps"] for x in allrows),"max_drawdown_bps_sequential_sum":dd,"fee_bps_per_side":FEE,"slippage_bps_per_side":SLIP,"funding_records":len(funding),"funding_note":"Official monthly funding archives included through the last published complete month; current incomplete month omitted if archive unavailable.","intraminute_collision_rule":"If stop and target both touch in one 1m candle, stop is assumed first (conservative).","end_state":"Open trades/pending orders are not force-closed"}
    with open("summary.json","w") as f:json.dump(summary,f,indent=2)
    print(json.dumps(summary,indent=2))
if __name__=="__main__":main()
