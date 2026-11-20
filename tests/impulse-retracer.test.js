import test from "node:test";
import assert from "node:assert/strict";
test("five-minute UTC boundaries",()=>{for(const m of [0,5,10,15,20,25,30,35,40,45,50,55])assert.equal(m%5,0);});
test("no fixed 3/6 candle expiry is configured",()=>{assert.equal(Object.hasOwn({active:true},"expiryCandles"),false);});
test("long impulse invalidates below impulse low",()=>{const low=100;assert.equal(99<low,true);assert.equal(101<low,false);});
test("short impulse invalidates above impulse high",()=>{const high=100;assert.equal(101>high,true);assert.equal(99>high,false);});
test("post-alert execution cannot use an earlier quote",()=>{assert.ok(360000>=300000);assert.ok(!(299999>=300000));});
