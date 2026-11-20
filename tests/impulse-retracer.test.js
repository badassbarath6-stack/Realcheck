import test from "node:test";
import assert from "node:assert/strict";
import { selectLiveHour, completedMinuteBars, structuralTradePlan, ImpulseState } from "../cloudflare/src/worker.js";

test("minute polling selects the currently forming hourly candle",()=>{
  const bars=[
    {openTime:0,closeTime:3599999,tag:"closed"},
    {openTime:3600000,closeTime:7199999,tag:"forming"}
  ];
  assert.equal(selectLiveHour(bars,4200000).tag,"forming");
});
test("minute polling excludes the still-forming 1m candle",()=>{
  const bars=[
    {openTime:60000,closeTime:119999,tag:"closed"},
    {openTime:120000,closeTime:179999,tag:"forming"}
  ];
  assert.deepEqual(completedMinuteBars(bars,150000).map(x=>x.tag),["closed"]);
});
test("a setup can process M1 candles immediately after detection, before H1 close",async()=>{
  const data=new Map();
  const storage={get:async k=>data.get(k),put:async(k,v)=>data.set(k,structuredClone(v))};
  const state=new ImpulseState({storage},{});
  await state.addSetup({symbol:"BTCUSDT",configId:"IR-A01",direction:"LONG",range:100,impulseHigh:200,impulseLow:100,impulseOpenTime:0,impulseCloseTime:3599999,createdAt:120000,detectedMinute:120000});
  await state.processCandle({symbol:"BTCUSDT",candle:{openTime:180000,closeTime:239999,high:190,low:160,close:180},strategies:[{id:"IR-A01",minRetrace:0.25,maxRetrace:0.62,confirmationLevel:0.5}]});
  assert.equal(data.get("setups")["BTCUSDT:IR-A01:0"].lastCandleTime,180000);
});
test("long structural stop is 1x and target is 5R",()=>{
  const plan=structuralTradePlan(160,{direction:"LONG",impulseLow:100,impulseHigh:200},{structuralStopMultiplier:1,targetR:5});
  assert.equal(plan.stop,100);
  assert.equal(plan.target,460);
  assert.equal(plan.risk,60);
});
test("short structural stop is 1x and target is 5R",()=>{
  const plan=structuralTradePlan(140,{direction:"SHORT",impulseLow:100,impulseHigh:200},{structuralStopMultiplier:1,targetR:5});
  assert.equal(plan.stop,200);
  assert.equal(plan.target,-160);
  assert.equal(plan.risk,60);
});
