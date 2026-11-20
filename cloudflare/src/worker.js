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
function atr(bars, period) {
  if (bars.length < period+1) return null;
  const values=[];
  for (let i=bars.length-period;i<bars.length;i++) values.push(tr(bars[i],bars[i-1]));
  return values.reduce((a,b)=>a+b,0)/period;
}
export function selectLiveHour(hourly, now) { return hourly.filter(x=>x.openTime<=now).at(-1) || null; }
export function completedMinuteBars(minutes, now) { return minutes.filter(x=>x.closeTime<now); }
export function structuralTradePlan(entry, setup, cfg) {
  const multiplier=cfg.structuralStopMultiplier ?? 1.0;
  const targetR=cfg.targetR ?? 5.0;
  const stop=setup.direction==="LONG"
    ? entry-(entry-setup.impulseLow)*multiplier
    : entry+(setup.impulseHigh-entry)*multiplier;
  const risk=Math.abs(entry-stop);
  if (!(risk>0)) return null;
  const target=setup.direction==="LONG" ? entry+risk*targetR : entry-risk*targetR;
  return {stop,target,risk,stopMultiplier:multiplier,targetR};
}
function detectImpulse(bar, history, cfg) {
  const volatility=atr(history,cfg.atrPeriod);
  if (!volatility || volatility<=0) return null;
  const range=bar.high-bar.low, body=Math.abs(bar.close-bar.open);
  if (range<volatility*cfg.minRangeAtr || body<volatility*cfg.minBodyAtr || ratio(body,range)<cfg.minBodyRatio || bar.close===bar.open) return null;
  return {
    direction:bar.close>bar.open?"LONG":"SHORT", atr:volatility, range:range,
    impulseHigh:bar.high, impulseLow:bar.low, impulseOpenTime:bar.openTime,
    impulseCloseTime:bar.closeTime, impulseId:cfg.id+":"+bar.openTime
  };
}
function retracementResult(bar, setup, cfg) {
  if (setup.direction==="LONG") {
    if (bar.low<setup.impulseLow) return {invalid:true,reason:"BROKE_IMPULSE_LOW"};
    const depth=ratio(setup.impulseHigh-bar.low,setup.range);
    const reclaimed=bar.close>setup.impulseHigh-setup.range*cfg.confirmationLevel;
    return depth>=cfg.minRetrace && depth<=cfg.maxRetrace && reclaimed
      ? {trigger:true,entryReference:bar.close,depth:depth}:null;
  }
  if (bar.high>setup.impulseHigh) return {invalid:true,reason:"BROKE_IMPULSE_HIGH"};
  const depth=ratio(bar.high-setup.impulseLow,setup.range);
  const reclaimed=bar.close<setup.impulseLow+setup.range*cfg.confirmationLevel;
  return depth>=cfg.minRetrace && depth<=cfg.maxRetrace && reclaimed
    ? {trigger:true,entryReference:bar.close,depth:depth}:null;
}
async function getKlines(symbol, interval, limit, base) {
  const url=new URL("/fapi/v1/klines",base||BINANCE);
  url.searchParams.set("symbol",symbol); url.searchParams.set("interval",interval); url.searchParams.set("limit",String(limit));
  const response=await fetch(url,{headers:{accept:"application/json"}});
  if (!response.ok) throw new Error("Market data "+symbol+" "+interval+": HTTP "+response.status);
  return (await response.json()).map(candle);
}
async function telegramAlert(env, selected) {
  if (!env.TELEGRAM_BOT_TOKEN || !env.TELEGRAM_CHAT_ID) return {sent:false,reason:"TELEGRAM_NOT_CONFIGURED"};
  const lines=[
    "IMPULSE RETRACER",selected.symbol+" | "+selected.direction,
    "Config: "+selected.configId+" | PF: "+selected.pf.toFixed(3),
    "Impulse candle opened: "+new Date(selected.impulseOpenTime).toISOString(),
    "Impulse detected: "+new Date(selected.impulseDetectedAt).toISOString(),
    "Alert batch: "+new Date(selected.alertTime).toISOString(),
    "Trigger reference (not a fill): "+selected.entryReference,
    "Structural SL (1x): "+selected.stop,
    "Target ("+selected.targetR+"R): "+selected.target,
    "Retracement: "+(selected.depth*100).toFixed(1)+"%",
    "Use a fresh quote after this alert; never backfill the earlier trigger price."
  ];
  const response=await fetch("https://api.telegram.org/bot"+env.TELEGRAM_BOT_TOKEN+"/sendMessage",{
    method:"POST",headers:{"content-type":"application/json"},
    body:JSON.stringify({chat_id:env.TELEGRAM_CHAT_ID,text:lines.join("\n")})
  });
  if (!response.ok) throw new Error("Telegram HTTP "+response.status);
  return {sent:true};
}
export default {
  async scheduled(event,env,ctx) { ctx.waitUntil(runMinute(event.scheduledTime||Date.now(),env)); },
  async fetch(request,env) {
    const url=new URL(request.url);
    if (url.pathname==="/health") return json({ok:true,service:"Impulse Retracer",schedule:"every minute",alertCycle:"every successful one-minute poll"});
    if (url.pathname==="/admin/pf-rankings" && request.method==="GET") return json(PF_RANKINGS);
    return json({error:"Not found"},404);
  }
};
async function runMinute(now,env) {
  const symbols=(env.SYMBOLS||DEFAULT_SYMBOLS.join(",")).split(",").map(s=>s.trim().toUpperCase()).filter(Boolean);
  const state=env.STATE.get(env.STATE.idFromName("impulse-retracer-global"));
  const errors=[];
  for (const symbol of symbols) {
    try {
      const pair=await Promise.all([
        getKlines(symbol,"1h",80,env.BINANCE_API_BASE),
        getKlines(symbol,"1m",60,env.BINANCE_API_BASE)
      ]);
      // Evaluate the currently forming H1 candle on every one-minute poll.
      // ATR history is strictly completed H1 candles; the live H1 snapshot is never
      // mistaken for a completed bar. A setup is frozen once per config/hour.
      const completedHours=pair[0].filter(x=>x.closeTime<now);
      const liveHour=selectLiveHour(pair[0],now);
      const minutes=completedMinuteBars(pair[1],now);
      if (completedHours.length<31 || !liveHour || !minutes.length) continue;
      const configs=STRATEGIES.filter(x=>x.enabled);
      for (const cfg of configs) {
        const impulse=detectImpulse(liveHour,completedHours,cfg);
        if (impulse) await state.fetch("https://state/setup",{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({symbol,configId:cfg.id,...impulse,createdAt:now,detectedMinute:Math.floor(now/60000)*60000})});
      }
      for (const m of minutes) {
        await state.fetch("https://state/candle",{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({symbol,candle:m,strategies:configs})});
      }
    } catch(e) { errors.push({symbol,error:String(e.message||e)}); }
  }
  {
    const response=await state.fetch("https://state/flush",{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({now,rankings:PF_RANKINGS})});
    const payload=await response.json();
    if (payload.selected) {
      let result;
      try { result=await telegramAlert(env,payload.selected); }
      catch(e) { result={sent:false,error:String(e.message||e)}; }
      await state.fetch("https://state/alert-result",{method:"POST",headers:{"content-type":"application/json"},body:JSON.stringify({candidateId:payload.selected.candidateId,alertResult:result,alertTime:now})});
    }
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
    const setups=await this.read("setups",{});
    const key=s.symbol+":"+s.configId+":"+s.impulseOpenTime;
    if (!setups[key]) setups[key]={...s,active:true,lastCandleTime:s.detectedMinute??Math.floor(s.createdAt/60000)*60000,triggered:false};
    await this.ctx.storage.put("setups",setups);
    return json({ok:true});
  }
  async processCandle(input) {
    const setups=await this.read("setups",{});
    const pending=await this.read("pending",[]);
    const seen=await this.read("seen",{});
    const configs=Object.fromEntries(input.strategies.map(s=>[s.id,s]));
    let changed=false;
    for (const [key,s] of Object.entries(setups)) {
      const bar=input.candle;
      // Only completed M1 bars strictly after the minute in which this live-H1
      // impulse snapshot was first detected may participate in retracement.
      if (!s.active || s.symbol!==input.symbol || bar.openTime<=s.lastCandleTime) continue;
      const cfg=configs[s.configId]; if (!cfg) continue;
      s.lastCandleTime=bar.openTime;
      const result=retracementResult(bar,s,cfg);
      if (result&&result.invalid) { s.active=false;s.invalidReason=result.reason;s.invalidAt=bar.closeTime;changed=true;continue; }
      if (result&&result.trigger&&!s.triggered) {
        const candidateId=key+":"+bar.openTime;
        if (!seen[candidateId]) {
          const plan=structuralTradePlan(result.entryReference,s,cfg);
          if (!plan) continue;
          pending.push({candidateId,symbol:s.symbol,configId:s.configId,direction:s.direction,impulseOpenTime:s.impulseOpenTime,impulseDetectedAt:s.createdAt,triggerTime:bar.closeTime,entryReference:result.entryReference,depth:result.depth,...plan});
          seen[candidateId]=true;s.triggered=true;changed=true;
        }
      }
    }
    if (changed) {
      await this.ctx.storage.put("setups",setups);
      await this.ctx.storage.put("pending",pending);
      await this.ctx.storage.put("seen",seen);
    }
    return json({ok:true});
  }
  async flush(input) {
    const pending=await this.read("pending",[]);
    // Each successful minute poll is its own selection cycle; no five-minute batch.
    const eligible=pending.filter(c=>Number.isFinite(Number(input.rankings[c.configId]?.profitFactor))&&Number(input.rankings[c.configId].profitFactor)>0&&input.rankings[c.configId].validated===true);
    eligible.sort((a,b)=>{
      const pa=input.rankings[a.configId],pb=input.rankings[b.configId];
      return pb.profitFactor-pa.profitFactor||(pb.trades||0)-(pa.trades||0)||a.triggerTime-b.triggerTime;
    });
    const selected=eligible[0]||null;
    // Resolve the current minute poll; do not defer stale candidates to a later poll.
    await this.ctx.storage.put("pending",[]);
    if (!selected) return json({selected:null,queued:pending.length,reason:"NO_PF_VALIDATED_CONFIGURATION"});
    return json({selected:{...selected,pf:input.rankings[selected.configId].profitFactor,alertTime:input.now}});
  }
  async alertResult(input) {
    const history=await this.read("alerts",[]);
    history.push({...input,recordedAt:Date.now()});
    await this.ctx.storage.put("alerts",history.slice(-5000));
    return json({ok:true});
  }
}