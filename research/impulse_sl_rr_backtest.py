#!/usr/bin/env python3
"""Config 1 impulse-entry SL/TP sweep. Independent configurations; no retracement."""
from __future__ import annotations
import argparse,csv,hashlib,json,math,re,zipfile,urllib.request
from pathlib import Path
from datetime import datetime,timezone
import numpy as np
from numba import njit

START=int(datetime(2023,11,1,tzinfo=timezone.utc).timestamp()*1000)
END=int(datetime(2026,11,1,tzinfo=timezone.utc).timestamp()*1000)
BASE="https://data.binance.vision/data/futures/um"
TFS={"5m":5,"15m":15,"30m":30,"1h":60,"2h":120,"4h":240}
IMPULSE_ATR={"5m":5.0,"15m":5.0,"30m":5.0,"1h":2.6,"2h":2.6,"4h":2.6}
SL_VALUES=np.round(np.arange(0.5,5.0001,0.1),1)
RR_VALUES=np.round(np.arange(0.5,6.0001,0.25),2)
FEE_BPS=5.0; NORMAL_SLIPPAGE_BPS=2.0; STRESS_SLIPPAGE_BPS=7.0; ATR_PERIOD=14

def sha(p):
 h=hashlib.sha256()
 with open(p,"rb") as f:
  for b in iter(lambda:f.read(1<<20),b""):h.update(b)
 return h.hexdigest()

def months():
 y,m=2023,9
 while (y,m)<=(2026,10):
  yield y,m
  m+=1
  if m==13:y+=1;m=1

def fetch(url,path):
 path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
 if not path.exists():
  req=urllib.request.Request(url,headers={"User-Agent":"Realcheck-Impulse-SL-RR/1.0"})
  with urllib.request.urlopen(req,timeout=180) as r,path.open("wb") as f:
   while True:
    b=r.read(1<<20)
    if not b:break
    f.write(b)
 req=urllib.request.Request(url+".CHECKSUM",headers={"User-Agent":"Realcheck-Impulse-SL-RR/1.0"})
 with urllib.request.urlopen(req,timeout=60) as r:s=r.read().decode()
 m=re.search(r"([0-9a-fA-F]{64})",s)
 if not m or sha(path).lower()!=m.group(1).lower():
  path.unlink(missing_ok=True);raise RuntimeError("Binance archive checksum verification failed: "+url)
 return path

def load(paths):
 d={}
 for p in paths:
  with zipfile.ZipFile(p) as z:
   n=next(x for x in z.namelist() if x.endswith(".csv"))
   with z.open(n) as f:
    for raw in f:
     a=raw.decode().strip().split(",")
     if len(a)<6 or not a[0].isdigit():continue
     t=int(a[0]);o,h,l,c=map(float,a[1:5])
     if t in d and d[t]!=(o,h,l,c):raise RuntimeError("Conflicting duplicate M1 candle")
     d[t]=(o,h,l,c)
 return [(t,*v) for t,v in sorted(d.items())]

def make_tf_bars(m1,mins):
 step=mins*60000;out=[]
 for t,o,h,l,c in m1:
  b=t//step*step
  if not out or out[-1][0]!=b:out.append([b,o,h,l,c,1])
  else:
   x=out[-1];x[2]=max(x[2],h);x[3]=min(x[3],l);x[4]=c;x[5]+=1
 return [tuple(x) for x in out if x[5]==mins]

def wilder_atr(bs):
 tr=[]
 for i,b in enumerate(bs):
  pc=bs[i-1][4] if i else b[4]
  tr.append(max(b[2]-b[3],abs(b[2]-pc),abs(b[3]-pc)))
 out=np.full(len(bs),np.nan,dtype=np.float64)
 if len(bs)>=ATR_PERIOD:
  out[ATR_PERIOD-1]=sum(tr[:ATR_PERIOD])/ATR_PERIOD
  for i in range(ATR_PERIOD,len(bs)):out[i]=(out[i-1]*(ATR_PERIOD-1)+tr[i])/ATR_PERIOD
 return out

def make_impulses(m1,tf_bars,atr,tf):
 tfm=TFS[tf];step=tfm*60000
 starts={int(b[0]):i for i,b in enumerate(tf_bars)}
 events=[];active_bucket=None;bucket_open=0.0;triggered=False
 threshold=IMPULSE_ATR[tf]
 for i,(t,o,h,l,c) in enumerate(m1):
  bucket=t//step*step
  if bucket!=active_bucket:
   active_bucket=bucket;bucket_open=o;triggered=False
  if triggered or t<START or t>=END:continue
  pi=starts.get(bucket-step)
  if pi is None or not math.isfinite(atr[pi]) or atr[pi]<=0:continue
  displacement=c-bucket_open
  if abs(displacement)>=threshold*atr[pi] and displacement!=0:
   events.append((i,1 if displacement>0 else -1,float(atr[pi])))
   triggered=True
 return events

@njit
def simulate_grid(m1_t,m1_o,m1_h,m1_l,m1_c,events,sl_values,rr_values,split1,split2,fee,slip,stress_slip):
 nsl=len(sl_values);nrr=len(rr_values);nconfig=nsl*nrr
 # columns per period: trades,wins,gp,gl,net,stress_gp,stress_gl,stress_net,max_dd
 out=np.zeros((nconfig,3,9),dtype=np.float64)
 for si in range(nsl):
  for ri in range(nrr):
   ci=si*nrr+ri;slm=sl_values[si];rr=rr_values[ri]
   active_until=-1
   eq=np.zeros(3);peak=np.zeros(3);maxdd=np.zeros(3)
   for ei in range(len(events)):
    signal_i=events[ei,0]
    if signal_i<=active_until:continue
    entry_i=signal_i+1
    if entry_i>=len(m1_t):continue
    direction=events[ei,1];atr=events[ei,2]
    entry=m1_o[entry_i];risk=slm*atr
    if risk<=0 or entry<=0:continue
    if direction==1:stop=entry-risk;target=entry+risk*rr
    else:stop=entry+risk;target=entry-risk*rr
    exit_px=m1_c[len(m1_t)-1];exit_i=len(m1_t)-1
    for k in range(entry_i,len(m1_t)):
     op=m1_o[k];hi=m1_h[k];lo=m1_l[k]
     hit=False
     if direction==1:
      if op<=stop:exit_px=op;hit=True
      elif lo<=stop:exit_px=stop;hit=True
      elif op>=target:exit_px=op;hit=True
      elif hi>=target:exit_px=target;hit=True
     else:
      if op>=stop:exit_px=op;hit=True
      elif hi>=stop:exit_px=stop;hit=True
      elif op<=target:exit_px=op;hit=True
      elif lo<=target:exit_px=target;hit=True
     if hit:exit_i=k;break
    active_until=exit_i
    gross=direction*(exit_px-entry)/entry*10000.0
    net=gross-2.0*(fee+slip);stress=gross-2.0*(fee+stress_slip)
    signal_t=m1_t[signal_i];exit_t=m1_t[exit_i]
    period=-1;boundary=0
    if signal_t<split1:period=0;boundary=split1
    elif signal_t<split2:period=1;boundary=split2
    elif signal_t<END:period=2;boundary=END
    if period<0 or exit_t>=boundary:continue
    a=out[ci,period]
    a[0]+=1.0
    if net>0:a[1]+=1.0;a[2]+=net
    elif net<0:a[3]+=-net
    a[4]+=net
    if stress>0:a[5]+=stress
    elif stress<0:a[6]+=-stress
    a[7]+=stress
    eq[period]+=net
    if eq[period]>peak[period]:peak[period]=eq[period]
    dd=peak[period]-eq[period]
    if dd>maxdd[period]:maxdd[period]=dd
    a[8]=maxdd[period]
 return out

def metrics_row(a):
 n=int(a[0]);wins=int(a[1]);gp=a[2];gl=a[3];net=a[4]
 return {"trades":n,"wins":wins,"losses":n-wins,"win_rate":wins/n if n else 0.0,
         "gross_profit_bps":gp,"gross_loss_bps":gl,"net_bps":net,
         "pf":gp/gl if gl else (999.0 if gp else 0.0),"expectancy_bps":net/n if n else 0.0,
         "max_drawdown_bps":a[8],"stress7_net_bps":a[7],
         "stress7_pf":a[5]/a[6] if a[6] else (999.0 if a[5] else 0.0)}

def run(symbol,tf,data_dir,out_dir):
 files=[]
 for y,m in months():
  name=f"{symbol}-1m-{y}-{m:02d}.zip"
  files.append(fetch(f"{BASE}/monthly/klines/{symbol}/1m/{name}",Path(data_dir)/name))
 allm=load(files);warm=START-35*86400000
 m1=[x for x in allm if warm<=x[0]<END]
 if not m1 or m1[0][0]>warm or m1[-1][0]<END-60000:
  raise RuntimeError("M1 data does not cover warmup through final requested minute")
 gaps=[(a[0],b[0]) for a,b in zip(m1,m1[1:]) if b[0]-a[0]!=60000]
 if gaps:raise RuntimeError(f"M1 continuity failure: {len(gaps)} gaps; first={gaps[:3]}")
 bs=make_tf_bars(m1,TFS[tf]);atr=wilder_atr(bs);events=make_impulses(m1,bs,atr,tf)
 if not events:raise RuntimeError("No qualifying impulse events found; refusing empty backtest")
 split1=START+int((END-START)*.6);split2=START+int((END-START)*.8)
 arr=np.asarray(m1,dtype=np.float64);events_np=np.asarray(events,dtype=np.float64)
 result=simulate_grid(arr[:,0],arr[:,1],arr[:,2],arr[:,3],arr[:,4],events_np,
                      SL_VALUES,RR_VALUES,split1,split2,FEE_BPS,NORMAL_SLIPPAGE_BPS,STRESS_SLIPPAGE_BPS)
 rows=[]
 for si,slm in enumerate(SL_VALUES):
  for ri,rr in enumerate(RR_VALUES):
   ci=si*len(RR_VALUES)+ri
   row={"symbol":symbol,"timeframe":tf,"impulse_atr_minimum":IMPULSE_ATR[tf],
        "sl_atr":float(slm),"rr":float(rr)}
   for pi,pname in enumerate(("train","validation","oos")):
    m=metrics_row(result[ci,pi])
    for k,v in m.items():row[pname+"_"+k]=v
   rows.append(row)
 # Keep full grid in stable SL/RR order; rankings are separate derived files.
 out=Path(out_dir);out.mkdir(parents=True,exist_ok=True)
 fields=list(rows[0])
 with (out/f"{symbol}_{tf}_sl_rr_all.csv").open("w",newline="") as f:
  w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
 manifest={"symbol":symbol,"timeframe":tf,"period_start_utc":"2023-11-01T00:00:00Z",
  "period_end_exclusive_utc":"2026-11-01T00:00:00Z","impulse_atr_minimum":IMPULSE_ATR[tf],
  "atr_period":ATR_PERIOD,"sl_atr_values":SL_VALUES.tolist(),"rr_values":RR_VALUES.tolist(),
  "configurations":len(rows),"impulse_events":len(events),"m1_rows":len(m1),"m1_gap_count":len(gaps),
  "timeframe_bars":len(bs),"fees_bps_per_side":FEE_BPS,
  "normal_slippage_bps_per_side":NORMAL_SLIPPAGE_BPS,"stress_slippage_bps_per_side":STRESS_SLIPPAGE_BPS,
  "funding_model":"Not included; this is a price/fee/slippage backtest, not a fully funded perpetual PnL simulation.",
  "split_ms":[START,split1,split2,END],
  "execution":"Each timeframe candle can emit at most one impulse, at the first completed M1 close crossing the fixed Config 1 displacement threshold. Entry is next M1 open. Every SL×RR combination is independent; each config may hold one position at a time and ignores new impulses while occupied.",
  "risk":"SL distance = selected SL_ATR × ATR(14) of the prior completed timeframe candle, measured from actual entry. TP distance = SL distance × selected RR.",
  "intrabar":"Stop-first when both levels are touched in one M1 candle; adverse stop gaps fill at candle open; target gaps fill at candle open.",
  "data_archives":[{"name":p.name,"sha256":sha(p)} for p in files]}
 (out/f"{symbol}_{tf}_sl_rr_manifest.json").write_text(json.dumps(manifest,indent=2))
 # Local summary based on validation only; OOS is reported but never used for selection.
 eligible=[r for r in rows if r["validation_trades"]>=30]
 eligible.sort(key=lambda r:(r["validation_pf"],r["validation_net_bps"]),reverse=True)
 print(f"{symbol} {tf}: {len(rows)} configs; {len(events)} impulse events; M1 rows={len(m1)}; gaps=0")
 for r in eligible[:8]:
  print(f"SL={r['sl_atr']:.1f} ATR RR={r['rr']:.2f} | val PF={r['validation_pf']:.3f} n={r['validation_trades']} | OOS PF={r['oos_pf']:.3f} n={r['oos_trades']} | OOS stress PF={r['oos_stress7_pf']:.3f}")

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--symbol",required=True,choices=["BTCUSDT","ETHUSDT"])
 p.add_argument("--timeframe",required=True,choices=sorted(TFS))
 p.add_argument("--data-dir",default="/tmp/binance");p.add_argument("--output-dir",default="research-output")
 a=p.parse_args();run(a.symbol,a.timeframe,a.data_dir,a.output_dir)
if __name__=="__main__":main()
