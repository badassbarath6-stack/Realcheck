#!/usr/bin/env python3
"""Impulse-strength-only sweep. No retracement, confirmation filters, or live-code imports."""
import argparse,csv,hashlib,json,math,re,zipfile,urllib.request
from pathlib import Path
from datetime import datetime,timezone
START=int(datetime(2023,11,1,tzinfo=timezone.utc).timestamp()*1000)
END=int(datetime(2026,11,1,tzinfo=timezone.utc).timestamp()*1000)
BASE="https://data.binance.vision/data/futures/um"
TFS={"5m":5,"15m":15,"30m":30,"1h":60,"2h":120,"4h":240}
THRESHOLDS=[round(x/10,1) for x in range(5,101)]
ATR_PERIOD=14; SL_BUFFER=.2; RR=2.0; FEE=5.; SLIP=2.

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
  req=urllib.request.Request(url,headers={"User-Agent":"Realcheck-Impulse-Research/1.0"})
  with urllib.request.urlopen(req,timeout=180) as r,path.open("wb") as f:
   while True:
    b=r.read(1<<20)
    if not b:break
    f.write(b)
 req=urllib.request.Request(url+".CHECKSUM",headers={"User-Agent":"Realcheck-Impulse-Research/1.0"})
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

def bars(m1,mins):
 step=mins*60000;out=[]
 for t,o,h,l,c in m1:
  b=t//step*step
  if not out or out[-1][0]!=b:out.append([b,o,h,l,c,1])
  else:
   x=out[-1];x[2]=max(x[2],h);x[3]=min(x[3],l);x[4]=c;x[5]+=1
 return [tuple(x) for x in out if x[5]==mins]

def atrs(bs):
 tr=[]
 for i,b in enumerate(bs):
  pc=bs[i-1][4] if i else b[4]
  tr.append(max(b[2]-b[3],abs(b[2]-pc),abs(b[3]-pc)))
 out=[float("nan")]*len(bs)
 if len(bs)>=ATR_PERIOD:
  out[ATR_PERIOD-1]=sum(tr[:ATR_PERIOD])/ATR_PERIOD
  for i in range(ATR_PERIOD,len(bs)):out[i]=(out[i-1]*(ATR_PERIOD-1)+tr[i])/ATR_PERIOD
 return out

def metrics(ts):
 p=[x["net_bps"] for x in sorted(ts,key=lambda z:z["entry_ms"])]
 gp=sum(x for x in p if x>0);gl=-sum(x for x in p if x<0);eq=peak=dd=0.
 for x in p:eq+=x;peak=max(peak,eq);dd=max(dd,peak-eq)
 return {"trades":len(p),"wins":sum(x>0 for x in p),"losses":sum(x<=0 for x in p),
 "win_rate":sum(x>0 for x in p)/len(p) if p else 0.,"gross_profit_bps":gp,"gross_loss_bps":gl,
 "net_bps":sum(p),"pf":gp/gl if gl else (999. if gp else 0.),
 "expectancy_bps":sum(p)/len(p) if p else 0.,"max_drawdown_bps":dd}

def run(symbol,tf,data_dir,out_dir):
 files=[]
 for y,m in months():
  name=f"{symbol}-1m-{y}-{m:02d}.zip"
  files.append(fetch(f"{BASE}/monthly/klines/{symbol}/1m/{name}",Path(data_dir)/name))
 allm=load(files);warm=START-35*86400000
 m1=[x for x in allm if warm<=x[0]<END]
 if not m1 or m1[0][0]>warm or m1[-1][0]<END-60000:raise RuntimeError("M1 data does not cover warmup through final requested minute")
 gaps=[(a[0],b[0]) for a,b in zip(m1,m1[1:]) if b[0]-a[0]!=60000]
 if gaps:raise RuntimeError(f"M1 continuity failure: {len(gaps)} gaps; first={gaps[:3]}")
 tfm=TFS[tf];tfms=tfm*60000;bs=bars(m1,tfm);atr=atrs(bs)
 idx={b[0]:i for i,b in enumerate(bs)}
 # Precompute each forming TF candle's open and running extremes once. This avoids
 # repeatedly rescanning up to 240 M1 rows for every threshold.
 forming=[]; bucket=None; tf_open=run_hi=run_lo=None
 for t,o,h,l,c in m1:
  b=t//tfms*tfms
  if b!=bucket: bucket=b;tf_open=o;run_hi=h;run_lo=l
  else: run_hi=max(run_hi,h);run_lo=min(run_lo,l)
  forming.append((bucket,tf_open,run_hi,run_lo))
 split1=START+int((END-START)*.6);split2=START+int((END-START)*.8)
 outputs=[]
 for threshold in THRESHOLDS:
  trades=[];active_until=-1
  for i,x in enumerate(m1):
   t,o,h,l,c=x
   if t<START or t>=END or i<=active_until:continue
   bucket,tf_open,run_hi,run_lo=forming[i];pi=idx.get(bucket-tfms)
   if pi is None or not math.isfinite(atr[pi]) or atr[pi]<=0:continue
   # Impulse is the forming TF close-to-open displacement at this completed M1 close.
   direction=1 if c>tf_open else (-1 if c<tf_open else 0)
   if not direction or abs(c-tf_open)<threshold*atr[pi]:continue
   entry_i=i+1
   if entry_i>=len(m1):continue
   entry=m1[entry_i][1]
   stop=run_lo-SL_BUFFER*atr[pi] if direction==1 else run_hi+SL_BUFFER*atr[pi]
   risk=direction*(entry-stop)
   if risk<=0:continue
   target=entry+direction*risk*RR
   exit_px=None;reason="end_of_data";exit_i=len(m1)-1
   for k in range(entry_i,len(m1)):
    _,op,hi,lo,cl=m1[k]
    if direction==1:
     if op<=stop:exit_px=op;reason="stop_gap"
     elif lo<=stop:exit_px=stop;reason="stop"
     elif op>=target:exit_px=op;reason="target_gap"
     elif hi>=target:exit_px=target;reason="target"
    else:
     if op>=stop:exit_px=op;reason="stop_gap"
     elif hi>=stop:exit_px=stop;reason="stop"
     elif op<=target:exit_px=op;reason="target_gap"
     elif lo<=target:exit_px=target;reason="target"
    if exit_px is not None:exit_i=k;break
   if exit_px is None:exit_px=m1[exit_i][4]
   gross=direction*(exit_px-entry)/entry*10000
   net=gross-2*(FEE+SLIP)
   trades.append({"entry_ms":m1[entry_i][0],"exit_ms":m1[exit_i][0],"impulse_ms":t,
    "direction":"long" if direction==1 else "short","entry":entry,"exit":exit_px,"reason":reason,
    "gross_bps":gross,"net_bps":net,"stress7_net_bps":gross-2*(FEE+7)})
   active_until=exit_i
  row={"symbol":symbol,"timeframe":tf,"impulse_atr":threshold}
  for period,lo,hi in (("train",START,split1),("validation",split1,split2),("oos",split2,END)):
   subset=[z for z in trades if lo<=z["impulse_ms"]<hi and z["exit_ms"]<hi]
   m=metrics(subset)
   for k,v in m.items():row[period+"_"+k]=v
   stress=metrics([dict(z,net_bps=z["stress7_net_bps"]) for z in subset])
   for k in ("trades","pf","net_bps","expectancy_bps","max_drawdown_bps"):row[period+"_stress7_"+k]=stress[k]
  outputs.append(row)
 out=Path(out_dir);out.mkdir(parents=True,exist_ok=True)
 outputs.sort(key=lambda z:(z["validation_pf"],z["validation_net_bps"]),reverse=True)
 with (out/f"{symbol}_{tf}_impulse_strength.csv").open("w",newline="") as f:
  w=csv.DictWriter(f,fieldnames=list(outputs[0]));w.writeheader();w.writerows(outputs)
 manifest={"symbol":symbol,"timeframe":tf,"start_utc":"2023-11-01T00:00:00Z","end_utc_exclusive":"2026-11-01T00:00:00Z",
 "thresholds_atr":THRESHOLDS,"threshold_count":len(THRESHOLDS),"atr_period":ATR_PERIOD,"sl_buffer_atr":SL_BUFFER,
 "rr":RR,"fee_bps_per_side":FEE,"slippage_bps_per_side":SLIP,"stress_slippage_bps_per_side":7,
 "m1_rows":len(m1),"m1_gap_count":len(gaps),"timeframe_bars":len(bs),"split_ms":[START,split1,split2,END],
 "source_files":[{"name":p.name,"sha256":sha(p)} for p in files],
 "method":"At first completed M1 candle where forming same-timeframe candle close-to-open displacement reaches threshold × prior completed TF ATR, enter at next M1 open; stop beyond running opposite impulse extreme plus 0.2 ATR; TP 2R; one position per threshold until exit; stop-first; no retracement or other filters."}
 (out/f"{symbol}_{tf}_impulse_manifest.json").write_text(json.dumps(manifest,indent=2))
 print(f"{symbol} {tf}: {len(outputs)} thresholds complete; M1 rows={len(m1)}; gaps={len(gaps)}")
 for r in outputs[:5]:print(f"ATR {r['impulse_atr']:.1f} | val PF {r['validation_pf']:.3f} n={r['validation_trades']} | OOS PF {r['oos_pf']:.3f} n={r['oos_trades']} | OOS stress PF {r['oos_stress7_pf']:.3f}")

def main():
 p=argparse.ArgumentParser();p.add_argument("--symbol",required=True,choices=["BTCUSDT","ETHUSDT"])
 p.add_argument("--timeframe",required=True,choices=sorted(TFS));p.add_argument("--data-dir",default="/tmp/binance")
 p.add_argument("--output-dir",default="research-output");a=p.parse_args();run(a.symbol,a.timeframe,a.data_dir,a.output_dir)
if __name__=="__main__":main()
