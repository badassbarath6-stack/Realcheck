#!/usr/bin/env python3
"""Five-year, independent crypto-futures model-family comparison.

Uses completed timeframe candles for signals and Binance M1 for execution.
No model is selected by another model's results. All variants are evaluated
independently with identical fees, slippage, funding, splits and exit rules.
"""
from __future__ import annotations
import argparse, csv, json, math, sys
from collections import defaultdict
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import impulse_retracer_backtest as base

START_MS=base.START_MS
END_MS=base.END_MS
TIMEFRAMES=base.TIMEFRAMES
RR_VALUES=(2.0,3.0,4.0)
SL_BUFFERS=(0.2,0.5,1.0)
LOOKBACK=20
EXPIRY_BARS=3
FEE_BPS=base.FEE_BPS
SLIPPAGE_BPS=(2.0,7.0)
FAMILIES=("liquidity_sweep","structure_break_retest","fvg_retracement",
          "trend_continuation","volatility_expansion","hybrid_confluence")

def ema(values, period):
    out=[float("nan")]*len(values)
    if len(values)<period: return out
    alpha=2.0/(period+1)
    seed=sum(values[:period])/period
    out[period-1]=seed
    for i in range(period,len(values)): out[i]=alpha*values[i]+(1-alpha)*out[i-1]
    return out

def metrics(trades, slip_extra=0.0):
    p=[x["net_bps"]-slip_extra for x in sorted(trades,key=lambda z:z["entry_ms"])]
    wins=[x for x in p if x>0]; losses=[x for x in p if x<=0]
    gp=sum(wins); gl=-sum(losses)
    eq=peak=dd=0.0
    for x in p:
        eq+=x; peak=max(peak,eq); dd=max(dd,peak-eq)
    return {"trades":len(p),"wins":len(wins),"losses":len(losses),
      "win_rate":len(wins)/len(p) if p else 0.0,"pf":gp/gl if gl else (999.0 if gp else 0.0),
      "net_bps":sum(p),"expectancy_bps":sum(p)/len(p) if p else 0.0,
      "max_drawdown_bps":dd}

def funding_index(funding):
    times=[x[0] for x in funding]
    prefix=[0.0]
    for _,rate in funding: prefix.append(prefix[-1]+rate)
    return times,prefix

def funding_paid(index, direction, entry_ms, exit_ms):
    import bisect
    times,prefix=index
    lo=bisect.bisect_right(times,entry_ms)
    hi=bisect.bisect_right(times,exit_ms)
    return direction*(prefix[hi]-prefix[lo])*10000.0

def execute(m1, times, trigger_index, direction, stop, target, expiry_ms, funding_idx, slip):
    entry_i=trigger_index+1
    if entry_i>=len(m1): return None
    entry_ms,entry=m1[entry_i][0],m1[entry_i][1]
    risk=direction*(entry-stop)
    if risk<=0 or not math.isfinite(risk): return None
    # Target is risk-based and fixed from the actual next-M1-open entry.
    target=entry+direction*risk*target
    last=min(len(m1),__import__("bisect").bisect_left(times,expiry_ms))
    exit_px=None; reason=None; exit_ms=None
    for j in range(entry_i,last):
        ts,o,h,l,c=m1[j]
        if direction==1:
            if o<=stop: exit_px=o; reason="stop_gap"
            elif l<=stop: exit_px=stop; reason="stop"
            elif o>=target: exit_px=o; reason="target_gap"
            elif h>=target: exit_px=target; reason="target"
        else:
            if o>=stop: exit_px=o; reason="stop_gap"
            elif h>=stop: exit_px=stop; reason="stop"
            elif o<=target: exit_px=o; reason="target_gap"
            elif l<=target: exit_px=target; reason="target"
        if reason: exit_ms=ts; break
    if reason is None:
        if last<=entry_i: return None
        exit_ms=m1[last-1][0]; exit_px=m1[last-1][4]; reason="expiry"
    gross=direction*(exit_px-entry)/entry*10000.0
    costs=2.0*(FEE_BPS+slip)
    paid=funding_paid(funding_idx,direction,entry_ms,exit_ms)
    return {"entry_ms":entry_ms,"exit_ms":exit_ms,"entry":entry,"exit":exit_px,
      "reason":reason,"gross_bps":gross,"funding_bps":paid,
      "net_bps":gross-costs-paid,"direction":"long" if direction==1 else "short"}

def find_touch(m1, times, start_ms, end_ms, mode, level, tolerance):
    import bisect
    a=bisect.bisect_left(times,start_ms); b=bisect.bisect_left(times,end_ms)
    if mode=="market": return a if a<len(m1) and m1[a][0]<end_ms else None
    for j in range(a,b):
        _,_,hi,lo,_=m1[j]
        if lo<=level+tolerance and hi>=level-tolerance: return j
    return None

def build_setups(m1, tf_bars, tf):
    """Return causal setups; every decision uses only a fully closed TF candle."""
    minutes=TIMEFRAMES[tf]; tf_ms=minutes*60000
    times=[x[0] for x in m1]
    closes=[x[4] for x in tf_bars]
    atr=base.atr_wilder(tf_bars,14)
    e20,e50,e200=ema(closes,20),ema(closes,50),ema(closes,200)
    setups=[]
    for i in range(max(LOOKBACK,200),len(tf_bars)-1):
        t,o,h,l,c,_=tf_bars[i]
        close_ms=t+tf_ms
        if close_ms<START_MS or close_ms>=END_MS: continue
        a=atr[i]
        if not math.isfinite(a) or a<=0: continue
        prior=tf_bars[i-LOOKBACK:i]
        ph=max(x[2] for x in prior); pl=min(x[3] for x in prior)
        bullish=c>o; bearish=c<o
        signals=[]
        # 1) Sweep a prior 20-bar extreme and close back inside it.
        if l<pl and c>pl and bullish:
            signals.append(("liquidity_sweep",1,l,None,"market",None))
        if h>ph and c<ph and bearish:
            signals.append(("liquidity_sweep",-1,h,None,"market",None))
        # 2) Break of structure, followed by a first retest of the broken level.
        if c>ph and bullish:
            signals.append(("structure_break_retest",1,ph,ph,"touch",ph))
        if c<pl and bearish:
            signals.append(("structure_break_retest",-1,pl,pl,"touch",pl))
        # 3) Three-candle fair-value gap; enter at gap midpoint on a later touch.
        if l>tf_bars[i-2][2]:
            zlo,zhi=tf_bars[i-2][2],l
            signals.append(("fvg_retracement",1,zlo,zhi,"zone",(zlo+zhi)/2))
        if h<tf_bars[i-2][3]:
            zlo,zhi=h,tf_bars[i-2][3]
            signals.append(("fvg_retracement",-1,zhi,zlo,"zone",(zlo+zhi)/2))
        # 4) Trend continuation: EMA stack plus pullback/reclaim of EMA20.
        if e20[i]>e50[i]>e200[i] and l<=e20[i] and c>e20[i] and bullish:
            signals.append(("trend_continuation",1,l,None,"market",None))
        if e20[i]<e50[i]<e200[i] and h>=e20[i] and c<e20[i] and bearish:
            signals.append(("trend_continuation",-1,h,None,"market",None))
        # 5) Volatility expansion through the prior range with a strong close.
        rng=h-l
        if rng>=1.5*a and c>ph and c>=l+0.75*rng:
            signals.append(("volatility_expansion",1,ph,ph,"market",None))
        if rng>=1.5*a and c<pl and c<=h-0.75*rng:
            signals.append(("volatility_expansion",-1,pl,pl,"market",None))
        # Hybrid: at least two independent families agree on direction on this bar.
        for direction in (1,-1):
            same=[s for s in signals if s[1]==direction]
            independent={s[0] for s in same}
            if len(independent)>=2:
                # Use the widest supporting structural stop anchor, avoiding a tighter
                # stop than any confirming component; buffer is added later.
                anchors=[s[2] for s in same]
                anchor=min(anchors) if direction==1 else max(anchors)
                signals.append(("hybrid_confluence",direction,anchor,None,"market",None))
        seen=set()
        for family,direction,anchor,zone_hi,mode,level in signals:
            if family in seen: continue
            seen.add(family)
            setups.append({"family":family,"direction":direction,"anchor":anchor,
              "mode":mode,"level":level,"atr":a,"setup_ms":close_ms,
              "event_id":str(t),"expiry_ms":close_ms+EXPIRY_BARS*tf_ms,
              "tf_index":i})
    return setups

def run_pair(symbol,tf,data_dir,out_dir):
    files=base.download_inputs(symbol,data_dir)
    all_rows=base.load_klines(files)
    funding,funding_files,funding_missing=base.download_funding(symbol,data_dir)
    warm=START_MS-35*86400000
    m1=[x for x in all_rows if warm<=x[0]<END_MS]
    if not m1 or m1[0][0]>warm or m1[-1][0]<END_MS-60000:
        raise RuntimeError("M1 input does not cover the required warmup and final minute")
    gaps=[(a[0],b[0]) for a,b in zip(m1,m1[1:]) if b[0]-a[0]!=60000]
    if gaps: raise RuntimeError(f"M1 continuity failure: {len(gaps)} gaps; first={gaps[:5]}")
    tf_bars=[b for b in base.resample_m1(m1,TIMEFRAMES[tf]) if b[5]==TIMEFRAMES[tf]]
    setups=build_setups(m1,tf_bars,tf)
    times=[x[0] for x in m1]
    funding_idx=funding_index(funding)
    trade_rows=[]
    for setup in setups:
        direction=setup["direction"]; a=setup["atr"]
        trig=find_touch(m1,times,setup["setup_ms"],setup["expiry_ms"],
                        setup["mode"],setup["level"],0.20*a)
        if trig is None: continue
        # Stops are anchored to the setup's structure/zone; the ATR buffer grid is shared.
        for buf in SL_BUFFERS:
            stop=setup["anchor"]-buf*a if direction==1 else setup["anchor"]+buf*a
            for rr in RR_VALUES:
                tr=execute(m1,times,trig,direction,stop,rr,setup["expiry_ms"],funding_idx,2.0)
                if tr is None: continue
                tr.update({"symbol":symbol,"timeframe":tf,"family":setup["family"],
                  "event_id":setup["event_id"],"setup_ms":setup["setup_ms"],
                  "trigger_ms":m1[trig][0],"rr":rr,"sl_buffer_atr":buf,
                  "anchor":setup["anchor"],"atr":a})
                trade_rows.append(tr)
    # Independent family/config evaluation; no cross-model winner selection.
    groups=defaultdict(list)
    for tr in trade_rows:
        key=(tr["family"],tr["rr"],tr["sl_buffer_atr"],tr["event_id"])
        groups[key].append(tr)
    dedup=[]
    for key,rows in groups.items():
        dedup.append(min(rows,key=lambda x:(x["trigger_ms"],x["entry_ms"])))
    train_end,val_end=base.split_bounds()
    splits={"train":(START_MS,train_end),"validation":(train_end,val_end),"oos":(val_end,END_MS)}
    cfgs=[(f,rr,b) for f in FAMILIES for rr in RR_VALUES for b in SL_BUFFERS]
    output=[]
    for family,rr,buf in cfgs:
        row={"symbol":symbol,"timeframe":tf,"family":family,"rr":rr,"sl_buffer_atr":buf}
        selected=[x for x in dedup if (x["family"],x["rr"],x["sl_buffer_atr"])==(family,rr,buf)]
        for name,(lo,hi) in splits.items():
            chosen=[x for x in selected if lo<=x["setup_ms"]<hi and x["exit_ms"]<hi]
            for k,v in metrics(chosen).items(): row[f"{name}_{k}"]=v
            for k,v in metrics(chosen,10.0).items():
                if k in ("trades","pf","net_bps","expectancy_bps","max_drawdown_bps"):
                    row[f"{name}_slippage7_{k}"]=v
        # Calendar-year metrics make weak regimes visible instead of hiding them in aggregate PF.
        for year in range(2021,2027):
            lo=max(START_MS,int(datetime(year,1,1,tzinfo=timezone.utc).timestamp()*1000))
            hi=min(END_MS,int(datetime(year+1,1,1,tzinfo=timezone.utc).timestamp()*1000))
            ys=[x for x in selected if lo<=x["setup_ms"]<hi and x["exit_ms"]<hi]
            ym=metrics(ys,10.0)
            row[f"y{year}_trades"]=ym["trades"]; row[f"y{year}_slippage7_pf"]=ym["pf"]
        output.append(row)
    output.sort(key=lambda x:(x["validation_slippage7_pf"],x["validation_trades"]),reverse=True)
    out=Path(out_dir); out.mkdir(parents=True,exist_ok=True)
    base.write_csv(out/f"{symbol}_{tf}_model_metrics.csv",output)
    base.write_csv(out/f"{symbol}_{tf}_model_trades.csv",dedup)
    manifest={"symbol":symbol,"timeframe":tf,"start_utc":"2021-11-20T00:00:00Z",
      "end_utc_exclusive":"2026-11-20T00:00:00Z","families":list(FAMILIES),
      "rr_values":RR_VALUES,"sl_buffers_atr":SL_BUFFERS,"lookback_bars":LOOKBACK,
      "expiry_bars":EXPIRY_BARS,"configuration_count":len(cfgs),"code_commit":__import__("subprocess").check_output(["git","rev-parse","HEAD"],text=True).strip(),
      "m1_rows":len(m1),"m1_gap_count":len(gaps),"timeframe_bars":len(tf_bars),
      "detected_setups":len(setups),"executed_config_trades":len(dedup),
      "fees_bps_per_side":FEE_BPS,"slippage_scenarios_bps_per_side":SLIPPAGE_BPS,
      "funding_rows":len(funding),"funding_missing_archives":funding_missing,
      "source_files":[{"name":p.name,"sha256":base.sha256(p)} for p in files],
      "funding_files":[{"name":p.name,"sha256":base.sha256(p)} for p in funding_files],
      "method":"Completed timeframe-candle signals; M1 next-open or first-zone-touch execution; stop-first; 3-bar setup expiry; independent family/config evaluation",
      "notes":["Initial fixed-rule family comparison, not parameter optimisation.",
       "Structure/FVG retests are executed on first M1 zone touch after the signal candle closes.",
       "All six families use identical RR, stop-buffer, fees, slippage and funding assumptions.",
       "Yearly and chronological split metrics are reported per configuration."]}
    (out/f"{symbol}_{tf}_model_manifest.json").write_text(json.dumps(manifest,indent=2))
    print(json.dumps(manifest,indent=2))

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--symbol",required=True,choices=["BTCUSDT","ETHUSDT"])
    p.add_argument("--timeframe",required=True,choices=["15m","30m","1h","2h","4h"])
    p.add_argument("--data-dir",default="/tmp/binance")
    p.add_argument("--output-dir",default="model-family-output")
    a=p.parse_args()
    run_pair(a.symbol,a.timeframe,a.data_dir,a.output_dir)

if __name__=="__main__": main()
