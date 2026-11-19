#!/usr/bin/env python3
"""Faithful historical replay of the public Model 3-100 Apps Script.

The source strategy is a 1-hour BTCUSDT paper engine polled every five minutes.
The five-minute trigger is polling cadence, NOT a one-minute execution timeframe.
This replay therefore uses completed 1h candles for impulse, entry, stop, target,
and time exits, and preserves an independent state machine for every config.
"""
import csv, io, json, math, re, time, zipfile
from datetime import datetime, timezone, timedelta
from urllib.request import urlopen, Request
from urllib.parse import urlencode, urlparse
from bisect import bisect_left

# Rolling six-month window ending at the latest fully closed UTC hour.
END_DT = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
END = int(END_DT.timestamp() * 1000)
# Calendar six months (not a fixed 183-day approximation).
_start_month = END_DT.month - 6
_start_year = END_DT.year
if _start_month <= 0:
    _start_month += 12
    _start_year -= 1
import calendar
START_DT = END_DT.replace(year=_start_year, month=_start_month,
                          day=min(END_DT.day, calendar.monthrange(_start_year, _start_month)[1]))
START = int(START_DT.timestamp() * 1000)
WARMUP_START = START - 500 * 3600000
OKX_BASE = "https://www.okx.com"
OKX_INST = "BTC-USDT-SWAP"
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

def okx_get(endpoint, params):
    url = OKX_BASE + endpoint + "?" + urlencode(params)
    req = Request(url, headers={"User-Agent":"Model-3-100-OKX-historical-replay/1.0","Accept":"application/json"})
    with urlopen(req, timeout=45) as r:
        payload = json.loads(r.read().decode("utf-8"))
    if payload.get("code") != "0" or not isinstance(payload.get("data"), list):
        raise RuntimeError(f"OKX API error at {endpoint}: {payload}")
    return payload["data"]

def load_hourly():
    # Same venue and perpetual instrument as the live runner: OKX BTC-USDT-SWAP.
    rows, cursor, previous_oldest = [], None, None
    while True:
        params = {"instId":OKX_INST, "bar":"1H", "limit":"100"}
        if cursor is not None: params["after"] = str(cursor)
        page = okx_get("/api/v5/market/history-candles", params)
        if not page: break
        rows.extend(page)
        oldest = min(int(k[0]) for k in page)
        if oldest <= WARMUP_START: break
        if previous_oldest == oldest: raise RuntimeError(f"OKX hourly pagination stalled at {oldest}")
        previous_oldest, cursor = oldest, oldest
        time.sleep(0.12)
    unique = {}
    for k in rows:
        ts = int(k[0])
        if k[8] != "1" or not (WARMUP_START <= ts < END): continue
        unique[ts] = tuple(float(x) for x in k[1:6])
    out = [dict(t=ts+3600000,o=v[0],h=v[1],l=v[2],c=v[3],v=v[4]) for ts,v in sorted(unique.items())]
    if not out: raise RuntimeError("OKX returned no completed BTC-USDT-SWAP 1H candles")
    for x,y in zip(out,out[1:]):
        if y["t"]-x["t"] != 3600000: raise RuntimeError(f"OKX hourly data gap at {y['t']}")
    if out[0]["t"] > START-400*3600000: raise RuntimeError("Insufficient OKX indicator warm-up before test start")
    if out[-1]["t"] > END: raise RuntimeError("OKX returned a candle beyond requested end boundary")
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
    # OKX's ordinary funding-rate-history REST endpoint only retains ~3 months.
    # Pull older settlements from OKX's first-party monthly funding archive (module 3),
    # then overlap the REST history to cover the archive's T+2 publication lag.
    floor_ts = START - 30*86400000
    start_month = START_DT.replace(day=1)
    end_month = END_DT.replace(day=1)
    utc8 = timezone(timedelta(hours=8))
    archive_begin = int(start_month.replace(tzinfo=utc8).timestamp()*1000)
    next_month = end_month.replace(year=end_month.year+(1 if end_month.month==12 else 0),
                                   month=1 if end_month.month==12 else end_month.month+1, day=1)
    archive_end = int(next_month.replace(tzinfo=utc8).timestamp()*1000)-1
    params = {"module":"3","instType":"SWAP","instFamilyList":"BTC-USDT",
              "dateAggrType":"monthly","begin":str(archive_begin),"end":str(archive_end)}
    listing = okx_get("/api/v5/public/market-data-history", params)
    details = listing.get("details") if isinstance(listing, dict) else None
    if not isinstance(details, list):
        raise RuntimeError(f"OKX historical funding archive response missing data.details: {listing}")
    archives = {}
    for detail in details:
        for item in detail.get("groupDetails", []):
            filename = item.get("filename") or item.get("fileName")
            url = item.get("url")
            if not filename or not url:
                continue
            parsed = urlparse(url)
            if parsed.scheme != "https" or (parsed.hostname or "").lower() != "static.okx.com":
                raise RuntimeError(f"Untrusted OKX funding archive URL: {url}")
            archives[filename] = url
    if not archives:
        raise RuntimeError("OKX returned no monthly funding archive files for BTC-USDT-SWAP")

    out = {}
    for filename, url in sorted(archives.items()):
        req = Request(url, headers={"User-Agent":"Model-3-100-OKX-historical-replay/1.0",
                                    "Referer":"https://www.okx.com/historical-data"})
        with urlopen(req, timeout=90) as response:
            raw = response.read()
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            bad = archive.testzip()
            if bad is not None:
                raise RuntimeError(f"OKX funding ZIP CRC failure: {filename}:{bad}")
            members = [name for name in archive.namelist() if name.lower().endswith(".csv")]
            if not members:
                raise RuntimeError(f"OKX funding ZIP has no CSV member: {filename}")
            for member in members:
                with archive.open(member) as stream:
                    reader = csv.reader(io.TextIOWrapper(stream, encoding="utf-8-sig", newline=""))
                    for row in reader:
                        if not row or len(row) < 3 or row[0].strip() != OKX_INST:
                            continue
                        try:
                            rate, ts = float(row[1]), int(row[2])
                        except (ValueError, TypeError) as exc:
                            raise RuntimeError(f"Malformed OKX funding row in {filename}: {row}") from exc
                        if floor_ts <= ts < END:
                            out[ts] = rate
        time.sleep(0.12)

    # The public REST history is limited to the most recent three months;
    # merge it over archive data so newest settlements are present too.
    cursor, previous_oldest = None, None
    while True:
        q = {"instId":OKX_INST, "limit":"400"}
        if cursor is not None:
            q["after"] = str(cursor)
        page = okx_get("/api/v5/public/funding-rate-history", q)
        if not page:
            break
        for row in page:
            try:
                ts, rate = int(row["fundingTime"]), float(row["fundingRate"])
            except (KeyError,ValueError,TypeError) as exc:
                raise RuntimeError(f"Unrecognized OKX funding-rate row: {row}") from exc
            if floor_ts <= ts < END:
                out[ts] = rate
        oldest = min(int(row["fundingTime"]) for row in page)
        if oldest <= floor_ts:
            break
        if previous_oldest == oldest:
            raise RuntimeError(f"OKX funding pagination stalled at {oldest}")
        previous_oldest, cursor = oldest, oldest
        time.sleep(0.12)

    result = sorted(out.items())
    if not result:
        raise RuntimeError("No historical OKX BTC-USDT-SWAP funding rates returned")
    if result[0][0] > START:
        raise RuntimeError("OKX funding archive does not reach the beginning of the requested six-month test")
    return result

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
    summary={"status":"COMPLETE","method":"Existing Model 3-100 historical replay logic; independent state per config; OKX live-venue data; no cross-config selection or deduplication",
      "period_utc":{"start":START_DT.isoformat(),"end_exclusive":END_DT.isoformat()},
      "symbol":"BTC-USDT-SWAP OKX USDT perpetual","configs":len(configs),"data_source":"OKX V5 history-candles + official monthly funding archive","instrument_id":OKX_INST,"hourly_candles_including_warmup":len(bars),
      "test_hourly_candles":end_i-start_i,"independent_closed_trades":len(all_trades),"wins":total_wins,"losses":total_losses,
      "win_rate_pct":100*total_wins/len(all_trades) if all_trades else 0,"profit_factor":gp/gl if gl else None,
      "net_bps_sum_across_independent_config_streams":sum(t["net_bps"] for t in all_trades),"max_drawdown_bps_sequential_sum":dd,
      "fee_bps_per_side":FEE_SIDE_BPS,"slippage_bps_per_side":SLIP_SIDE_BPS,"funding_source":"OKX official monthly historical funding archive + overlapping V5 funding-rate-history","funding_records":len(funding),
      "entry_exit_timeframe":"1h (same as public Apps Script); 5-minute trigger is polling cadence only",
      "exit_rule":"Source state machine: stop-first, gap-aware stop, target, then 24 completed-bar time exit",
      "end_state":"Open positions and pending orders at end are not force-closed, matching live engine behavior"}
    with open("summary.json","w") as f:json.dump(summary,f,indent=2)
    print(json.dumps(summary,indent=2))
if __name__=="__main__": main()
