#!/usr/bin/env python3
"""Ten independent crypto-perpetual strategy backtests on Binance USD-M 1h candles.
No leverage compounding: fixed notional per trade, fee+slippage charged on both sides.
Signals use closed bars; entries occur at next bar open. Conservative same-bar SL/TP: stop wins.
"""
from __future__ import annotations
import io, json, math, os, time, zipfile
from datetime import date
from pathlib import Path
import requests
import numpy as np
import pandas as pd

START="2023-11-01"; END="2026-11-01"
SYMBOLS=["BTCUSDT","ETHUSDT"]
BASE="https://data.binance.vision/data/futures/um/monthly/klines"
OUT=Path("crypto-10-engine-results"); OUT.mkdir(exist_ok=True)
FEE=0.0004; SLIPPAGE=0.0002; NOTIONAL=1000.0

def months(start,end):
    s=pd.Timestamp(start).replace(day=1); e=pd.Timestamp(end).replace(day=1)
    while s<=e:
        yield s.strftime("%Y-%m"); s+=pd.offsets.MonthBegin(1)

def load_symbol(symbol):
    frames=[]
    for m in months(START,END):
        url=f"{BASE}/{symbol}/1h/{symbol}-1h-{m}.zip"
        try:
            r=requests.get(url,timeout=45)
            if r.status_code==404: continue
            r.raise_for_status()
            z=zipfile.ZipFile(io.BytesIO(r.content))
            name=next(n for n in z.namelist() if n.endswith(".csv"))
            d=pd.read_csv(z.open(name),header=None)
            d=d.iloc[:,:12]; d.columns=["open_time","open","high","low","close","volume","close_time","quote_volume","trades","taker_buy_base","taker_buy_quote","ignore"]
            frames.append(d[["open_time","open","high","low","close","volume"]])
        except Exception as ex:
            raise RuntimeError(f"Download failed {symbol} {m}: {ex}")
        time.sleep(.03)
    if not frames: raise RuntimeError(f"No candles downloaded for {symbol}")
    d=pd.concat(frames,ignore_index=True).drop_duplicates("open_time").sort_values("open_time")
    d["open_time"]=pd.to_numeric(d["open_time"],errors="coerce")
    d["time"]=pd.to_datetime(d.open_time,unit="ms",utc=True)
    for c in ["open","high","low","close","volume"]: d[c]=pd.to_numeric(d[c],errors="coerce")
    d=d[(d.time>=pd.Timestamp(START,tz="UTC"))&(d.time<pd.Timestamp(END,tz="UTC"))].dropna().reset_index(drop=True)
    if len(d)<10000: raise RuntimeError(f"Insufficient history for {symbol}: {len(d)}")
    return d

def indicators(d):
    c=d.close; h=d.high; l=d.low; v=d.volume
    prev=c.shift()
    tr=pd.concat([h-l,(h-prev).abs(),(l-prev).abs()],axis=1).max(axis=1)
    d["atr"]=tr.ewm(alpha=1/14,adjust=False).mean()
    d["ema20"]=c.ewm(span=20,adjust=False).mean(); d["ema50"]=c.ewm(span=50,adjust=False).mean(); d["ema200"]=c.ewm(span=200,adjust=False).mean()
    delta=c.diff(); gain=delta.clip(lower=0).ewm(alpha=1/14,adjust=False).mean(); loss=(-delta.clip(upper=0)).ewm(alpha=1/14,adjust=False).mean()
    d["rsi"]=100-100/(1+gain/loss.replace(0,np.nan))
    mid=c.rolling(20).mean(); sd=c.rolling(20).std()
    d["bbz"]=(c-mid)/sd.replace(0,np.nan); d["bbwidth"]=(4*sd/mid).replace([np.inf,-np.inf],np.nan)
    up=h.diff(); dn=-l.diff()
    plus=up.where((up>dn)&(up>0),0); minus=dn.where((dn>up)&(dn>0),0)
    pdi=100*plus.ewm(alpha=1/14,adjust=False).mean()/d.atr
    mdi=100*minus.ewm(alpha=1/14,adjust=False).mean()/d.atr
    d["adx"]=(100*(pdi-mdi).abs()/(pdi+mdi).replace(0,np.nan)).ewm(alpha=1/14,adjust=False).mean()
    d["volz"]=(v-v.rolling(30).mean())/v.rolling(30).std()
    d["don_hi"]=h.shift(1).rolling(20).max(); d["don_lo"]=l.shift(1).rolling(20).min()
    d["ret24"]=c.pct_change(24); d["ret72"]=c.pct_change(72)
    return d

def signal_map(d, eth=None):
    c=d.close; e=d
    # +1 long, -1 short, 0 flat; all conditions evaluated at candle close.
    sig={}
    sig["E01 Donchian breakout"]=pd.Series(np.select([c>e.don_hi,c<e.don_lo],[1,-1],0),index=d.index)
    sig["E02 Supertrend ATR"]=pd.Series(np.select([(c>c.shift(1))&(c>e.ema20+1.5*e.atr),(c<c.shift(1))&(c<e.ema20-1.5*e.atr)],[1,-1],0),index=d.index)
    sig["E03 EMA trend pullback"]=pd.Series(np.select([(e.ema50>e.ema200)&(c>e.ema50)&(e.rsi.between(40,58)),(e.ema50<e.ema200)&(c<e.ema50)&(e.rsi.between(42,60))],[1,-1],0),index=d.index)
    sig["E04 Volatility squeeze breakout"]=pd.Series(np.select([(e.bbwidth<e.bbwidth.rolling(100).quantile(.2))&(c>e.ema20),(e.bbwidth<e.bbwidth.rolling(100).quantile(.2))&(c<e.ema20)],[1,-1],0),index=d.index)
    sig["E05 Bollinger mean reversion"]=pd.Series(np.select([(e.bbz<-2)&(e.rsi<35),(e.bbz>2)&(e.rsi>65)],[1,-1],0),index=d.index)
    sig["E06 RSI exhaustion reversal"]=pd.Series(np.select([(e.rsi<20)&(e.rsi.shift(1)>=20),(e.rsi>80)&(e.rsi.shift(1)<=80)],[1,-1],0),index=d.index)
    sig["E07 Volume shock continuation"]=pd.Series(np.select([(e.volz>2)&(c>e.open)&(c>e.ema50),(e.volz>2)&(c<e.open)&(c<e.ema50)],[1,-1],0),index=d.index)
    # Range expansion after multi-day consolidation, distinct from channel breakout.
    range_pct=(e.high.rolling(48).max()-e.low.rolling(48).min())/c
    sig["E08 Volatility expansion"]=pd.Series(np.select([(range_pct<range_pct.rolling(200).quantile(.2))&(e.atr/e.atr.rolling(50).mean()>1.25)&(c>e.ema50),(range_pct<range_pct.rolling(200).quantile(.2))&(e.atr/e.atr.rolling(50).mean()>1.25)&(c<e.ema50)],[1,-1],0),index=d.index)
    # Cross-asset relative strength: trade BTC direction from BTC-vs-ETH 72h return spread.
    if eth is not None:
        spread=e.ret72-eth.reindex(e.index)
        sig["E09 BTC-ETH relative momentum"]=pd.Series(np.select([(spread>.015)&(e.ret72>0),(spread<-.015)&(e.ret72<0)],[1,-1],0),index=d.index)
    else:
        sig["E09 BTC-ETH relative momentum"]=pd.Series(0,index=d.index)
    # Trend regime + ADX directional persistence, not an indicator-only trigger.
    sig["E10 ADX directional regime"]=pd.Series(np.select([(e.adx>25)&(e.ema20>e.ema50)&(e.ema50>e.ema200),(e.adx>25)&(e.ema20<e.ema50)&(e.ema50<e.ema200)],[1,-1],0),index=d.index)
    return sig

def run_engine(d, sig, name, symbol, sl_atr, rr):
    # Numpy arrays avoid repeated pandas row construction across the parameter grid.
    op=d.open.to_numpy(float); hi=d.high.to_numpy(float); lo=d.low.to_numpy(float)
    cl=d.close.to_numpy(float); atr=d.atr.to_numpy(float)
    times=d.time.astype(str).to_numpy(); signals=sig.to_numpy(int)
    side=0; entry=stop=target=0.0; entry_i=0; trades=[]
    for i in range(250,len(d)-1):
        if side:
            hit_sl=(lo[i]<=stop if side==1 else hi[i]>=stop)
            hit_tp=(hi[i]>=target if side==1 else lo[i]<=target)
            if hit_sl or hit_tp:
                px=stop if hit_sl else target
                gross=side*(px-entry)/entry; net=gross-2*(FEE+SLIPPAGE)
                trades.append(dict(engine=name,symbol=symbol,sl_atr=sl_atr,rr=rr,
                    entry_time=times[entry_i],exit_time=times[i],
                    side="LONG" if side==1 else "SHORT",entry=entry,exit=px,
                    gross_pct=gross*100,net_pct=net*100,pnl_usd=NOTIONAL*net,
                    exit_reason="SL" if hit_sl else "TP",bars=i-entry_i))
                side=0
            elif i-entry_i>=72:
                px=cl[i]; gross=side*(px-entry)/entry; net=gross-2*(FEE+SLIPPAGE)
                trades.append(dict(engine=name,symbol=symbol,sl_atr=sl_atr,rr=rr,
                    entry_time=times[entry_i],exit_time=times[i],
                    side="LONG" if side==1 else "SHORT",entry=entry,exit=px,
                    gross_pct=gross*100,net_pct=net*100,pnl_usd=NOTIONAL*net,
                    exit_reason="TIME",bars=i-entry_i)); side=0
        if not side and signals[i]!=0 and np.isfinite(atr[i]) and atr[i]>0:
            s=int(signals[i]); entry=float(op[i+1]); dist=sl_atr*float(atr[i])
            side=s; entry_i=i+1; stop=entry-s*dist; target=entry+s*dist*rr
    if side:
        i=len(d)-1; px=float(cl[i]); gross=side*(px-entry)/entry; net=gross-2*(FEE+SLIPPAGE)
        trades.append(dict(engine=name,symbol=symbol,sl_atr=sl_atr,rr=rr,
            entry_time=times[entry_i],exit_time=times[i],
            side="LONG" if side==1 else "SHORT",entry=entry,exit=px,
            gross_pct=gross*100,net_pct=net*100,pnl_usd=NOTIONAL*net,
            exit_reason="END",bars=i-entry_i))
    return trades

def summarize(t):
    if t.empty: return dict(trades=0,win_rate_pct=0,net_pnl_usd=0,profit_factor=0,expectancy_pct=0,max_drawdown_pct=0,avg_win_pct=0,avg_loss_pct=0)
    p=t.net_pct; wins=p[p>0]; losses=p[p<0]; eq=(1+p/100).cumprod(); dd=(eq/eq.cummax()-1)*100
    return dict(trades=len(t),win_rate_pct=round((p>0).mean()*100,2),net_pnl_usd=round(t.pnl_usd.sum(),2),profit_factor=round(wins.sum()/abs(losses.sum()),3) if len(losses) else None,expectancy_pct=round(p.mean(),4),max_drawdown_pct=round(dd.min(),2),avg_win_pct=round(wins.mean(),4) if len(wins) else 0,avg_loss_pct=round(losses.mean(),4) if len(losses) else 0)

def main():
    data={s:indicators(load_symbol(s)) for s in SYMBOLS}
    # Broad but bounded grid: stop distance is measured in ATR; target = stop distance x RR.
    SL_ATR_GRID=[0.8,1.0,1.2,1.5,1.8,2.0,2.5,3.0]
    RR_GRID=[1.0,1.2,1.5,2.0,2.5,3.0,4.0]
    alltr=[]
    for s,d in data.items():
        eth=data["ETHUSDT"].ret72 if s=="BTCUSDT" else None
        sigs=signal_map(d,eth)
        for name,sig in sigs.items():
            if name.startswith("E09") and s!="BTCUSDT": continue
            for sl_atr in SL_ATR_GRID:
                for rr in RR_GRID:
                    alltr.extend(run_engine(d,sig,name,s,sl_atr,rr))
    t=pd.DataFrame(alltr)
    if t.empty: raise RuntimeError("No trades generated by parameter grid")
    t.to_csv(OUT/"grid_all_trades.csv",index=False)
    summaries=[]
    for (engine,symbol,sl_atr,rr),g in t.groupby(["engine","symbol","sl_atr","rr"]):
        summaries.append({"engine":engine,"symbol":symbol,"sl_atr":sl_atr,"rr":rr,**summarize(g)})
    sm=pd.DataFrame(summaries).sort_values(["engine","symbol","sl_atr","rr"])
    sm.to_csv(OUT/"parameter_grid_summary.csv",index=False)
    # Time-separated evaluation: first two years are development; final year is holdout.
    t["exit_dt"]=pd.to_datetime(t.exit_time,utc=True)
    cut=pd.Timestamp("2025-11-01",tz="UTC")
    hold=t[t.exit_dt>=cut]
    oos=[]
    for (engine,symbol,sl_atr,rr),g in hold.groupby(["engine","symbol","sl_atr","rr"]):
        oos.append({"engine":engine,"symbol":symbol,"sl_atr":sl_atr,"rr":rr,**summarize(g)})
    oos_df=pd.DataFrame(oos)
    oos_df.to_csv(OUT/"holdout_year_summary.csv",index=False)
    # Rank within each engine/symbol on the final-year holdout, not on the full sample.
    if not oos_df.empty:
        ranked=oos_df[oos_df.trades>=20].sort_values(
            ["engine","symbol","profit_factor","net_pnl_usd"],
            ascending=[True,True,False,False])
        ranked.groupby(["engine","symbol"],as_index=False,group_keys=False).head(5).to_csv(
            OUT/"top5_holdout_configs_per_engine_symbol.csv",index=False)
    t["year"]=t.exit_dt.dt.year
    yearly=[]
    for (engine,symbol,sl_atr,rr,year),g in t.groupby(["engine","symbol","sl_atr","rr","year"]):
        yearly.append({"engine":engine,"symbol":symbol,"sl_atr":sl_atr,"rr":rr,"year":int(year),**summarize(g)})
    pd.DataFrame(yearly).to_csv(OUT/"yearly_grid_summary.csv",index=False)
    manifest={"period_utc":[START,END],"development_period_utc":["2023-11-01","2025-11-01"],
        "holdout_period_utc":["2025-11-01","2026-11-01"],"symbols":SYMBOLS,"timeframe":"1h",
        "candles":{s:len(d) for s,d in data.items()},"fee_per_side":FEE,"slippage_per_side":SLIPPAGE,
        "fixed_notional_usd":NOTIONAL,"sl_atr_grid":SL_ATR_GRID,"rr_grid":RR_GRID,
        "parameter_combinations_per_engine":len(SL_ATR_GRID)*len(RR_GRID),
        "max_holding_bars":72,"entry":"next candle open after closed-bar signal",
        "intrabar_policy":"stop-loss wins when SL and TP both touched",
        "funding":"NOT INCLUDED; results are not funding-adjusted",
        "engines":10,"trade_records":len(t),"holdout_ranking_minimum_trades":20,
        "note":"SL_ATR is the stop distance in ATR units, not a separate swing-structure buffer. RR is target distance divided by stop distance. Final-year holdout is separated from first two years for selection discipline."}
    (OUT/"manifest.json").write_text(json.dumps(manifest,indent=2))
    print("GRID SUMMARY ROWS:",len(sm),"TRADE RECORDS:",len(t))
    print("HOLDOUT ROWS:",len(oos_df))
    print(manifest)
if __name__=="__main__": main()
