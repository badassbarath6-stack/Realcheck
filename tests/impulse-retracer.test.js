import test from "node:test";
import assert from "node:assert/strict";
import { STRATEGIES } from "../config/strategies.js";
import {
  selectLiveHour,
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
  const result=await (await state.fetch("https://state/flush",{method:"POST",body:JSON.stringify({now:3700000,rankings:{}})})).json();
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
  const result=await (await state.fetch("https://state/flush",{method:"POST",body:JSON.stringify({now:3700000,rankings})})).json();
  assert.equal(result.selected.length,1);
  assert.equal(result.selected[0].configId,"IR-T001");
  assert.equal(result.selected[0].pf,1.8);
  assert.equal(data.get("pending").length,0);
});
test("same impulse is locked across all configurations after successful alert",async()=>{
  const {state,data}=makeState();
  await state.ctx.storage.put("pending",[candidate("IR-T001",1)]);
  await state.fetch("https://state/flush",{method:"POST",body:JSON.stringify({now:3700000,rankings:{}})});
  await state.fetch("https://state/alert-result",{method:"POST",body:JSON.stringify({
    candidateId:"x",impulseKey:"BTCUSDT:3600000",alertTime:3700000,alertResult:{sent:true}
  })});
  const add=await (await state.fetch("https://state/setup",{method:"POST",body:JSON.stringify({
    symbol:"BTCUSDT",configId:"IR-T002",impulseOpenTime:3600000,createdAt:3720000,detectedMinute:3720000
  })})).json();
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
  const result=await (await state.fetch("https://state/flush",{method:"POST",body:JSON.stringify({now:3700000,rankings:{}})})).json();
  assert.equal(result.selected.length,2);
});
test("multiple same-minute candidates are withheld if any candidate lacks validated PF",async()=>{
  const {state}=makeState();
  await state.ctx.storage.put("pending",[
    candidate("IR-T001",1),
    candidate("IR-T002",2)
  ]);
  const result=await (await state.fetch("https://state/flush",{method:"POST",body:JSON.stringify({
    now:3700000,rankings:{"IR-T001":{profitFactor:1.5,validated:true,trades:100}}
  })})).json();
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

test("the active model contains exactly the 100 approved ranked configurations",()=>{
  assert.equal(STRATEGIES.length,100);
  assert.deepEqual(STRATEGIES.map(x=>x.rank),Array.from({length:100},(_,i)=>i+1));
  assert.equal(new Set(STRATEGIES.map(x=>x.id)).size,100);
  assert.ok(STRATEGIES.every(x=>x.timeframe==="1h" && x.rr===2));
});
