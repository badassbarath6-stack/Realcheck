#!/usr/bin/env python3
"""Five-year Top-100 Impulse Retracer replay: forming H1 detection, M1 alert, next-minute fills."""
import argparse, bisect, csv, hashlib, io, json, math, os, time, urllib.parse, urllib.request, zipfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
CACHE=ROOT/".backtest-cache-top100"
OUT=ROOT/"backtest-results-top100-5y"
BASE="https://data.binance.vision/data/futures/um"
SYMBOLS=("BTCUSDT","ETHUSDT")
MIN=60_000; HOUR=60*MIN; DAY=24*HOUR
FEE_BPS=5.0
SLIPPAGE=(2.0,7.0)
RR=2.0
MAX_HOLD=1440
ATR_PERIODS=(14,20,25)
TRAIN_FRACTION=0.60

def utc_ms(s):
    return int(datetime.strptime(s,"%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp()*1000)
def month_range(start_ms,end_ms):
    a=datetime.fromtimestamp(start_ms/1000,timezone.utc); b=datetime.fromtimestamp((end_ms-1)/1000,timezone.utc)
    y,m=a.year,a.month; out=[]
    while (y,m)<=(b.year,b.month):
        out.append(f"{y:04d}-{m:02d}")
        m+=1
        if m==13:y,m=y+1,1
    return out
def day_range(start_ms,end_ms):
    a=datetime.fromtimestamp(start_ms/1000,timezone.utc); b=datetime.fromtimestamp((end_ms-1)/1000,timezone.utc)
    cur=a.date(); out=[]
    while cur<=b.date():
        out.append(cur.isoformat()); cur=cur.fromordinal(cur.toordinal()+1)
    return out
def http_bytes(url):
    last=None
    for attempt in range(4):
        try:
            req=urllib.request.Request(url,headers={"User-Agent":"Impulse-Retracer-Top100-5Y/1.0","Accept":"*/*"})
            with urllib.request.urlopen(req,timeout=120) as r:return r.read()
        except Exception as e:
            last=e; time.sleep(1.5*(attempt+1))
    raise RuntimeError(f"Download failed: {url}: {last}")
def archive_file(url):
    CACHE.mkdir(parents=True,exist_ok=True)
    path=CACHE/Path(urllib.parse.urlparse(url).path).name
    if not path.exists():path.write_bytes(http_bytes(url))
    check=http_bytes(url+".CHECKSUM").decode("utf-8","replace").strip().split()[0].lower()
    if len(check)!=64 or hashlib.sha256(path.read_bytes()).hexdigest()!=check:
        path.unlink(missing_ok=True); raise RuntimeError(f"SHA-256 verification failed: {url}")
    return path,check
def parse_kline_zip(path,start_ms,end_ms):
    rows=[]
    with zipfile.ZipFile(path) as z:
        names=[n for n in z.namelist() if n.lower().endswith(".csv")]
        if not names:raise RuntimeError(f"No CSV in {path}")
        for name in names:
            with z.open(name) as raw:
                for row in csv.reader(io.TextIOWrapper(raw,encoding="utf-8",newline="")):
                    if len(row)<6:continue
                    try:
                        t=int(float(row[0])); o,h,l,c,v=map(float,row[1:6])
                    except (ValueError,TypeError):continue
                    if not start_ms<=t<end_ms:continue
                    if not all(math.isfinite(x) for x in (o,h,l,c,v)) or h<max(o,c) or l>min(o,c) or h<l or v<0:
                        raise RuntimeError(f"Invalid OHLCV {path.name} at {t}")
                    rows.append((t,o,h,l,c,v))
    return rows
def load_m1(symbol,start_ms,end_ms):
    months=month_range(start_ms,end_ms); current=months[-1]
    merged=[]; checks=[]
    for month in months:
        if month==current:continue
        name=f"{symbol}-1m-{month}.zip"
        url=f"{BASE}/monthly/klines/{symbol}/1m/{name}"
        p,d=archive_file(url); checks.append({"file":name,"sha256":d})
        merged.extend(parse_kline_zip(p,start_ms,end_ms))
    for day in day_range(start_ms,end_ms):
        if day[:7]!=current:continue
        name=f"{symbol}-1m-{day}.zip"
        url=f"{BASE}/daily/klines/{symbol}/1m/{name}"
        p,d=archive_file(url); checks.append({"file":name,"sha256":d})
        merged.extend(parse_kline_zip(p,start_ms,end_ms))
    merged.sort(key=lambda x:x[0])
    if not merged:raise RuntimeError(f"No 1m data for {symbol}")
    ts=np.fromiter((r[0] for r in merged),dtype=np.int64,count=len(merged))
    if len(ts)>1 and np.any(np.diff(ts)!=MIN):
        i=int(np.flatnonzero(np.diff(ts)!=MIN)[0]); raise RuntimeError(f"{symbol} 1m gap/duplicate at {ts[i]} -> {ts[i+1]}")
    expected=(end_ms-start_ms)//MIN
    if len(ts)!=expected:raise RuntimeError(f"{symbol} expected {expected:,} 1m bars, got {len(ts):,}")
    o=np.fromiter((r[1] for r in merged),dtype=np.float64,count=len(merged))
    h=np.fromiter((r[2] for r in merged),dtype=np.float64,count=len(merged))
    l=np.fromiter((r[3] for r in merged),dtype=np.float64,count=len(merged))
    c=np.fromiter((r[4] for r in merged),dtype=np.float64,count=len(merged))
    del merged
    if len(ts)%60:raise RuntimeError("M1 data does not align to whole H1 bars")
    return (ts,o,h,l,c),checks
def load_funding(symbol,start_ms,end_ms):
    events={}
    months=month_range(start_ms,end_ms)
    end_dt=datetime.fromtimestamp(end_ms/1000,timezone.utc)
    final_month_is_partial=(end_dt.day>1 or end_dt.hour>0 or end_dt.minute>0 or end_dt.second>0)
    skipped_partial_month=None
    for month in months:
        # Binance publishes funding-rate archives monthly, only after a month closes.
        # Keep the full five-year M1 replay; omit only the unpublished tail-month funding.
        if month==months[-1] and final_month_is_partial:
            skipped_partial_month=month
            continue
        name=f"{symbol}-fundingRate-{month}.zip"
        url=f"{BASE}/monthly/fundingRate/{symbol}/{name}"
        p,_=archive_file(url)
        with zipfile.ZipFile(p) as z:
            for name2 in z.namelist():
                if not name2.lower().endswith(".csv"):continue
                with z.open(name2) as raw:
                    for row in csv.reader(io.TextIOWrapper(raw,encoding="utf-8",newline="")):
                        if len(row)<3:continue
                        try:
                            if row[0].strip().upper()==symbol and len(row)>=4:
                                t=int(float(row[1])); rate=float(row[3])
                            else:
                                t=int(float(row[0])); rate=float(row[2])
                        except (ValueError,TypeError):continue
                        if start_ms<=t<end_ms and math.isfinite(rate):events[t]=rate
    ordered=sorted(events.items())
    expected=(end_ms-start_ms)//DAY*3
    coverage=100*len(ordered)/expected if expected else 0
    if coverage<95:raise RuntimeError(f"{symbol} official funding archive coverage only {coverage:.1f}% ({len(ordered)} records; rough expected {expected})")
    times=np.array([x[0] for x in ordered],dtype=np.int64)
    prefix=np.zeros(len(ordered)+1,dtype=np.float64)
    for i,x in enumerate(ordered):prefix[i+1]=prefix[i]+x[1]
    return times,prefix,{"records":len(ordered),"rough_coverage_pct":round(coverage,2),
        "source":"Binance USD-M official monthly fundingRate archives",
        "unpublished_partial_month_omitted":skipped_partial_month}
def wilder(values,n):
    out=np.full(len(values),np.nan,dtype=np.float64); acc=None; count=0
    for i,x in enumerate(values):
        if not math.isfinite(float(x)):continue
        if acc is None:acc=float(x);count=1
        else:acc=(acc*(n-1)+float(x))/n;count+=1
        if count>=n:out[i]=acc
    return out
def h1_indicators(m1):
    ts,o,h,l,c=m1; n=len(ts)//60
    ho=o[::60].copy(); hh=h.reshape(n,60).max(axis=1); hl=l.reshape(n,60).min(axis=1); hc=c[59::60].copy()
    tr=np.full(n,np.nan); pdm=np.full(n,np.nan); mdm=np.full(n,np.nan); gain=np.full(n,np.nan); loss=np.full(n,np.nan)
    tr[1:]=np.maximum.reduce([hh[1:]-hl[1:],np.abs(hh[1:]-hc[:-1]),np.abs(hl[1:]-hc[:-1])])
    up=hh[1:]-hh[:-1]; down=hl[:-1]-hl[1:]
    pdm[1:]=np.where((up>down)&(up>0),up,0); mdm[1:]=np.where((down>up)&(down>0),down,0)
    delta=hc[1:]-hc[:-1]; gain[1:]=np.maximum(delta,0); loss[1:]=np.maximum(-delta,0)
    atrs={p:wilder(tr,p) for p in ATR_PERIODS}
    atr14=wilder(tr,14); ps=wilder(pdm,14); ms=wilder(mdm,14)
    dx=np.full(n,np.nan)
    valid=np.isfinite(atr14)&np.isfinite(ps)&np.isfinite(ms)&(atr14>0)
    pdi=np.zeros(n); mdi=np.zeros(n); pdi[valid]=100*ps[valid]/atr14[valid]; mdi[valid]=100*ms[valid]/atr14[valid]
    den=pdi+mdi; good=valid&(den>0); dx[good]=100*np.abs(pdi[good]-mdi[good])/den[good]
    adx=wilder(dx,14); ag=wilder(gain,14); al=wilder(loss,14)
    return {"ts":ts[::60],"open":ho,"high":hh,"low":hl,"close":hc,"atr":atrs,"atr14":atr14,"plus":ps,"minus":ms,"adx":adx,"avg_gain":ag,"avg_loss":al}
def partial_ind(ind,hour_i,high,low,close):
    prev=hour_i-1
    if prev<1:return None
    prev_close=ind["close"][prev]; prev_high=ind["high"][prev]; prev_low=ind["low"][prev]
    tr=max(high-low,abs(high-prev_close),abs(low-prev_close))
    up=high-prev_high; down=prev_low-low
    plus=up if up>down and up>0 else 0.0
    minus=down if down>up and down>0 else 0.0
    delta=close-prev_close
    def upd(arr):
        x=arr[prev]
        return None if not np.isfinite(x) else (float(x)*13+0)/14
    a14=ind["atr14"][prev]; p14=ind["plus"][prev]; m14=ind["minus"][prev]
    ag=ind["avg_gain"][prev]; al=ind["avg_loss"][prev]; old_adx=ind["adx"][prev]
    if not all(np.isfinite(x) for x in (a14,p14,m14,ag,al,old_adx)):return None
    a=(a14*13+tr)/14; p=(p14*13+plus)/14; m=(m14*13+minus)/14
    den=100*p/a+100*m/a
    if den<=0:return None
    dx=100*abs(100*p/a-100*m/a)/den
    adx=(old_adx*13+dx)/14
    avg_g=(ag*13+max(delta,0))/14; avg_l=(al*13+max(-delta,0))/14
    rsi=100 if avg_l==0 else 100-100/(1+avg_g/avg_l)
    atr_prior={period:float(ind["atr"][period][prev]) if np.isfinite(ind["atr"][period][prev]) else None for period in ATR_PERIODS}
    return {"adx":adx,"rsi":rsi,"atr":atr_prior}
def impulse_ok(cfg,side,span,vals):
    atr=vals["atr"][cfg["atrPeriod"]]
    if atr is None or atr<=0 or vals["adx"]<cfg["adxMin"] or vals["adx"]>cfg["adxMax"]:return False
    if span<cfg["impulseAtr"]*atr:return False
    rsi=vals["rsi"]
    if cfg["rsiMode"]=="exact":
        return (50<=rsi<=70) if side==1 else (30<=rsi<=50)
    if cfg["rsiMode"]=="loose":
        return (50<=rsi<=75) if side==1 else (25<=rsi<=50)
    if cfg["rsiMode"]!="none":raise RuntimeError("Unknown RSI mode "+cfg["rsiMode"])
    return True
def first_entry(setup,m1,expiry):
    ts,o,h,l,c=m1
    start=np.searchsorted(ts,setup["detectedAt"],side="left")
    end=np.searchsorted(ts,expiry,side="left")
    if start>=end:return None
    sl=setup["stop"]; level=setup["level"]; side=setup["side"]
    lows=l[start:end]; highs=h[start:end]
    stopmask=(lows<=sl) if side==1 else (highs>=sl)
    entermask=(lows<=level) if side==1 else (highs>=level)
    si=np.flatnonzero(stopmask); ei=np.flatnonzero(entermask)
    first_stop=start+int(si[0]) if len(si) else None
    first_entry=start+int(ei[0]) if len(ei) else None
    if first_entry is None or (first_stop is not None and first_stop<=first_entry):return None
    fill_i=first_entry+1
    if fill_i>=len(ts):return None
    return {**setup,"triggerIdx":first_entry,"triggerMinute":int(ts[first_entry]),"alertTime":int(ts[first_entry]+MIN),"fillIdx":fill_i,"entryTime":int(ts[fill_i])}
def funding_sum(times,prefix,start,end):
    a=bisect.bisect_left(times,start); b=bisect.bisect_right(times,end)
    return float(prefix[b]-prefix[a])
def simulate(candidate,m1,fund,slip,end_ms):
    ts,o,h,l,c=m1; side=candidate["side"]; i=candidate["fillIdx"]
    if ts[i]>=end_ms:return None
    fill=float(o[i])*(1+side*slip/10000)
    stop=float(candidate["stop"])
    if (side==1 and fill<=stop) or (side==-1 and fill>=stop):return None
    risk=abs(fill-stop); target=fill+side*RR*risk
    last=min(len(ts)-1,i+MAX_HOLD-1)
    last=min(last,np.searchsorted(ts,end_ms,side="left")-1)
    if last<i:return None
    exit_raw=None; reason=None; exit_i=None
    for j in range(i,last+1):
        stop_hit=(l[j]<=stop) if side==1 else (h[j]>=stop)
        target_hit=(h[j]>=target) if side==1 else (l[j]<=target)
        if stop_hit:
            gap=(o[j]<stop) if side==1 else (o[j]>stop)
            exit_raw=float(o[j] if gap else stop); reason="STOP"; exit_i=j; break
        if target_hit:
            exit_raw=target; reason="TARGET"; exit_i=j; break
    if exit_i is None:
        # Do not manufacture a time exit at a truncated train/test or data boundary.
        if i+MAX_HOLD-1>last:return None
        exit_i=last; exit_raw=float(c[last]); reason="TIME"
    exit_time=int(ts[exit_i]+MIN-1)
    exit_px=exit_raw*(1-side*slip/10000)
    gross=side*(exit_px-fill)/fill*10000
    funding=funding_sum(fund[0],fund[1],int(ts[i]),exit_time)*side*10000
    fees=2*FEE_BPS
    net=gross-fees-funding
    return {"symbol":candidate["symbol"],"configId":candidate["configId"],"rank":candidate["rank"],
        "impulseOpenTime":candidate["impulseOpenTime"],"detectedAt":candidate["detectedAt"],
        "triggerMinute":candidate["triggerMinute"],"alertTime":candidate["alertTime"],"entryTime":int(ts[i]),
        "exitTime":exit_time,"side":"LONG" if side==1 else "SHORT","entry":fill,"exit":exit_px,
        "stop":stop,"target":target,"rr":RR,"reason":reason,"grossBps":gross,"feesBps":fees,
        "fundingBps":funding,"netBps":net,"netR":net/(risk/fill*10000),"holdMinutes":exit_i-i+1,"slippageBpsSide":slip}
def metrics(rows):
    if not rows:return {"trades":0,"wins":0,"losses":0,"winRatePct":None,"profitFactor":None,"netBps":0.0,"avgNetBps":None}
    wins=[x["netBps"] for x in rows if x["netBps"]>0]; losses=[x["netBps"] for x in rows if x["netBps"]<=0]
    gl=-sum(losses); gp=sum(wins)
    return {"trades":len(rows),"wins":len(wins),"losses":len(losses),"winRatePct":100*len(wins)/len(rows),
        "profitFactor":gp/gl if gl>0 else (None if gp==0 else 999.0),"netBps":sum(x["netBps"] for x in rows),
        "avgNetBps":sum(x["netBps"] for x in rows)/len(rows),
        "stopPct":100*sum(x["reason"]=="STOP" for x in rows)/len(rows),
        "targetPct":100*sum(x["reason"]=="TARGET" for x in rows)/len(rows),
        "timePct":100*sum(x["reason"]=="TIME" for x in rows)/len(rows)}
def select_alerts(candidates,pf_by_config):
    groups=defaultdict(list)
    for c in candidates:groups[(c["symbol"],c["impulseOpenTime"])].append(c)
    selected=[]; skipped=[]
    for key,items in groups.items():
        earliest=min(x["triggerMinute"] for x in items)
        same=[x for x in items if x["triggerMinute"]==earliest]
        if len(same)==1:selected.append(same[0]);continue
        if any(x["configId"] not in pf_by_config for x in same):
            skipped.append({"symbol":key[0],"impulseOpenTime":key[1],"triggerMinute":earliest,"reason":"MISSING_VALIDATED_PF","configs":[x["configId"] for x in same]})
            continue
        selected.append(sorted(same,key=lambda x:(-pf_by_config[x["configId"]]["profitFactor"],-pf_by_config[x["configId"]]["trades"],x["rank"]))[0])
    return selected,skipped
def write_csv(path,rows):
    if not rows:
        path.write_text("no_rows\n");return
    with path.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
CONFIG_CSV_SHA256=None
def load_configs():
    global CONFIG_CSV_SHA256
    csv_path=ROOT/"config/model3_asset_independent_top100_rr2.csv"
    csv_bytes=csv_path.read_bytes()
    CONFIG_CSV_SHA256=hashlib.sha256(csv_bytes).hexdigest()
    with csv_path.open(newline="",encoding="utf-8") as f:
        source_rows=list(csv.DictReader(f))
    if len(source_rows)!=100:raise RuntimeError(f"Approved source CSV must have 100 rows; got {len(source_rows)}")
    expected=[]
    for row in source_rows:
        expected.append({
            "id":f"IR-T{int(row['rank']):03d}","rank":int(row["rank"]),
            "timeframe":row["timeframe"],"atrPeriod":int(row["atr_period"]),
            "impulseAtr":float(row["impulse_atr"]),"adxMin":float(row["adx_min"]),
            "adxMax":float(row["adx_max"]),"rsiMode":row["rsi_mode"],
            "retracement":float(row["retracement"]),"rr":float(row["rr"]),
            "pendingBars":int(row["pending_bars"])
        })
    js=(ROOT/"config/strategies.js").read_text()
    m=__import__("re").search(r"export const STRATEGIES = (\[[\s\S]*?\]);",js)
    if not m:raise RuntimeError("Cannot parse live Top-100 configuration array")
    configs=json.loads(m.group(1))
    if configs!=[dict(x,enabled=True) for x in expected]:
        # enabled is the only live-only field; all strategy parameters and rank IDs must match CSV exactly.
        actual=[{k:v for k,v in x.items() if k!="enabled"} for x in configs]
        if actual!=expected:raise RuntimeError("Live strategy parameters do not exactly match the approved Top-100 CSV")
    if len(configs)!=100 or [x["rank"] for x in configs]!=list(range(1,101)):
        raise RuntimeError("Expected exact Top-100 ranks 1..100")
    if any(x["rr"]!=2 or x["timeframe"]!="1h" for x in configs):
        raise RuntimeError("Top-100 RR/timeframe mismatch")
    return configs
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--start",default="2021-11-19")
    ap.add_argument("--end",default="2026-11-19",help="exclusive UTC date")
    args=ap.parse_args()
    start_ms,end_ms=utc_ms(args.start),utc_ms(args.end)
    days=(end_ms-start_ms)//DAY
    if days<1750 or days>1900:raise RuntimeError(f"Expected five-year window, got {days} days")
    split_ms=((start_ms+int((end_ms-start_ms)*TRAIN_FRACTION))//DAY)*DAY
    configs=load_configs(); OUT.mkdir(parents=True,exist_ok=True)
    print(f"TOP-100 IMPULSE RETRACER | {args.start} to {args.end} UTC | BTCUSDT + ETHUSDT",flush=True)
    summaries={}; all_candidates=[]; symbol_data={}
    for symbol in SYMBOLS:
        print(f"Downloading and validating {symbol} M1 archives...",flush=True)
        m1,checks=load_m1(symbol,start_ms-60*DAY,end_ms)
        ind=h1_indicators(m1)
        ts,o,h,l,c=m1; candidates=[]; setups=0
        first_h=np.searchsorted(ind["ts"],start_ms,side="left")
        for hi in range(max(2,first_h),len(ind["ts"])):
            hour=int(ind["ts"][hi])
            if hour>=end_ms:break
            base_i=hi*60
            seen=set()
            for off in range(60):
                mi=base_i+off
                if mi>=len(ts) or ts[mi]>=end_ms:break
                if off==0:
                    ph=max(float(ind["open"][hi]),float(o[mi])); pl=min(float(ind["open"][hi]),float(o[mi])); pc=float(o[mi])
                else:
                    ph=max(float(ind["open"][hi]),float(np.max(h[base_i:mi])),float(o[mi]))
                    pl=min(float(ind["open"][hi]),float(np.min(l[base_i:mi])),float(o[mi]))
                    pc=float(o[mi])
                side=1 if pc>float(ind["open"][hi]) else (-1 if pc<float(ind["open"][hi]) else 0)
                if not side:continue
                vals=partial_ind(ind,hi,ph,pl,pc)
                if vals is None:continue
                span=ph-pl
                for cfg in configs:
                    if cfg["rank"] in seen:continue
                    if not impulse_ok(cfg,side,span,vals):continue
                    seen.add(cfg["rank"]);setups+=1
                    level=ph-cfg["retracement"]*span if side==1 else pl+cfg["retracement"]*span
                    stop=pl if side==1 else ph
                    setup={"symbol":symbol,"configId":cfg["id"],"rank":cfg["rank"],"side":side,
                        "impulseOpenTime":hour,"detectedAt":int(ts[mi]),"impulseHigh":ph,"impulseLow":pl,
                        "impulseRange":span,"level":level,"stop":stop,"pendingBars":cfg["pendingBars"]}
                    expiry=hour+(cfg["pendingBars"]+1)*HOUR
                    hit=first_entry(setup,m1,expiry)
                    if hit:candidates.append(hit)
            if hi%5000==0:print(f"{symbol}: scanned {hi-first_h:,} H1 bars; setups={setups:,}; entry candidates={len(candidates):,}",flush=True)
        print(f"{symbol}: H1={len(ind['ts']):,}; M1={len(ts):,}; setups={setups:,}; candidates={len(candidates):,}",flush=True)
        fund=load_funding(symbol,start_ms,end_ms)
        all_candidates.extend(candidates)
        symbol_data[symbol]={"m1":m1,"fund":fund,"checks":checks,"candidates":candidates,"ind":ind}
        summaries[symbol]={"m1Bars":len(ts),"h1Bars":len(ind["ts"]),"setups":setups,"entryCandidates":len(candidates),"funding":fund[2]}
    # Simulate independent config streams to build PF estimates and validation diagnostics.
    train_rows=defaultdict(list); oos_rows=defaultdict(list); full_rows=defaultdict(list)
    candidate_outcomes={}
    for symbol in SYMBOLS:
        data=symbol_data[symbol]; m1=data["m1"]; fund=data["fund"]
        for i,cand in enumerate(data["candidates"]):
            full=simulate(cand,m1,fund,2.0,end_ms)
            if full:full_rows[cand["configId"]].append(full)
            if cand["detectedAt"]<split_ms:
                train=simulate(cand,m1,fund,2.0,split_ms)
                if train and train["exitTime"]<split_ms:train_rows[cand["configId"]].append(train)
            else:
                oos=simulate(cand,m1,fund,2.0,end_ms)
                if oos:oos_rows[cand["configId"]].append(oos)
            candidate_outcomes[(symbol,cand["configId"],cand["impulseOpenTime"])]=cand
            if i%10000==0 and i:print(f"{symbol}: simulated {i:,}/{len(data['candidates']):,} candidate streams",flush=True)
    train_pf={}
    for cfg in configs:
        rows=train_rows[cfg["id"]]; m=metrics(rows)
        if m["trades"]>=30 and m["profitFactor"] is not None:
            train_pf[cfg["id"]]={"profitFactor":m["profitFactor"],"trades":m["trades"],"validated":True}
    # OOS model stream: first trigger for each impulse; PF competition only for candidates on that exact M1 candle.
    oos_candidates=[c for c in all_candidates if c["detectedAt"]>=split_ms]
    selected_oos,skipped_oos=select_alerts(oos_candidates,train_pf)
    # Full-period retrospective stream is diagnostic only; it uses full-period PF to rank simultaneous candidates.
    full_pf={}
    for cfg in configs:
        m=metrics(full_rows[cfg["id"]])
        if m["trades"]>=30 and m["profitFactor"] is not None:
            full_pf[cfg["id"]]={"profitFactor":m["profitFactor"],"trades":m["trades"],"validated":True}
    selected_full,skipped_full=select_alerts(all_candidates,full_pf)
    model_oos={2.0:[],7.0:[]}; model_full={2.0:[],7.0:[]}
    for slip in SLIPPAGE:
        for cand in selected_oos:
            row=simulate(cand,symbol_data[cand["symbol"]]["m1"],symbol_data[cand["symbol"]]["fund"],slip,end_ms)
            if row:model_oos[slip].append(row)
        for cand in selected_full:
            row=simulate(cand,symbol_data[cand["symbol"]]["m1"],symbol_data[cand["symbol"]]["fund"],slip,end_ms)
            if row:model_full[slip].append(row)
    # Per-year OOS stats, by exit year.
    yearly=[]
    for year in range(datetime.fromtimestamp(split_ms/1000,timezone.utc).year,datetime.fromtimestamp((end_ms-1)/1000,timezone.utc).year+1):
        rows=[x for x in model_oos[2.0] if datetime.fromtimestamp(x["exitTime"]/1000,timezone.utc).year==year]
        yearly.append({"year":year,**metrics(rows)})
    per_config=[]
    for cfg in configs:
        tr=metrics(train_rows[cfg["id"]]); oo=metrics(oos_rows[cfg["id"]]); fu=metrics(full_rows[cfg["id"]])
        validated=tr["trades"]>=30 and tr["profitFactor"] is not None
        per_config.append({"configId":cfg["id"],"rank":cfg["rank"],"pendingBars":cfg["pendingBars"],"rsiMode":cfg["rsiMode"],"adxMin":cfg["adxMin"],"adxMax":cfg["adxMax"],"impulseAtr":cfg["impulseAtr"],"retracement":cfg["retracement"],
            "train":tr,"oos":oo,"fullFiveYear":fu,"livePfValidated":validated})
    registry={}
    for row in per_config:
        if row["train"]["trades"]>=30 and row["train"]["profitFactor"] is not None:
            registry[row["configId"]]={"profitFactor":row["train"]["profitFactor"],"trades":row["train"]["trades"],"validated":bool(row["livePfValidated"])}
    js="// Generated by the reproducible five-year Top-100 backtest. Do not edit by hand.\nexport const PF_RANKINGS = "+json.dumps(registry,indent=2)+";\n"
    (OUT/"pf-rankings.js").write_text(js)
    for slip in SLIPPAGE:
        write_csv(OUT/f"model_oos_trades_{int(slip)}bps.csv",model_oos[slip])
        write_csv(OUT/f"model_full_retro_trades_{int(slip)}bps.csv",model_full[slip])
    write_csv(OUT/"per_config_metrics.csv",per_config)
    write_csv(OUT/"oos_yearly_metrics.csv",yearly)
    write_csv(OUT/"oos_skipped_impulses.csv",skipped_oos)
    write_csv(OUT/"full_skipped_impulses.csv",skipped_full)
    summary={"status":"COMPLETED","periodUtc":{"start":args.start,"endExclusive":args.end},"symbols":list(SYMBOLS),"configurations":len(configs),"approvedCsvSha256":CONFIG_CSV_SHA256,
        "model":"One Top-100 model; first M1 entry trigger per symbol/hour impulse; PF comparison only among configurations triggering on the same M1 candle.",
        "execution":"H1 forming candle evaluated every minute using completed M1 history through prior minute; M1 retracement touch triggers alert at candle close; entry filled at next M1 open.",
        "indicators":"Wilder ATR prior completed H1; Wilder ADX(14) and RSI(14) recalculated from forming H1 snapshot. exact RSI: long 50-70/short 30-50; loose: long 50-75/short 25-50.",
        "pendingBars":"Valid from first detection minute until impulse H1 open + (pending_bars+1) hours; 3 means the impulse hour plus the next 3 hourly bars, expiry at the following H1 open.",
        "exits":"Structural opposite impulse extreme (1x); target 2R; stop-first if both barriers hit in one M1 candle; adverse gap stop fills at candle open; max hold 24h.",
        "costs":{"feeBpsPerSide":FEE_BPS,"slippageBpsPerSideScenarios":list(SLIPPAGE),"funding":"Official Binance USD-M monthly fundingRate archives; unpublished incomplete final month omitted and coverage disclosed."},
        "trainSplitUtc":datetime.fromtimestamp(split_ms/1000,timezone.utc).isoformat(),
        "data":summaries,
        "pfRegistryValidatedConfigs":sum(1 for x in registry.values() if x["validated"]),
        "pfRegistryTotalConfigs":len(registry),
        "oosModel2bps":metrics(model_oos[2.0]),"oosModel7bps":metrics(model_oos[7.0]),
        "fullFiveYearRetrospective2bps":metrics(model_full[2.0]),"fullFiveYearRetrospective7bps":metrics(model_full[7.0]),
        "oosUniqueAlertsSelected":len(selected_oos),"oosCandidates":len(oos_candidates),"oosSkippedImpulses":len(skipped_oos),
        "fullUniqueAlertsSelected":len(selected_full),"fullCandidates":len(all_candidates),"fullSkippedImpulses":len(skipped_full),
        "oosYearly":yearly,"archiveChecksums":{s:symbol_data[s]["checks"] for s in SYMBOLS},
        "limitations":"The full-five-year retrospective PF ranking uses all five years and is descriptive/in-sample. The 60/40 OOS stream uses only training-period per-config PF for same-minute selection. OOS metrics are the primary validation result."}
    (OUT/"summary.json").write_text(json.dumps(summary,indent=2,allow_nan=False)+"\n")
    print(json.dumps(summary,indent=2),flush=True)
if __name__=="__main__":main()
