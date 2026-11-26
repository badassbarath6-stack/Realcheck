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

START="2021-11-22"; END="2026-11-22"
SYMBOLS=["BTCUSDT","ETHUSDT"]
BASE="https://data.binance.vision/data/futures/um/monthly/klines"
OUT=Path("crypto-rolling-walkforward-results"); OUT.mkdir(exist_ok=True)
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
    d=pd.concat(frames,ignore_index=True)
    d["open_time"]=pd.to_numeric(d["open_time"],errors="coerce")
    d=d.dropna(subset=["open_time"]).drop_duplicates("open_time").sort_values("open_time")
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

def signal_map(d, eth=None, overrides=None):
    """Engine-specific factors. Primary values are locked from stage 1."""
    p=overrides or {}; c=d.close; e=d
    def get(k, default): return p.get(k, default)
    # Primary factors: selected on the prior development-only scan and held fixed.
    don_n=int(get("E01",40)); atr_mult=float(get("E02",1.75))
    rsi_low=float(get("E03",45)); squeeze_q=float(get("E04",.10))
    bb_z=float(get("E05",1.75)); rsi_extreme=float(get("E06",25))
    vol_z=float(get("E07",1.5)); atr_expand=float(get("E08",1.25))
    spread_th=float(get("E09",.025)); adx_th=float(get("E10",30))
    # Secondary / tertiary dimensions.
    e01_buf=float(get("E01_buffer",0.0)); e01_confirm=int(get("E01_confirm",1))
    e02_ema=int(get("E02_ema",20)); e02_slope=int(get("E02_slope",1))
    e03_band=float(get("E03_band",18)); e03_pullback=float(get("E03_pullback",99.0))
    e04_look=int(get("E04_lookback",100)); e04_break=float(get("E04_breakout",0.0))
    e05_rsi=float(get("E05_rsi",35)); e05_bb=int(get("E05_bbperiod",20))
    e06_period=int(get("E06_period",14)); e06_confirm=int(get("E06_confirm",1))
    e07_look=int(get("E07_lookback",30)); e07_body=float(get("E07_body",0.0))
    e08_range=int(get("E08_range",48)); e08_quant=float(get("E08_quantile",.20))
    e09_look=int(get("E09_lookback",72)); e09_persist=int(get("E09_persist",1))
    e10_fast=int(get("E10_fast",20)); e10_mid=int(get("E10_mid",50)); e10_slow=int(get("E10_slow",200))

    # Dynamic indicator variants used only by their corresponding engine.
    atr=e.atr
    don_hi=e.high.shift(1).rolling(don_n).max()
    don_lo=e.low.shift(1).rolling(don_n).min()
    ema02=c.ewm(span=e02_ema,adjust=False).mean()
    rsi_delta=c.diff()
    rsi_gain=rsi_delta.clip(lower=0).ewm(alpha=1/e06_period,adjust=False).mean()
    rsi_loss=(-rsi_delta.clip(upper=0)).ewm(alpha=1/e06_period,adjust=False).mean()
    rsi_dyn=100-100/(1+rsi_gain/rsi_loss.replace(0,np.nan))
    bb_mid=c.rolling(e05_bb).mean(); bb_sd=c.rolling(e05_bb).std()
    bbz_dyn=(c-bb_mid)/bb_sd.replace(0,np.nan)
    vol_mean=e.volume.rolling(e07_look).mean()
    vol_std=e.volume.rolling(e07_look).std()
    volz_dyn=(e.volume-vol_mean)/vol_std.replace(0,np.nan)
    range_pct=(e.high.rolling(e08_range).max()-e.low.rolling(e08_range).min())/c
    squeeze=e.bbwidth<e.bbwidth.rolling(e04_look).quantile(squeeze_q)
    squeeze_exp=e.bbwidth<e.bbwidth.rolling(e04_look).quantile(squeeze_q)
    rel_btc=c.pct_change(e09_look)
    ema_fast=c.ewm(span=e10_fast,adjust=False).mean()
    ema_mid=c.ewm(span=e10_mid,adjust=False).mean()
    ema_slow=c.ewm(span=e10_slow,adjust=False).mean()

    def confirmed(condition, n):
        n=max(1,int(n))
        if n==1: return condition.fillna(False)
        return condition.fillna(False).rolling(n).sum().eq(n)

    # E01: channel breakout with ATR clearance and consecutive close confirmation.
    long01=confirmed(c>don_hi+e01_buf*atr,e01_confirm)
    short01=confirmed(c<don_lo-e01_buf*atr,e01_confirm)
    # E02: EMA/ATR trend threshold plus selectable slope horizon.
    sig02_long=(c>c.shift(e02_slope))&(c>ema02+atr_mult*atr)
    sig02_short=(c<c.shift(e02_slope))&(c<ema02-atr_mult*atr)
    # E03: retain the selected EMA trend and RSI lower boundary; tune band width
    # and maximum normalized distance from EMA50 to avoid chasing extended moves.
    rsi_high=rsi_low+e03_band
    dist_long=(c-e.ema50)/atr; dist_short=(e.ema50-c)/atr
    sig03_long=(e.ema50>e.ema200)&(c>e.ema50)&(rsi_dyn.between(rsi_low,rsi_high))&(dist_long<=e03_pullback)
    sig03_short=(e.ema50<e.ema200)&(c<e.ema50)&(rsi_dyn.between(100-rsi_high,100-rsi_low))&(dist_short<=e03_pullback)
    # E04: compression duration and breakout clearance.
    sig04_long=squeeze_exp&(c>e.ema20+e04_break*atr)
    sig04_short=squeeze_exp&(c<e.ema20-e04_break*atr)
    # E05: BB deviation plus RSI confirmation; selectable BB window.
    sig05_long=(bbz_dyn<-bb_z)&(e.rsi<e05_rsi)
    sig05_short=(bbz_dyn>bb_z)&(e.rsi>100-e05_rsi)
    # E06: dynamic RSI period and reversal confirmation.
    sig06_long=(rsi_dyn<rsi_extreme)&(rsi_dyn.shift(e06_confirm)>=rsi_extreme)
    sig06_short=(rsi_dyn>100-rsi_extreme)&(rsi_dyn.shift(e06_confirm)<=100-rsi_extreme)
    # E07: volume shock with body-size quality filter.
    body=(c-e.open).abs()/atr
    sig07_long=(volz_dyn>vol_z)&(c>e.open)&(c>e.ema50)&(body>=e07_body)
    sig07_short=(volz_dyn>vol_z)&(c<e.open)&(c<e.ema50)&(body>=e07_body)
    # E08: contraction range and expansion threshold.
    compressed=range_pct<range_pct.rolling(200).quantile(e08_quant)
    expanded=e.atr/e.atr.rolling(50).mean()>atr_expand
    sig08_long=compressed&expanded&(c>e.ema50)
    sig08_short=compressed&expanded&(c<e.ema50)
    # E09: relative momentum lookback and persistence of relative outperformance.
    sig09=pd.Series(0,index=d.index,dtype=int)
    if eth is not None:
        eth_ret=eth.reindex(e.index) if e09_look==72 else None
        if eth_ret is None:
            # Align ETH close returns using the shared timestamp index.
            # eth argument is the ETH close series for this engine.
            eth_close=eth.attrs.get("close_series") if hasattr(eth,"attrs") else None
            if eth_close is not None: eth_ret=eth_close.pct_change(e09_look).reindex(e.index)
        spread=rel_btc-eth_ret if eth_ret is not None else pd.Series(np.nan,index=d.index)
        long09=confirmed(spread>spread_th,e09_persist)&(rel_btc>0)
        short09=confirmed(spread<-spread_th,e09_persist)&(rel_btc<0)
        sig09=pd.Series(np.select([long09,short09],[1,-1],0),index=d.index)
    # E10: preserve the original three-EMA directional regime. All three
    # selected EMA periods must participate; the prior pass accidentally
    # ignored E10_mid, making that factor dimension inert.
    sig10_long=(e.adx>adx_th)&(ema_fast>ema_mid)&(ema_mid>ema_slow)
    sig10_short=(e.adx>adx_th)&(ema_fast<ema_mid)&(ema_mid<ema_slow)
    sig={
        "E01 Donchian breakout":pd.Series(np.select([long01,short01],[1,-1],0),index=d.index),
        "E02 Supertrend ATR":pd.Series(np.select([sig02_long,sig02_short],[1,-1],0),index=d.index),
        "E03 EMA trend pullback":pd.Series(np.select([sig03_long,sig03_short],[1,-1],0),index=d.index),
        "E04 Volatility squeeze breakout":pd.Series(np.select([sig04_long,sig04_short],[1,-1],0),index=d.index),
        "E05 Bollinger mean reversion":pd.Series(np.select([sig05_long,sig05_short],[1,-1],0),index=d.index),
        "E06 RSI exhaustion reversal":pd.Series(np.select([sig06_long,sig06_short],[1,-1],0),index=d.index),
        "E07 Volume shock continuation":pd.Series(np.select([sig07_long,sig07_short],[1,-1],0),index=d.index),
        "E08 Volatility expansion":pd.Series(np.select([sig08_long,sig08_short],[1,-1],0),index=d.index),
        "E09 BTC-ETH relative momentum":sig09,
        "E10 ADX directional regime":pd.Series(np.select([sig10_long,sig10_short],[1,-1],0),index=d.index),
    }
    return sig

def run_engine(d, sig, name, symbol, sl_atr, rr, sl_buffer_atr=0.0, start_idx=250, end_idx=None):
    # Numpy arrays avoid repeated pandas row construction across the parameter grid.
    op=d.open.to_numpy(float); hi=d.high.to_numpy(float); lo=d.low.to_numpy(float)
    cl=d.close.to_numpy(float); atr=d.atr.to_numpy(float)
    times=d.time.astype(str).to_numpy(); signals=sig.to_numpy(int)
    side=0; entry=stop=target=0.0; entry_i=0; trades=[]
    end_idx=len(d) if end_idx is None else min(int(end_idx),len(d))
    start_idx=max(250,int(start_idx))
    for i in range(start_idx,end_idx-1):
        if side:
            hit_sl=(lo[i]<=stop if side==1 else hi[i]>=stop)
            hit_tp=(hi[i]>=target if side==1 else lo[i]<=target)
            if hit_sl or hit_tp:
                px=stop if hit_sl else target
                gross=side*(px-entry)/entry; net=gross-2*(FEE+SLIPPAGE)
                trades.append(dict(engine=name,symbol=symbol,sl_atr=sl_atr,sl_buffer_atr=sl_buffer_atr,rr=rr,
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
            s=int(signals[i]); entry=float(op[i+1]); dist=(sl_atr+sl_buffer_atr)*float(atr[i])
            side=s; entry_i=i+1; stop=entry-s*dist; target=entry+s*dist*rr
    if side:
        i=end_idx-1; px=float(cl[i]); gross=side*(px-entry)/entry; net=gross-2*(FEE+SLIPPAGE)
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
    # Locked primary factors from the completed primary-factor scan.
    PRIMARY={"E01":40,"E02":1.75,"E03":45,"E04":.10,"E05":1.75,
             "E06":25,"E07":1.5,"E08":1.25,"E09":.025,"E10":30}
    DEFAULTS={
        "E01_buffer":0.0,"E01_confirm":1,"E02_ema":20,"E02_slope":1,
        "E03_band":18,"E03_pullback":99.0,"E04_lookback":100,"E04_breakout":0.0,
        "E05_rsi":35,"E05_bbperiod":20,"E06_period":14,"E06_confirm":1,
        "E07_lookback":30,"E07_body":0.0,"E08_range":48,"E08_quantile":.20,
        "E09_lookback":72,"E09_persist":1,"E10_fast":20,"E10_mid":50,"E10_slow":200}
    ENGINES={
        "E01":"E01 Donchian breakout","E02":"E02 Supertrend ATR",
        "E03":"E03 EMA trend pullback","E04":"E04 Volatility squeeze breakout",
        "E05":"E05 Bollinger mean reversion","E06":"E06 RSI exhaustion reversal",
        "E07":"E07 Volume shock continuation","E08":"E08 Volatility expansion",
        "E09":"E09 BTC-ETH relative momentum","E10":"E10 ADX directional regime"}
    # Frozen benchmark settings supplied by the prior best-performing experiment.
    BENCHMARK={
        ("E01","BTCUSDT"):(2.5,0,2.5),("E01","ETHUSDT"):(3.0,0,2.5),
        ("E02","BTCUSDT"):(2.0,0,3.0),("E02","ETHUSDT"):(1.2,0,2.5),
        ("E03","BTCUSDT"):(2.0,0,4.0),("E03","ETHUSDT"):(1.5,0,2.5),
        ("E04","BTCUSDT"):(1.8,0,4.0),("E04","ETHUSDT"):(2.5,0,2.5),
        ("E05","BTCUSDT"):(3.0,0,2.0),("E05","ETHUSDT"):(0.8,0,4.0),
        ("E06","BTCUSDT"):(3.0,0,1.0),("E06","ETHUSDT"):(2.5,0,4.0),
        ("E07","BTCUSDT"):(2.5,0,1.0),("E07","ETHUSDT"):(3.0,0,1.2),
        ("E08","BTCUSDT"):(2.0,0,3.0),("E08","ETHUSDT"):(1.5,0,1.0),
        ("E09","BTCUSDT"):(1.5,0,4.0),
        ("E10","BTCUSDT"):(3.0,0,4.0),("E10","ETHUSDT"):(1.8,0,2.0)}
    # Restrained SL/buffer/RR candidate grid to keep the rolling test computationally practical.
    SL_VALUES=[1.0,1.5,2.0,2.5,3.0]
    BUFFER_VALUES=[0.0,0.20]
    RR_VALUES=[1.2,2.0,3.0,4.0]
    TRAIN_MONTHS=24
    TEST_MONTHS=6
    MIN_TRAIN_TRADES=100
    MIN_TRAIN_PF=1.15
    START_TS=pd.Timestamp(START,tz="UTC")
    END_TS=pd.Timestamp(END,tz="UTC")
    data={s:indicators(load_symbol(s)) for s in SYMBOLS}
    signals={}
    for code,engine in ENGINES.items():
        for symbol in SYMBOLS:
            if code=="E09" and symbol!="BTCUSDT": continue
            eth_close=data["ETHUSDT"].close if symbol=="BTCUSDT" else None
            if eth_close is not None:
                eth_close.attrs["close_series"]=eth_close
            sig=signal_map(data[symbol],eth_close,{**PRIMARY,**DEFAULTS})[engine]
            signals[(code,symbol)]=sig
    # Six-month non-overlapping forward test blocks, each using only the immediately
    # preceding 24 months to select SL/buffer/RR. Primary and secondary factors stay fixed.
    folds=[]
    test_start=START_TS+pd.DateOffset(months=TRAIN_MONTHS)
    while test_start<END_TS:
        test_end=min(test_start+pd.DateOffset(months=TEST_MONTHS),END_TS)
        train_start=test_start-pd.DateOffset(months=TRAIN_MONTHS)
        folds.append((train_start,test_start,test_end))
        test_start=test_end
    selected_rows=[]; oos_rows=[]; benchmark_rows=[]; fold_audit=[]
    for fold_no,(train_start,test_start,test_end) in enumerate(folds,1):
        for (code,symbol),sig in signals.items():
            d=data[symbol]
            train_a=int(d.time.searchsorted(train_start))
            test_a=int(d.time.searchsorted(test_start))
            test_b=int(d.time.searchsorted(test_end))
            if test_b<=test_a+2: continue
            train_candidates=[]
            for sl in SL_VALUES:
                for buf in BUFFER_VALUES:
                    for rr in RR_VALUES:
                        tr=run_engine(d,sig,ENGINES[code],symbol,sl,rr,buf,train_a,test_a)
                        tf=pd.DataFrame(tr)
                        metrics=summarize(tf.sort_values("exit_time")) if not tf.empty else summarize(pd.DataFrame())
                        train_candidates.append({"engine_code":code,"symbol":symbol,
                            "sl_atr":sl,"sl_buffer_atr":buf,"effective_sl_atr":round(sl+buf,3),
                            "rr":rr,**metrics})
            cdf=pd.DataFrame(train_candidates)
            eligible=cdf[(cdf.trades>=MIN_TRAIN_TRADES)&
                         (cdf.profit_factor>=MIN_TRAIN_PF)&(cdf.net_pnl_usd>0)].copy()
            # If no sufficiently robust profitable configuration exists, abstain for
            # this engine/symbol/fold; do not force a trade-producing configuration.
            if eligible.empty:
                selected_rows.append({"fold":fold_no,"engine_code":code,"engine":ENGINES[code],
                    "symbol":symbol,"train_start":str(train_start),"train_end":str(test_start),
                    "test_start":str(test_start),"test_end":str(test_end),
                    "status":"REJECTED_NO_QUALIFYING_TRAIN_CONFIG","qualifying_configs":0})
                fold_audit.append({"fold":fold_no,"engine_code":code,"symbol":symbol,
                    "status":"NO_QUALIFYING_CONFIG","train_candidates":len(cdf),
                    "qualifying_configs":0,"oos_trades":0})
            else:
                eligible=eligible.sort_values(["profit_factor","net_pnl_usd","trades"],
                                              ascending=[False,False,False])
                best=eligible.iloc[0].to_dict()
                selected_rows.append({"fold":fold_no,"engine_code":code,"engine":ENGINES[code],
                    "symbol":symbol,"train_start":str(train_start),"train_end":str(test_start),
                    "test_start":str(test_start),"test_end":str(test_end),
                    "status":"SELECTED","qualifying_configs":len(eligible),**best})
                trades=run_engine(d,sig,ENGINES[code],symbol,float(best["sl_atr"]),
                                  float(best["rr"]),float(best["sl_buffer_atr"]),test_a,test_b)
                tf=pd.DataFrame(trades)
                metrics=summarize(tf.sort_values("exit_time")) if not tf.empty else summarize(pd.DataFrame())
                oos_rows.append({"fold":fold_no,"engine_code":code,"engine":ENGINES[code],
                    "symbol":symbol,"train_start":str(train_start),"train_end":str(test_start),
                    "test_start":str(test_start),"test_end":str(test_end),
                    "sl_atr":best["sl_atr"],"sl_buffer_atr":best["sl_buffer_atr"],
                    "effective_sl_atr":best["effective_sl_atr"],"rr":best["rr"],**metrics})
                fold_audit.append({"fold":fold_no,"engine_code":code,"symbol":symbol,
                    "status":"SELECTED","train_candidates":len(cdf),
                    "qualifying_configs":len(eligible),"oos_trades":metrics["trades"],
                    "oos_pf":metrics["profit_factor"],"oos_net_pnl_usd":metrics["net_pnl_usd"]})
            # Benchmark is always evaluated independently, even when the quality gate abstains.
            bsl,bbuf,brr=BENCHMARK[(code,symbol)]
            bt=run_engine(d,sig,ENGINES[code],symbol,bsl,brr,bbuf,test_a,test_b)
            bf=pd.DataFrame(bt)
            bm=summarize(bf.sort_values("exit_time")) if not bf.empty else summarize(pd.DataFrame())
            benchmark_rows.append({"fold":fold_no,"engine_code":code,"engine":ENGINES[code],
                "symbol":symbol,"test_start":str(test_start),"test_end":str(test_end),
                "sl_atr":bsl,"sl_buffer_atr":bbuf,"effective_sl_atr":round(bsl+bbuf,3),
                "rr":brr,**bm})
    selected_df=pd.DataFrame(selected_rows); oos_df=pd.DataFrame(oos_rows)
    bench_df=pd.DataFrame(benchmark_rows); audit_df=pd.DataFrame(fold_audit)
    selected_df.to_csv(OUT/"fold_selections_and_abstentions.csv",index=False)
    oos_df.to_csv(OUT/"walkforward_quality_gate_oos.csv",index=False)
    bench_df.to_csv(OUT/"frozen_benchmark_oos.csv",index=False)
    audit_df.to_csv(OUT/"fold_audit.csv",index=False)
    def aggregate(df,group_cols):
        rows=[]
        if df.empty: return pd.DataFrame()
        for key,g in df.groupby(group_cols):
            if not isinstance(key,tuple): key=(key,)
            row=dict(zip(group_cols,key))
            row.update(summarize(g.sort_values("test_start") if "test_start" in g else g))
            rows.append(row)
        return pd.DataFrame(rows)
    if not oos_df.empty:
        aggregate(oos_df,["engine_code","engine","symbol"]).to_csv(OUT/"quality_gate_engine_symbol_summary.csv",index=False)
        aggregate(oos_df,["engine_code","engine"]).to_csv(OUT/"quality_gate_engine_summary.csv",index=False)
    if not bench_df.empty:
        aggregate(bench_df,["engine_code","engine","symbol"]).to_csv(OUT/"benchmark_engine_symbol_summary.csv",index=False)
        aggregate(bench_df,["engine_code","engine"]).to_csv(OUT/"benchmark_engine_summary.csv",index=False)
    manifest={
        "experiment":"Rolling walk-forward quality gate with abstention",
        "data_period_utc":[START,END],"symbols":SYMBOLS,"timeframe":"1h",
        "candles":{s:len(d) for s,d in data.items()},
        "primary_factors_locked":PRIMARY,"secondary_tertiary_factors_fixed":DEFAULTS,
        "train_window_months":TRAIN_MONTHS,"forward_test_months":TEST_MONTHS,
        "folds":[{"train_start":str(a),"train_end":str(b),"test_start":str(b),"test_end":str(c)} for a,b,c in folds],
        "candidate_sl_atr":SL_VALUES,"candidate_sl_buffer_atr":BUFFER_VALUES,
        "candidate_rr":RR_VALUES,"minimum_training_trades":MIN_TRAIN_TRADES,
        "minimum_training_profit_factor":MIN_TRAIN_PF,
        "selection_rule":"Select only if training PF >=1.15, net P&L >0 and >=100 trades; rank PF then net P&L then entries; otherwise abstain",
        "benchmark":"User's original frozen SL/RR table; primary factors held at updated values for all engines",
        "fees_per_side":FEE,"slippage_per_side":SLIPPAGE,"fixed_notional_usd":NOTIONAL,
        "max_holding_bars":72,"entry":"next candle open after closed-bar signal",
        "same_bar_rule":"SL wins if SL and TP both touched","funding_included":False,
        "critical_caveat":"The quality gate cannot guarantee zero losing trades. It only rejects engine/symbol/fold configurations that fail the historical training threshold; forward-test trades can still lose. This is research, not a live trading safety guarantee.",
        "limitations":["Funding excluded","No portfolio overlap/capital model","Fixed notional; no compounding",
            "SL/TP intrabar ordering uses conservative stop-first assumption",
            "Six-month forward blocks are chronological; each selection uses only the preceding 24 months"],
        "counts":{"folds":len(folds),"selected_rows":len(selected_df),
                  "oos_rows":len(oos_df),"benchmark_rows":len(bench_df)}
    }
    (OUT/"manifest.json").write_text(json.dumps(manifest,indent=2,default=str))
    print("WALK-FORWARD MANIFEST:",json.dumps(manifest,default=str))
    print("QUALITY-GATE OOS:")
    if not oos_df.empty: print(oos_df.to_string(index=False))
    else: print("NO CONFIGURATIONS PASSED THE TRAINING QUALITY GATE")
    print("FROZEN BENCHMARK OOS:")
    print(bench_df.to_string(index=False))
if __name__=="__main__": main()
