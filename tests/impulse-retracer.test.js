import test from "node:test";
import assert from "node:assert/strict";
import { STRATEGIES } from "../config/strategies.js";
import {
  selectLiveHour,
  detectImpulse,
  indicatorSnapshot,
  completedMinuteBars,
  latestCompletedMinuteBar,
  structuralTradePlan,
  ImpulseState
} from "../cloudflare/src/worker.js";

function makeState() {
  const data=new Map();
  const storage={
    get:async k=>data.get(k),
    put:async(k,v)=>data.set(k,structuredClone(v))
  };
  return {state:new ImpulseState({storage},{}),data};
}
async function post(state,path,body) {
  const request=new Request("https://state"+path,{
    method:"POST",
    headers:{"content-type":"application/json"},
    body:JSON.stringify(body)
  });
  return await (await state.fetch(request)).json();
}
function candidate(configId,rank,impulseKey="BTCUSDT:3600000",triggerMinute=3660000) {
  const symbol=impulseKey.split(":")[0];
  return {
    candidateId:impulseKey+":"+configId+":"+triggerMinute,
    impulseKey,triggerMinute,symbol,configId,rank,direction:"LONG",
    impulseOpenTime:3600000,impulseDetectedAt:3660000,triggerTime:triggerMinute+59999,
    entryReference:100,depth:0.75,stop:90,target:120,risk:10,targetR:2
  };
}

test("hourly impulse scan uses the currently forming H1 candle",()=>{
  const bars=[
    {openTime:0,closeTime:3599999,tag:"closed"},
    {openTime:3600000,closeTime:7199999,tag:"forming"}
  ];
  assert.equal(selectLiveHour(bars,4200000).tag,"forming");
});
test("M1 processing selects only the latest completed minute, not stale bars",()=>{
  const bars=[
    {openTime:60000,closeTime:119999,tag:"old"},
    {openTime:120000,closeTime:179999,tag:"latest"},
    {openTime:180000,closeTime:239999,tag:"forming"}
  ];
  assert.equal(latestCompletedMinuteBar(bars,200000).tag,"latest");
  assert.deepEqual(completedMinuteBars(bars,200000).map(x=>x.tag),["old","latest"]);
});
test("one completed configuration alerts without requiring a PF registry",async()=>{
  const {state,data}=makeState();
  await state.ctx.storage.put("pending",[candidate("IR-T001",1)]);
  const result=await post(state,"/flush",{now:3700000,rankings:{}});
  assert.equal(result.selected.length,1);
  assert.equal(result.selected[0].configId,"IR-T001");
  assert.equal(result.selected[0].pf,null);
  assert.equal(data.get("impulseLocks")["BTCUSDT:3600000"].status,"ALERTING");
});
test("multiple configurations completing in the same minute compete by validated PF",async()=>{
  const {state,data}=makeState();
  await state.ctx.storage.put("pending",[
    candidate("IR-T002",2),
    candidate("IR-T001",1)
  ]);
  const rankings={
    "IR-T002":{profitFactor:1.4,trades:200,validated:true},
    "IR-T001":{profitFactor:1.8,trades:100,validated:true}
  };
  const result=await post(state,"/flush",{now:3700000,rankings});
  assert.equal(result.selected.length,1);
  assert.equal(result.selected[0].configId,"IR-T001");
  assert.equal(result.selected[0].pf,1.8);
  assert.equal(data.get("pending").length,0);
});
test("same impulse is locked across all configurations after successful alert",async()=>{
  const {state,data}=makeState();
  await state.ctx.storage.put("pending",[candidate("IR-T001",1)]);
  await post(state,"/flush",{now:3700000,rankings:{}});
  await post(state,"/alert-result",{
    candidateId:"x",impulseKey:"BTCUSDT:3600000",alertTime:3700000,alertResult:{sent:true}
  });
  const add=await post(state,"/setup",{
    symbol:"BTCUSDT",configId:"IR-T002",impulseOpenTime:3600000,createdAt:3720000,detectedMinute:3720000
  });
  assert.equal(add.ok,false);
  assert.equal(add.reason,"IMPULSE_ALREADY_ALERTED");
  assert.equal(data.get("impulseLocks")["BTCUSDT:3600000"].status,"ALERTED");
});
test("a new hourly impulse can alert independently in the same execution cycle",async()=>{
  const {state}=makeState();
  await state.ctx.storage.put("pending",[
    candidate("IR-T001",1,"BTCUSDT:3600000"),
    candidate("IR-T003",3,"ETHUSDT:3600000")
  ]);
  const result=await post(state,"/flush",{now:3700000,rankings:{}});
  assert.equal(result.selected.length,2);
});
test("multiple same-minute candidates are withheld if any candidate lacks validated PF",async()=>{
  const {state}=makeState();
  await state.ctx.storage.put("pending",[
    candidate("IR-T001",1),
    candidate("IR-T002",2)
  ]);
  const result=await post(state,"/flush",{
    now:3700000,rankings:{"IR-T001":{profitFactor:1.5,validated:true,trades:100}}
  });
  assert.equal(result.selected.length,0);
  assert.equal(result.skipped[0].reason,"MULTIPLE_CONFIGS_REQUIRE_VALIDATED_PF_FOR_EVERY_CANDIDATE");
});
test("structural stop is 1x and Top-100 RR is applied as 2R",()=>{
  const plan=structuralTradePlan(160,{direction:"LONG",impulseLow:100,impulseHigh:200},{rr:2});
  assert.equal(plan.stop,100);
  assert.equal(plan.target,280);
  assert.equal(plan.risk,60);
  assert.equal(plan.targetR,2);
});
test("the active model contains exactly the 100 approved ranked configurations",()=>{
  assert.equal(STRATEGIES.length,100);
  assert.deepEqual(STRATEGIES.map(x=>x.rank),Array.from({length:100},(_,i)=>i+1));
  assert.equal(new Set(STRATEGIES.map(x=>x.id)).size,100);
  assert.ok(STRATEGIES.every(x=>x.timeframe==="1h" && x.rr===2));
});

test("a minute retracement touch completes one configuration and creates an immediate-cycle candidate",async()=>{
  const {state,data}=makeState();
  await post(state,"/setup",{
    symbol:"BTCUSDT",configId:"IR-T001",rank:1,direction:"LONG",
    range:100,impulseHigh:200,impulseLow:100,impulseOpenTime:3600000,
    createdAt:3660000,detectedMinute:3660000
  });
  await post(state,"/candle",{
    symbol:"BTCUSDT",
    candle:{openTime:3720000,closeTime:3779999,high:132,low:124,close:128},
    strategies:[{id:"IR-T001",rank:1,retracement:0.75,rr:2}]
  });
  const pending=data.get("pending");
  assert.equal(pending.length,1);
  assert.equal(pending[0].configId,"IR-T001");
  assert.equal(pending[0].entryReference,125);
  assert.equal(pending[0].target,175);
});
test("two configurations touched by the same M1 candle are compared together by PF",async()=>{
  const {state,data}=makeState();
  for (const [configId,rank] of [["IR-T001",1],["IR-T002",2]]) {
    await post(state,"/setup",{
      symbol:"BTCUSDT",configId,rank,direction:"LONG",
      range:100,impulseHigh:200,impulseLow:100,impulseOpenTime:3600000,
      createdAt:3660000,detectedMinute:3660000
    });
  }
  await post(state,"/candle",{
    symbol:"BTCUSDT",
    candle:{openTime:3720000,closeTime:3779999,high:132,low:124,close:128},
    strategies:[
      {id:"IR-T001",rank:1,retracement:0.75,rr:2},
      {id:"IR-T002",rank:2,retracement:0.75,rr:2}
    ]
  });
  assert.equal(data.get("pending").length,2);
  const result=await post(state,"/flush",{now:3780000,rankings:{
    "IR-T001":{profitFactor:1.7,trades:100,validated:true},
    "IR-T002":{profitFactor:1.9,trades:90,validated:true}
  }});
  assert.equal(result.selected.length,1);
  assert.equal(result.selected[0].configId,"IR-T002");
});

test("configurations triggered in different M1 minutes are not compared by PF",async()=>{
  const {state}=makeState();
  await state.ctx.storage.put("pending",[
    candidate("IR-T001",1,"BTCUSDT:3600000",3660000),
    candidate("IR-T002",2,"BTCUSDT:3600000",3720000)
  ]);
  const result=await post(state,"/flush",{now:3780000,rankings:{
    "IR-T001":{profitFactor:1.2,trades:100,validated:true},
    "IR-T002":{profitFactor:2.5,trades:100,validated:true}
  }});
  assert.equal(result.selected.length,1);
  assert.equal(result.selected[0].configId,"IR-T001");
  assert.equal(result.selected[0].pf,null);
});

test("ADX bounds reject impulses outside each configuration's band",()=>{
  const history=Array.from({length:40},(_,i)=>({
    openTime:i*3600000,closeTime:(i+1)*3600000-1,
    open:100+i,high:102+i,low:99+i,close:101+i
  }));
  const current={openTime:40*3600000,closeTime:41*3600000-1,open:140,high:160,low:139,close:159};
  const ind=indicatorSnapshot(history,current,[14,20,25]);
  assert.ok(ind.adx!==null);
  assert.equal(detectImpulse(current,history,{atrPeriod:14,impulseAtr:0.1,adxMin:ind.adx+1,adxMax:ind.adx+5,rsiMode:"none"},ind),null);
});
test("RSI exact and loose modes apply directional ranges",()=>{
  const history=Array.from({length:40},(_,i)=>({
    openTime:i*3600000,closeTime:(i+1)*3600000-1,
    open:100+i,high:102+i,low:99+i,close:101+i
  }));
  const current={openTime:40*3600000,closeTime:41*3600000-1,open:140,high:160,low:139,close:159};
  const ind=indicatorSnapshot(history,current,[14,20,25]);
  const cfg={atrPeriod:14,impulseAtr:0.1,adxMin:0,adxMax:100,rsiMode:"exact"};
  if(ind.rsi!==null && ind.rsi>70) assert.equal(detectImpulse(current,history,cfg,ind),null);
  const loose={...cfg,rsiMode:"loose"};
  if(ind.rsi!==null && ind.rsi>75) assert.equal(detectImpulse(current,history,loose,ind),null);
});
test("pending_bars expires at impulse-hour close plus the configured number of H1 bars",async()=>{
  const {state,data}=makeState();
  const impulseOpenTime=3600000, detectedMinute=3660000;
  await post(state,"/setup",{
    symbol:"BTCUSDT",configId:"IR-T001",rank:1,pendingBars:3,direction:"LONG",
    range:100,impulseHigh:200,impulseLow:100,impulseOpenTime,
    createdAt:detectedMinute,detectedMinute
  });
  const setups=data.get("setups");
  const setup=Object.values(setups)[0];
  assert.equal(setup.expiresAt,impulseOpenTime+4*3600000);
  await post(state,"/candle",{
    symbol:"BTCUSDT",candle:{openTime:setup.expiresAt,closeTime:setup.expiresAt+59999,high:150,low:120,close:130},
    strategies:[{id:"IR-T001",rank:1,retracement:0.75,rr:2}]
  });
  assert.equal(Object.values(data.get("setups"))[0].active,false);
  assert.equal(Object.values(data.get("setups"))[0].expiredAt,setup.expiresAt);
});
test("first eligible M1 candle is processed on the minute immediately after impulse detection",async()=>{
  const {state,data}=makeState();
  const detectedMinute=3660000;
  await post(state,"/setup",{
    symbol:"BTCUSDT",configId:"IR-T001",rank:1,pendingBars:3,direction:"LONG",
    range:100,impulseHigh:200,impulseLow:100,impulseOpenTime:3600000,
    createdAt:detectedMinute,detectedMinute
  });
  assert.equal(Object.values(data.get("setups"))[0].lastCandleTime,detectedMinute-60000);
  await post(state,"/candle",{
    symbol:"BTCUSDT",candle:{openTime:detectedMinute,closeTime:detectedMinute+59999,high:132,low:124,close:128},
    strategies:[{id:"IR-T001",rank:1,retracement:0.75,rr:2}]
  });
  assert.equal(data.get("pending").length,1);
});
