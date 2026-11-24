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
OUT=Path("crypto-engine-factor-tuning-results"); OUT.mkdir(exist_ok=True)
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
    c=d.close; e=d; p=overrides or {}
    don_n=int(p.get("E01",20)); atr_mult=float(p.get("E02",1.5))
    rsi_low=float(p.get("E03",40)); rsi_high=rsi_low+18
    squeeze_q=float(p.get("E04",.20)); bb_z=float(p.get("E05",2.0))
    rsi_extreme=float(p.get("E06",20)); vol_z=float(p.get("E07",2.0))
    atr_expand=float(p.get("E08",1.25)); spread_th=float(p.get("E09",.015))
    adx_th=float(p.get("E10",25))
    don_hi=e.high.shift(1).rolling(don_n).max()
    don_lo=e.low.shift(1).rolling(don_n).min()
    sig={}
    sig["E01 Donchian breakout"]=pd.Series(np.select([c>don_hi,c<don_lo],[1,-1],0),index=d.index)
    sig["E02 Supertrend ATR"]=pd.Series(np.select([(c>c.shift(1))&(c>e.ema20+atr_mult*e.atr),(c<c.shift(1))&(c<e.ema20-atr_mult*e.atr)],[1,-1],0),index=d.index)
    sig["E03 EMA trend pullback"]=pd.Series(np.select([(e.ema50>e.ema200)&(c>e.ema50)&(e.rsi.between(rsi_low,rsi_high)),(e.ema50<e.ema200)&(c<e.ema50)&(e.rsi.between(100-rsi_high,100-rsi_low))],[1,-1],0),index=d.index)
    squeeze=e.bbwidth<e.bbwidth.rolling(100).quantile(squeeze_q)
    sig["E04 Volatility squeeze breakout"]=pd.Series(np.select([squeeze&(c>e.ema20),squeeze&(c<e.ema20)],[1,-1],0),index=d.index)
    sig["E05 Bollinger mean reversion"]=pd.Series(np.select([(e.bbz<-bb_z)&(e.rsi<35),(e.bbz>bb_z)&(e.rsi>65)],[1,-1],0),index=d.index)
    sig["E06 RSI exhaustion reversal"]=pd.Series(np.select([(e.rsi<rsi_extreme)&(e.rsi.shift(1)>=rsi_extreme),(e.rsi>(100-rsi_extreme))&(e.rsi.shift(1)<=(100-rsi_extreme))],[1,-1],0),index=d.index)
    sig["E07 Volume shock continuation"]=pd.Series(np.select([(e.volz>vol_z)&(c>e.open)&(c>e.ema50),(e.volz>vol_z)&(c<e.open)&(c<e.ema50)],[1,-1],0),index=d.index)
    range_pct=(e.high.rolling(48).max()-e.low.rolling(48).min())/c
    sig["E08 Volatility expansion"]=pd.Series(np.select([(range_pct<range_pct.rolling(200).quantile(.2))&(e.atr/e.atr.rolling(50).mean()>atr_expand)&(c>e.ema50),(range_pct<range_pct.rolling(200).quantile(.2))&(e.atr/e.atr.rolling(50).mean()>atr_expand)&(c<e.ema50)],[1,-1],0),index=d.index)
    if eth is not None:
        spread=e.ret72-eth.reindex(e.index)
        sig["E09 BTC-ETH relative momentum"]=pd.Series(np.select([(spread>spread_th)&(e.ret72>0),(spread<-spread_th)&(e.ret72<0)],[1,-1],0),index=d.index)
    else:
        sig["E09 BTC-ETH relative momentum"]=pd.Series(0,index=d.index)
    sig["E10 ADX directional regime"]=pd.Series(np.select([(e.adx>adx_th)&(e.ema20>e.ema50)&(e.ema50>e.ema200),(e.adx>adx_th)&(e.ema20<e.ema50)&(e.ema50<e.ema200)],[1,-1],0),index=d.index)
    return sig

def run_engine(d, sig, name, symbol, sl_atr, rr, start_idx=250, end_idx=None):
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
    # IMPORTANT: SL_ATR and RR are frozen at the exact engine/symbol values
    # established in the previous parameter-selection work. This experiment
    # changes strategy-specific signal factors only.
    CONFIG = {
        ("E01 Donchian breakout","BTCUSDT"):(2.5,2.5), ("E01 Donchian breakout","ETHUSDT"):(3.0,2.5),
        ("E02 Supertrend ATR","BTCUSDT"):(2.0,3.0), ("E02 Supertrend ATR","ETHUSDT"):(1.2,2.5),
        ("E03 EMA trend pullback","BTCUSDT"):(2.0,4.0), ("E03 EMA trend pullback","ETHUSDT"):(1.5,2.5),
        ("E04 Volatility squeeze breakout","BTCUSDT"):(1.8,4.0), ("E04 Volatility squeeze breakout","ETHUSDT"):(2.5,2.5),
        ("E05 Bollinger mean reversion","BTCUSDT"):(3.0,2.0), ("E05 Bollinger mean reversion","ETHUSDT"):(0.8,4.0),
        ("E06 RSI exhaustion reversal","BTCUSDT"):(3.0,1.0), ("E06 RSI exhaustion reversal","ETHUSDT"):(2.5,4.0),
        ("E07 Volume shock continuation","BTCUSDT"):(2.5,1.0), ("E07 Volume shock continuation","ETHUSDT"):(3.0,1.2),
        ("E08 Volatility expansion","BTCUSDT"):(2.0,3.0), ("E08 Volatility expansion","ETHUSDT"):(1.5,1.0),
        ("E09 BTC-ETH relative momentum","BTCUSDT"):(1.5,4.0),
        ("E10 ADX directional regime","BTCUSDT"):(3.0,4.0), ("E10 ADX directional regime","ETHUSDT"):(1.8,2.0),
    }
    FACTORS = {
        "E01":("donchian_lookback",[10,15,20,30,40,55]),
        "E02":("atr_trend_multiplier",[1.0,1.25,1.5,1.75,2.0]),
        "E03":("pullback_rsi_lower_bound",[35,38,40,42,45]),
        "E04":("squeeze_quantile",[0.10,0.15,0.20,0.25,0.30]),
        "E05":("bollinger_z_threshold",[1.5,1.75,2.0,2.25,2.5]),
        "E06":("rsi_reversal_extreme",[15,18,20,22,25]),
        "E07":("volume_z_threshold",[1.5,1.75,2.0,2.25,2.5]),
        "E08":("atr_expansion_ratio",[1.10,1.20,1.25,1.30,1.40]),
        "E09":("relative_strength_spread_threshold",[0.005,0.010,0.015,0.020,0.025]),
        "E10":("adx_minimum",[18,20,22,25,28,30]),
    }
    BASELINE={"E01":20,"E02":1.5,"E03":40,"E04":0.20,"E05":2.0,"E06":20,"E07":2.0,"E08":1.25,"E09":0.015,"E10":25}
    ENGINE_NAMES={
        "E01":"E01 Donchian breakout","E02":"E02 Supertrend ATR",
        "E03":"E03 EMA trend pullback","E04":"E04 Volatility squeeze breakout",
        "E05":"E05 Bollinger mean reversion","E06":"E06 RSI exhaustion reversal",
        "E07":"E07 Volume shock continuation","E08":"E08 Volatility expansion",
        "E09":"E09 BTC-ETH relative momentum","E10":"E10 ADX directional regime"
    }
    DEV_END="2024-11-22"
    data={s:indicators(load_symbol(s)) for s in SYMBOLS}
    split={s:int(data[s].time.searchsorted(pd.Timestamp(DEV_END,tz="UTC"))) for s in SYMBOLS}
    # Store each candidate's development and holdout trades separately. The
    # holdout period is never used to select the factor.
    dev_rows=[]; hold_rows=[]; trade_store={}
    for code,(factor_name,values) in FACTORS.items():
        engine=ENGINE_NAMES[code]
        symbols=[s for s in SYMBOLS if (engine,s) in CONFIG]
        for value in values:
            for s in symbols:
                d=data[s]
                eth=data["ETHUSDT"].ret72 if s=="BTCUSDT" else None
                sigs=signal_map(d,eth,{code:value})[engine]
                sl_atr,rr=CONFIG[(engine,s)]
                cut=split[s]
                dev=run_engine(d,sigs,engine,s,sl_atr,rr,250,cut)
                hold=run_engine(d,sigs,engine,s,sl_atr,rr,cut,len(d))
                for arr in (dev,hold):
                    for tr in arr:
                        tr["factor_name"]=factor_name; tr["factor_value"]=value
                trade_store[(code,value,s,"development")]=dev
                trade_store[(code,value,s,"holdout")]=hold
                if dev: dev_rows.extend(dev)
                if hold: hold_rows.extend(hold)
    dev_tr=pd.DataFrame(dev_rows); hold_tr=pd.DataFrame(hold_rows)
    if dev_tr.empty: raise RuntimeError("No development trades produced by factor scan")
    if not hold_tr.empty:
        hold_tr["exit_dt"]=pd.to_datetime(hold_tr.exit_time,utc=True)
    dev_tr["exit_dt"]=pd.to_datetime(dev_tr.exit_time,utc=True)
    def pooled_summary(frame, code, value):
        g=frame[(frame.engine==ENGINE_NAMES[code])&(frame.factor_value==value)] if not frame.empty else pd.DataFrame()
        return summarize(g.sort_values("exit_dt")) if not g.empty else summarize(pd.DataFrame())
    dev_summary=[]; hold_summary=[]
    for code,(factor_name,values) in FACTORS.items():
        for value in values:
            dv=pooled_summary(dev_tr,code,value); hv=pooled_summary(hold_tr,code,value)
            dev_summary.append({"engine_code":code,"engine":ENGINE_NAMES[code],"factor_name":factor_name,"factor_value":value,**dv})
            hold_summary.append({"engine_code":code,"engine":ENGINE_NAMES[code],"factor_name":factor_name,"factor_value":value,**hv})
    dev_df=pd.DataFrame(dev_summary); hold_df=pd.DataFrame(hold_summary)
    dev_df.to_csv(OUT/"factor_scan_development.csv",index=False)
    hold_df.to_csv(OUT/"factor_scan_holdout_all_candidates.csv",index=False)
    # Choose the factor solely on development data. Require >=100 trades pooled
    # across available symbols; rank PF, then net P&L, then entries.
    selected={}
    for code,(factor_name,values) in FACTORS.items():
        sub=dev_df[(dev_df.engine_code==code)&(dev_df.trades>=100)].copy()
        if sub.empty:
            sub=dev_df[dev_df.engine_code==code].copy()
        sub=sub.sort_values(["profit_factor","net_pnl_usd","trades"],ascending=[False,False,False],na_position="last")
        selected[code]=sub.iloc[0].factor_value
    comparison=[]; selected_trades=[]
    for code,(factor_name,values) in FACTORS.items():
        engine=ENGINE_NAMES[code]
        chosen=selected[code]; base=BASELINE[code]
        for label,value in [("BASELINE",base),("SELECTED_ON_DEVELOPMENT",chosen)]:
            for s in [x for x in SYMBOLS if (engine,x) in CONFIG]:
                arr=trade_store.get((code,value,s,"holdout"),[])
                if arr:
                    selected_trades.extend([{**x,"validation_role":label} for x in arr])
                g=pd.DataFrame(arr)
                if not g.empty: g["exit_dt"]=pd.to_datetime(g.exit_time,utc=True)
                metrics=summarize(g.sort_values("exit_dt")) if not g.empty else summarize(pd.DataFrame())
                sl_atr,rr=CONFIG[(engine,s)]
                comparison.append({"engine_code":code,"engine":engine,"symbol":s,
                    "validation_role":label,"factor_name":factor_name,"factor_value":value,
                    "fixed_sl_atr":sl_atr,"fixed_rr":rr,**metrics})
    pd.DataFrame(comparison).to_csv(OUT/"selected_factor_holdout_comparison.csv",index=False)
    # Engine-level factor selection and holdout summary.
    chosen_rows=[]
    for code,(factor_name,values) in FACTORS.items():
        chosen=selected[code]
        drow=dev_df[(dev_df.engine_code==code)&(dev_df.factor_value==chosen)].iloc[0].to_dict()
        hrow=hold_df[(hold_df.engine_code==code)&(hold_df.factor_value==chosen)].iloc[0].to_dict()
        brow=hold_df[(hold_df.engine_code==code)&(hold_df.factor_value==BASELINE[code])].iloc[0].to_dict()
        chosen_rows.append({"engine_code":code,"engine":ENGINE_NAMES[code],"factor_name":factor_name,
            "baseline_factor":BASELINE[code],"selected_factor":chosen,
            "development_entries":drow["trades"],"development_pf":drow["profit_factor"],
            "holdout_entries_selected":hrow["trades"],"holdout_pf_selected":hrow["profit_factor"],
            "holdout_net_pnl_selected":hrow["net_pnl_usd"],
            "holdout_entries_baseline":brow["trades"],"holdout_pf_baseline":brow["profit_factor"],
            "holdout_net_pnl_baseline":brow["net_pnl_usd"]})
    pd.DataFrame(chosen_rows).to_csv(OUT/"factor_selection_and_validation.csv",index=False)
    # Annual results for selected vs baseline factor, using the same frozen SL/RR.
    yearly=[]
    for code,(factor_name,values) in FACTORS.items():
        engine=ENGINE_NAMES[code]
        for role,value in [("BASELINE",BASELINE[code]),("SELECTED_ON_DEVELOPMENT",selected[code])]:
            for s in [x for x in SYMBOLS if (engine,x) in CONFIG]:
                arr=trade_store.get((code,value,s,"holdout"),[])
                if not arr: continue
                g=pd.DataFrame(arr); g["exit_dt"]=pd.to_datetime(g.exit_time,utc=True); g["year"]=g.exit_dt.dt.year
                for year,yg in g.groupby("year"):
                    yearly.append({"engine_code":code,"engine":engine,"symbol":s,"role":role,
                        "factor_name":factor_name,"factor_value":value,"year":int(year),**summarize(yg)})
    pd.DataFrame(yearly).to_csv(OUT/"selected_factor_yearly_holdout.csv",index=False)
    frozen=[]
    for (engine,symbol),(sl_atr,rr) in CONFIG.items():
        frozen.append({"engine":engine,"symbol":symbol,"sl_atr":sl_atr,"rr":rr})
    pd.DataFrame(frozen).to_csv(OUT/"frozen_sl_rr_parameters.csv",index=False)
    manifest={"period_utc":[START,END],"development_period_utc":[START,DEV_END],
        "untouched_holdout_period_utc":[DEV_END,END],"symbols":SYMBOLS,"timeframe":"1h",
        "candles":{s:len(d) for s,d in data.items()},"fee_per_side":FEE,
        "slippage_per_side":SLIPPAGE,"fixed_notional_usd":NOTIONAL,
        "engines":10,"factor_candidates":sum(len(v[1]) for v in FACTORS.values()),
        "factor_candidates_per_engine":{k:len(v[1]) for k,v in FACTORS.items()},
        "selection_rule":"Select factor using development period only; pooled engine PF first, net P&L second, entries third; >=100 development entries preferred.",
        "frozen_risk_parameters":"Per-engine/per-symbol SL_ATR and RR copied unchanged from the previous five-year selected-parameter experiment. No SL/RR optimization or changes in this factor scan.",
        "fixed_sl_rr":frozen,"max_holding_bars":72,"entry":"next candle open after closed-bar signal",
        "intrabar_policy":"stop-loss wins when SL and TP both touched",
        "funding":"NOT INCLUDED; results are not funding-adjusted",
        "note":"Individual engine-specific signal factors tested one at a time. Factor is selected only on 2021-11-22 to 2024-11-22 development period and evaluated on 2024-11-22 to 2026-11-22 holdout. The holdout is untouched by factor selection. Aggregate metrics pool independent fixed-notional trades, not a portfolio."}
    (OUT/"manifest.json").write_text(json.dumps(manifest,indent=2))
    print("FACTOR SELECTION / HOLDOUT VALIDATION:")
    print(pd.DataFrame(chosen_rows).to_string(index=False))
    print("FROZEN SL/RR:")
    print(pd.DataFrame(frozen).to_string(index=False))
    print("MANIFEST:",json.dumps(manifest))
if __name__=="__main__": main()
