import test from "node:test";
import assert from "node:assert/strict";
import { evaluateMinimumTarget, pipSizeForSymbol } from "../cloudflare/src/min-target-gate.js";

test("accepts a target only when net target distance meets 8 pips", () => {
  const result = evaluateMinimumTarget({
    symbol:"BTCUSDT", side:"LONG", entryPrice:60000, targetPrice:60100,
    pipSize:1, minTargetPips:8, feeBpsPerSide:0, slippageBpsPerSide:0
  });
  assert.equal(result.eligible,true);
  assert.equal(result.netTargetPips,100);
});

test("rejects targets below 8 pips after round-trip costs", () => {
  const result = evaluateMinimumTarget({
    symbol:"BTCUSDT", side:"LONG", entryPrice:60000, targetPrice:60050,
    pipSize:1, minTargetPips:8, feeBpsPerSide:7.5, slippageBpsPerSide:2.5
  });
  assert.equal(result.eligible,false);
  assert.ok(result.netTargetPips < 8);
  assert.deepEqual(result.reasons,["NET_TARGET_BELOW_MINIMUM"]);
});

test("rejects target on wrong side", () => {
  const result = evaluateMinimumTarget({
    symbol:"ETHUSDT", side:"LONG", entryPrice:3000, targetPrice:2990,
    pipSize:0.1
  });
  assert.equal(result.eligible,false);
  assert.deepEqual(result.reasons,["TARGET_NOT_IN_TRADE_DIRECTION"]);
});

test("fails closed when pip size is unknown", () => {
  assert.equal(pipSizeForSymbol("SOLUSDT"),null);
  const result = evaluateMinimumTarget({
    symbol:"SOLUSDT", side:"LONG", entryPrice:100, targetPrice:120, pipSize:null
  });
  assert.equal(result.eligible,false);
  assert.ok(result.reasons.includes("PIP_SIZE_REQUIRED"));
});

test("allows environment override for symbol pip size", () => {
  assert.equal(pipSizeForSymbol("BTCUSDT",{PIP_SIZE_BTCUSDT:"0.5"}),0.5);
});
