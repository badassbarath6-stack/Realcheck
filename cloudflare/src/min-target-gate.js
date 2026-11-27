/**
 * Common pre-alert minimum-target-distance gate.
 * Strategy adapters must supply their own native target; this module never
 * invents or changes an engine's entry, stop, target, or exit logic.
 */
export const DEFAULT_MIN_TARGET_PIPS = 8;
export const DEFAULT_PIP_SIZES = Object.freeze({
  BTCUSDT: 1.0, // configurable convention: 1 pip = $1.00
  ETHUSDT: 0.1  // configurable convention: 1 pip = $0.10
});

export function evaluateMinimumTarget({
  symbol,
  side,
  entryPrice,
  targetPrice,
  pipSize,
  minTargetPips = DEFAULT_MIN_TARGET_PIPS,
  feeBpsPerSide = 7.5,
  slippageBpsPerSide = 2.5
}) {
  const errors = [];
  if (typeof symbol !== "string" || !symbol.trim()) errors.push("INVALID_SYMBOL");
  if (side !== "LONG" && side !== "SHORT") errors.push("INVALID_SIDE");
  if (!Number.isFinite(entryPrice) || entryPrice <= 0) errors.push("INVALID_ENTRY");
  if (!Number.isFinite(targetPrice) || targetPrice <= 0) errors.push("INVALID_TARGET");
  if (!Number.isFinite(pipSize) || pipSize <= 0) errors.push("PIP_SIZE_REQUIRED");
  if (!Number.isFinite(minTargetPips) || minTargetPips < 0) errors.push("INVALID_MIN_TARGET_PIPS");
  if (!Number.isFinite(feeBpsPerSide) || feeBpsPerSide < 0) errors.push("INVALID_FEE_BPS");
  if (!Number.isFinite(slippageBpsPerSide) || slippageBpsPerSide < 0) errors.push("INVALID_SLIPPAGE_BPS");
  if (errors.length) return { eligible:false, reasons:errors };

  const signedMove = side === "LONG" ? targetPrice-entryPrice : entryPrice-targetPrice;
  if (!(signedMove > 0)) return { eligible:false, reasons:["TARGET_NOT_IN_TRADE_DIRECTION"] };

  const grossTargetPips = signedMove / pipSize;
  const roundTripCostPrice = entryPrice * 2 * (feeBpsPerSide + slippageBpsPerSide) / 10000;
  const roundTripCostPips = roundTripCostPrice / pipSize;
  const netTargetPips = grossTargetPips - roundTripCostPips;
  const eligible = netTargetPips >= minTargetPips;

  return {
    eligible,
    reasons: eligible ? [] : ["NET_TARGET_BELOW_MINIMUM"],
    grossTargetPips,
    roundTripCostPips,
    netTargetPips,
    minTargetPips,
    pipSize,
    roundTripCostPrice
  };
}

/**
 * Env-backed symbol mapping. Explicit per-symbol overrides take precedence.
 * Unknown symbols fail closed; they are never silently assigned a pip size.
 */
export function pipSizeForSymbol(symbol, env = {}) {
  const key = "PIP_SIZE_" + String(symbol).toUpperCase();
  const override = env[key];
  if (override !== undefined && override !== "") {
    const n = Number(override);
    return Number.isFinite(n) && n > 0 ? n : null;
  }
  return DEFAULT_PIP_SIZES[String(symbol).toUpperCase()] ?? null;
}
