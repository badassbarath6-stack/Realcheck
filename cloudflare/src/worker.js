import { STRATEGIES } from "../../config/strategies.js";
import { PF_RANKINGS } from "../../config/pf-rankings.js";

const BINANCE = "https://fapi.binance.com";
const DEFAULT_SYMBOLS = ["BTCUSDT", "ETHUSDT"];

function json(data, status = 200) {
  return new Response(JSON.stringify(data), { status, headers: { "content-type": "application/json" } });
}
function ratio(a, b) { return b === 0 ? 0 : a / b; }
function candle(k) {
  return { openTime:+k[0], open:+k[1], high:+k[2], low:+k[3], close:+k[4], volume:+k[5], closeTime:+k[6] };
}
function tr(c, previous) {
  return Math.max(c.high-c.low, Math.abs(c.high-previous.close), Math.abs(c.low-previous.close));
}
function wilder(values, period) {
  let value=null, count=0;
  for (const x of values) {
    if (x===null || !Number.isFinite(x)) continue;
    value=value===null?x:((value*(period-1))+x)/period;
    count++;
  }
  return count>=period?value:null;
}
export function indicatorSnapshot(history,current,periods) {
  const bars=[...history,current], n=bars.length;
  const trValues=Array(n).fill(null), plus=Array(n).fill(null), minus=Array(n).fill(null);
  const gains=Array(n).fill(null), losses=Array(n).fill(null);
  for(let i=1;i<n;i++){
    const b=bars[i],p=bars[i-1];
    trValues[i]=tr(b,p);
    const up=b.high-p.high,down=p.low-b.low;
    plus[i]=up>down&&up>0?up:0;
    minus[i]=down>up&&down>0?down:0;
    const delta=b.close-p.close;
    gains[i]=Math.max(delta,0);losses[i]=Math.max(-delta,0);
  }
  const atrPrior={};
  for(const period of periods) atrPrior[period]=wilder(trValues.slice(0,-1),period);
  const avgGain=wilder(gains,14),avgLoss=wilder(losses,14);
  const rsi=avgGain===null||avgLoss===null?null:(avgLoss===0?100:100-100/(1+avgGain/avgLoss));
  const atr14=wilder(trValues,14),pdm=wilder(plus,14),mdm=wilder(minus,14);
  let adx=null;
  if(atr14!==null&&pdm!==null&&mdm!==null&&atr14>0){
    const pdi=100*pdm/atr14,mdi=100*mdm/atr14,den=pdi+mdi;
    const dx=den===0?null:100*Math.abs(pdi-mdi)/den;
    const priorDx=[];
    for(let i=1;i<n-1;i++){
      const a=wilder(trValues.slice(0,i+1),14);
      const p=wilder(plus.slice(0,i+1),14),m=wilder(minus.slice(0,i+1),14);
      if(a===null||p===null||m===null||a===0){priorDx.push(null);continue;}
      const pi=100*p/a,mi=100*m/a,dd=pi+mi;
      priorDx.push(dd===0?null:100*Math.abs(pi-mi)/dd);
    }
    adx=wilder([...priorDx,dx],14);
  }
  return {atrPrior,adx,rsi};
}
export function selectLiveHour(hourly, now) {
  return hourly.filter(x=>x.openTime<=now && x.closeTime>=now).at(-1) || null;
}
export function completedMinuteBars(minutes, now) {
  return minutes.filter(x=>x.closeTime<now).sort((a,b)=>a.openTime-b.openTime);
}
export function latestCompletedMinuteBar(minutes, now) {
  return completedMinuteBars(minutes,now).at(-1) || null;
}
export function impulseGroupKey(symbol, impulseOpenTime) {
  return symbol+":"+impulseOpenTime;
}
export function structuralTradePlan(entry, setup, cfg) {
  const multiplier=1.0; // User-confirmed structural stop multiplier.
  const targetR=cfg.rr;
  const stop=setup.direction==="LONG"
    ? entry-(entry-setup.impulseLow)*multiplier
    : entry+(setup.impulseHigh-entry)*multiplier;
  const risk=Math.abs(entry-stop);
  if (!(risk>0) || !(targetR>0)) return null;
  const target=setup.direction==="LONG" ? entry+risk*targetR : entry-risk*targetR;
  return {stop,target,risk,stopMultiplier:multiplier,targetR};
}
export function detectImpulse(bar, history, cfg, indicators) {
  const volatility=indicators?.atrPrior?.[cfg.atrPeriod];
  const adx=indicators?.adx, rsi=indicators?.rsi;
  if (volatility===null||volatility===undefined||volatility<=0||adx===null||adx===undefined) return null;
  if(adx<cfg.adxMin||adx>cfg.adxMax||bar.close===bar.open) return null;
  const direction=bar.close>bar.open?"LONG":"SHORT";
  if(bar.high-bar.low<volatility*cfg.impulseAtr) return null;
  if(cfg.rsiMode==="exact"){
    if(direction==="LONG"&&!(rsi!==null&&rsi>=50&&rsi<=70))return null;
    if(direction==="SHORT"&&!(rsi!==null&&rsi>=30&&rsi<=50))return null;
  }else if(cfg.rsiMode==="loose"){
    if(direction==="LONG"&&!(rsi!==null&&rsi>=50&&rsi<=75))return null;
    if(direction==="SHORT"&&!(rsi!==null&&rsi>=25&&rsi<=50))return null;
  }else if(cfg.rsiMode!=="none") throw new Error("Unknown RSI mode: "+cfg.rsiMode);
  const range=bar.high-bar.low;
  return {direction,atr:volatility,adx,rsi,range,impulseHigh:bar.high,impulseLow:bar.low,impulseOpenTime:bar.openTime,impulseCloseTime:bar.closeTime};
}
// Entry is a single retracement level from the approved CSV, not a retracement zone.
// Stop invalidation is checked before entry touch so a same-minute stop/entry overlap
// cannot be treated as a valid signal.
export function retracementResult(bar, setup, cfg) {
  const entryLevel=setup.direction==="LONG"
    ? setup.impulseHigh-setup.range*cfg.retracement
    : setup.impulseLow+setup.range*cfg.retracement;
  if (setup.direction==="LONG") {
    if (bar.low<=setup.impulseLow) return {invalid:true,reason:"BROKE_IMPULSE_LOW"};
    return bar.low<=entryLevel ? {trigger:true,entryReference:entryLevel,depth:cfg.retracement}:null;
  }
  if (bar.high>=setup.impulseHigh) return {invalid:true,reason:"BROKE_IMPULSE_HIGH"};
  return bar.high>=entryLevel ? {trigger:true,entryReference:entryLevel,depth:cfg.retracement}:null;
}
async function getKlines(symbol, interval, limit, base) {
  const url=new URL("/fapi/v1/klines",base||BINANCE);
  url.searchParams.set("symbol",symbol);
  url.searchParams.set("interval",interval);
  url.searchParams.set("limit",String(limit));
  const response=await fetch(url,{headers:{accept:"application/json"}});
  if (!response.ok) throw new Error("Market data "+symbol+" "+interval+": HTTP "+response.status);
  return (await response.json()).map(candle);
}
async function telegramAlert(env, selected) {
  if (!env.TELEGRAM_BOT_TOKEN || !env.TELEGRAM_CHAT_ID) return {sent:false,reason:"TELEGRAM_NOT_CONFIGURED"};
  const lines=[
    "IMPULSE RETRACER",
    selected.symbol+" | "+selected.direction,
    "Configuration: "+selected.configId+" | Top-100 rank: "+selected.rank,
    "PF: "+(Number.isFinite(selected.pf)?selected.pf.toFixed(3):"single qualifying configuration; PF comparison not needed"),
    "Impulse candle opened: "+new Date(selected.impulseOpenTime).toISOString(),
    "Impulse detected: "+new Date(selected.impulseDetectedAt).toISOString(),
    "Alert time: "+new Date(selected.alertTime).toISOString(),
    "Entry level touched (reference, not a fill): "+selected.entryReference,
    "Structural SL (1x): "+selected.stop,
    "Target ("+selected.targetR+"R): "+selected.target,
    "Retracement: "+(selected.depth*100).toFixed(1)+"%",
    "Use a fresh quote after this alert; do not assume the historical trigger level is still executable."
  ];
  const response=await fetch("https://api.telegram.org/bot"+env.TELEGRAM_BOT_TOKEN+"/sendMessage",{
    method:"POST",
    headers:{"content-type":"application/json"},
    body:JSON.stringify({chat_id:env.TELEGRAM_CHAT_ID,text:lines.join("\n")})
  });
  if (!response.ok) throw new Error("Telegram HTTP "+response.status);
  const payload=await response.json();
  if (!payload.ok) throw new Error("Telegram rejected alert");
  return {sent:true};
}
export default {
  async scheduled(event,env,ctx) { ctx.waitUntil(runMinute(Date.now(),env)); },
  async fetch(request,env) {
    const url=new URL(request.url);
    if (url.pathname==="/health") return json({
      ok:true,
      service:"Impulse Retracer",
      schedule:"every minute",
      enabledConfigurations:STRATEGIES.filter(x=>x.enabled).length,
      model:"single Top-100 model",
      impulseDetection:"hourly candle inspected every minute",
      entryEvaluation:"latest completed 1m candle",
      selection:"PF comparison only for multiple configurations completing in the same minute",
      alertPolicy:"one alert per symbol/hourly impulse"
    });
    if (url.pathname==="/admin/pf-rankings" && request.method==="GET") return json(PF_RANKINGS);
    return json({error:"Not found"},404);
  }
};
async function runMinute(now,env) {
  const symbols=(env.SYMBOLS||DEFAULT_SYMBOLS.join(",")).split(",").map(s=>s.trim().toUpperCase()).filter(Boolean);
  const state=env.STATE.get(env.STATE.idFromName("impulse-retracer-global"));
  const errors=[];
  const configs=STRATEGIES.filter(x=>x.enabled);
  for (const symbol of symbols) {
    try {
      const [hourly,minuteHistory]=await Promise.all([
        getKlines(symbol,"1h",100,env.BINANCE_API_BASE),
        getKlines(symbol,"1m",60,env.BINANCE_API_BASE)
      ]);
      const completedHours=hourly.filter(x=>x.closeTime<now);
      const liveHour=selectLiveHour(hourly,now);
      const latestMinute=latestCompletedMinuteBar(minuteHistory,now);
      if (completedHours.length<Math.max(...configs.map(x=>x.atrPeriod))+1 || !liveHour || !latestMinute) continue;

      // Indicators are recalculated against the forming H1 snapshot on every M1 execution.
      const indicators=indicatorSnapshot(completedHours,liveHour,[...new Set(configs.map(x=>x.atrPeriod))]);
      // On every one-minute invocation, evaluate the current H1 candle for all 100 configs.
      for (const cfg of configs) {
        const impulse=detectImpulse(liveHour,completedHours,cfg,indicators);
        if (impulse) {
          await state.fetch("https://state/setup",{
            method:"POST",
            headers:{"content-type":"application/json"},
            body:JSON.stringify({
              symbol,configId:cfg.id,rank:cfg.rank,pendingBars:cfg.pendingBars,...impulse,
              createdAt:now,
              detectedMinute:Math.floor(now/60000)*60000
            })
          });
        }
      }

      // Process only the newest completed M1 candle. Never backfill stale entry alerts.
      await state.fetch("https://state/candle",{
        method:"POST",
        headers:{"content-type":"application/json"},
        body:JSON.stringify({symbol,candle:latestMinute,strategies:configs})
      });
    } catch(e) {
      errors.push({symbol,error:String(e.message||e)});
    }
  }

  // All candidates from this one-minute execution are grouped by impulse.
  const response=await state.fetch("https://state/flush",{
    method:"POST",
    headers:{"content-type":"application/json"},
    body:JSON.stringify({now,rankings:PF_RANKINGS})
  });
  const payload=await response.json();
  for (const selected of (payload.selected||[])) {
    let result;
    try { result=await telegramAlert(env,{...selected,alertTime:now}); }
    catch(e) { result={sent:false,error:String(e.message||e)}; }
    await state.fetch("https://state/alert-result",{
      method:"POST",
      headers:{"content-type":"application/json"},
      body:JSON.stringify({candidateId:selected.candidateId,impulseKey:selected.impulseKey,alertResult:result,alertTime:now})
    });
  }
  if (errors.length) console.log(JSON.stringify({type:"minute_errors",now,errors}));
}
export class ImpulseState {
  constructor(ctx,env) { this.ctx=ctx; this.env=env; }
  async fetch(request) {
    const url=new URL(request.url);
    if (request.method!=="POST") return json({error:"POST required"},405);
    const body=await request.json();
    if (url.pathname==="/setup") return this.addSetup(body);
    if (url.pathname==="/candle") return this.processCandle(body);
    if (url.pathname==="/flush") return this.flush(body);
    if (url.pathname==="/alert-result") return this.alertResult(body);
    return json({error:"Unknown state route"},404);
  }
  async read(key,fallback) { return (await this.ctx.storage.get(key))??fallback; }
  async addSetup(s) {
    const locks=await this.read("impulseLocks",{});
    const groupKey=impulseGroupKey(s.symbol,s.impulseOpenTime);
    if (locks[groupKey]) return json({ok:false,reason:"IMPULSE_ALREADY_ALERTED"});
    const setups=await this.read("setups",{});
    const key=s.symbol+":"+s.configId+":"+s.impulseOpenTime;
    if (!setups[key]) {
      setups[key]={
        ...s,
        groupKey,
        active:true,
        lastCandleTime:(s.detectedMinute??Math.floor(s.createdAt/60000)*60000)-60000,
        expiresAt:s.impulseOpenTime+(s.pendingBars+1)*60*60*1000,
        triggered:false
      };
      await this.ctx.storage.put("setups",setups);
    }
    return json({ok:true});
  }
  async processCandle(input) {
    const setups=await this.read("setups",{});
    const pending=await this.read("pending",[]);
    const seen=await this.read("seen",{});
    const locks=await this.read("impulseLocks",{});
    const configs=Object.fromEntries(input.strategies.map(s=>[s.id,s]));
    let changed=false;
    for (const [key,s] of Object.entries(setups)) {
      const bar=input.candle;
      if (!s.active || s.symbol!==input.symbol || bar.openTime<=s.lastCandleTime) continue;
      s.lastCandleTime=bar.openTime;
      if(bar.openTime>=s.expiresAt){s.active=false;s.expiredAt=bar.openTime;continue;}
      changed=true;
      if (locks[s.groupKey]) { s.active=false; continue; }
      const cfg=configs[s.configId];
      if (!cfg) continue;
      const result=retracementResult(bar,s,cfg);
      if (result&&result.invalid) {
        s.active=false;
        s.invalidReason=result.reason;
        s.invalidAt=bar.closeTime;
        continue;
      }
      if (result&&result.trigger&&!s.triggered) {
        const candidateId=s.groupKey+":"+s.configId+":"+bar.openTime;
        if (!seen[candidateId]) {
          const plan=structuralTradePlan(result.entryReference,s,cfg);
          if (!plan) continue;
          pending.push({
            candidateId,
            impulseKey:s.groupKey,
            triggerMinute:bar.openTime,
            symbol:s.symbol,
            configId:s.configId,
            rank:s.rank,
            direction:s.direction,
            impulseOpenTime:s.impulseOpenTime,
            impulseDetectedAt:s.createdAt,
            triggerTime:bar.closeTime,
            entryReference:result.entryReference,
            depth:result.depth,
            ...plan
          });
          seen[candidateId]=true;
          s.triggered=true;
        }
      }
    }
    if (changed) await this.ctx.storage.put("setups",setups);
    if (pending.length) await this.ctx.storage.put("pending",pending);
    if (Object.keys(seen).length) await this.ctx.storage.put("seen",seen);
    return json({ok:true});
  }
  async flush(input) {
    const pending=await this.read("pending",[]);
    const locks=await this.read("impulseLocks",{});
    const groups=new Map();
    for (const candidate of pending) {
      if (locks[candidate.impulseKey]) continue;
      const key=candidate.impulseKey;
      if (!groups.has(key)) groups.set(key,[]);
      groups.get(key).push(candidate);
    }
    const selected=[];
    const skipped=[];
    for (const [impulseKey,allCandidates] of groups) {
      // Never compare configurations whose entry triggers occurred in different
      // M1 minutes. If invocations overlap, resolve the earliest pending minute;
      // PF competition is restricted to that exact minute only.
      const earliestMinute=Math.min(...allCandidates.map(c=>c.triggerMinute));
      const candidates=allCandidates.filter(c=>c.triggerMinute===earliestMinute);
      let winner=null;
      if (candidates.length===1) {
        winner={...candidates[0],pf:null};
      } else {
        const scored=candidates.map(c=>({candidate:c,ranking:input.rankings[c.configId]}));
        if (scored.some(x=>!x.ranking || x.ranking.validated!==true || !Number.isFinite(Number(x.ranking.profitFactor)) || Number(x.ranking.profitFactor)<=0)) {
          skipped.push({impulseKey,triggerMinute:earliestMinute,reason:"MULTIPLE_CONFIGS_REQUIRE_VALIDATED_PF_FOR_EVERY_CANDIDATE",configIds:candidates.map(c=>c.configId)});
          continue;
        }
        scored.sort((a,b)=>
          Number(b.ranking.profitFactor)-Number(a.ranking.profitFactor) ||
          Number(b.ranking.trades||0)-Number(a.ranking.trades||0) ||
          a.candidate.rank-b.candidate.rank
        );
        winner={...scored[0].candidate,pf:Number(scored[0].ranking.profitFactor)};
      }
      locks[impulseKey]={candidateId:winner.candidateId,lockedAt:input.now,status:"ALERTING"};
      selected.push(winner);
    }
    await this.ctx.storage.put("impulseLocks",locks);
    // Current-cycle candidates are consumed; no delayed comparison on later minutes.
    await this.ctx.storage.put("pending",[]);
    return json({selected,skipped,queued:pending.length});
  }
  async alertResult(input) {
    const history=await this.read("alerts",[]);
    history.push({...input,recordedAt:Date.now()});
    await this.ctx.storage.put("alerts",history.slice(-5000));
    const locks=await this.read("impulseLocks",{});
    if (input.impulseKey && input.alertResult && input.alertResult.sent===true) {
      locks[input.impulseKey]={...(locks[input.impulseKey]||{}),status:"ALERTED",alertedAt:input.alertTime};
      const setups=await this.read("setups",{});
      for (const s of Object.values(setups)) if (s.groupKey===input.impulseKey) s.active=false;
      await this.ctx.storage.put("setups",setups);
    } else if (input.impulseKey) {
      delete locks[input.impulseKey];
      const setups=await this.read("setups",{});
      for (const s of Object.values(setups)) if (s.groupKey===input.impulseKey && s.active) s.triggered=false;
      await this.ctx.storage.put("setups",setups);
    }
    await this.ctx.storage.put("impulseLocks",locks);
    return json({ok:true});
  }
}
