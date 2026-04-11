import { OptionContract, Strategy, PayoffPoint } from './types';

function findLeg(
  contracts: OptionContract[],
  type: 'Call' | 'Put',
  minDelta: number,
  maxDelta: number
): OptionContract | null {
  const candidates = contracts
    .filter(
      (c) =>
        c.type === type &&
        c.delta >= minDelta &&
        c.delta <= maxDelta &&
        c.vol > 1 &&
        c.bid > 0
    )
    .sort((a, b) => b.vol - a.vol);
  return candidates[0] ?? null;
}

function makeId(type: string, symbol: string): string {
  // Simple deterministic id without btoa to avoid SSR issues
  return `${type}-${symbol}`.replace(/[^a-zA-Z0-9-]/g, '_');
}

export function generateStrategies(
  contracts: OptionContract[],
  spotPrices: Record<string, number>
): Strategy[] {
  const strategies: Strategy[] = [];

  // Group by underlying + expiry
  const groups = new Map<string, OptionContract[]>();
  for (const contract of contracts) {
    const key = `${contract.underlying}|${contract.expiry}`;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key)!.push(contract);
  }

  for (const [key, group] of groups) {
    const [underlying] = key.split('|');
    const spot = spotPrices[`${underlying}USDT`];
    if (!spot) continue;

    const dte = group[0].dte;
    const expiry = group[0].expiry;

    // --- A. Long Call (Directional Bullish) ---
    const longCallOption = findLeg(group, 'Call', 0.45, 0.65);
    if (longCallOption) {
      const premium = longCallOption.ask;
      if (premium > 0) {
        strategies.push({
          id: makeId('LongCall', longCallOption.symbol),
          type: 'Long Call',
          symbol: `${underlying} Long Call ${longCallOption.strike}`,
          underlying,
          expiry,
          dte,
          spot,
          legs: [{ side: 'Buy', option: longCallOption, price: premium }],
          credit: -premium,
          maxRisk: premium,
          netDelta: longCallOption.delta,
          netGamma: longCallOption.gamma,
          netTheta: longCallOption.theta,
          netVega: longCallOption.vega,
          breakEven: longCallOption.strike + premium,
          probProfit: (1 - longCallOption.delta) * 100,
        });
      }
    }

    // --- B. Long Put (Directional Bearish) ---
    const longPutOption = findLeg(group, 'Put', -0.65, -0.45);
    if (longPutOption) {
      const premium = longPutOption.ask;
      if (premium > 0) {
        strategies.push({
          id: makeId('LongPut', longPutOption.symbol),
          type: 'Long Put',
          symbol: `${underlying} Long Put ${longPutOption.strike}`,
          underlying,
          expiry,
          dte,
          spot,
          legs: [{ side: 'Buy', option: longPutOption, price: premium }],
          credit: -premium,
          maxRisk: premium,
          netDelta: longPutOption.delta,
          netGamma: longPutOption.gamma,
          netTheta: longPutOption.theta,
          netVega: longPutOption.vega,
          breakEven: longPutOption.strike - premium,
          probProfit: (1 - Math.abs(longPutOption.delta)) * 100,
        });
      }
    }

    // --- C. Long Straddle (Volatility Play) ---
    const atmCall = findLeg(group, 'Call', 0.45, 0.55);
    if (atmCall) {
      const atmPut = group.find(
        (c) => c.strike === atmCall.strike && c.type === 'Put' && c.vol > 1 && c.bid > 0
      );
      if (atmPut) {
        const cost = atmCall.ask + atmPut.ask;
        if (cost > 0) {
          strategies.push({
            id: makeId('LongStraddle', atmCall.symbol),
            type: 'Long Straddle',
            symbol: `${underlying} Straddle ${atmCall.strike}`,
            underlying,
            expiry,
            dte,
            spot,
            legs: [
              { side: 'Buy', option: atmCall, price: atmCall.ask },
              { side: 'Buy', option: atmPut, price: atmPut.ask },
            ],
            credit: -cost,
            maxRisk: cost,
            netDelta: atmCall.delta + atmPut.delta,
            netGamma: atmCall.gamma + atmPut.gamma,
            netTheta: atmCall.theta + atmPut.theta,
            netVega: atmCall.vega + atmPut.vega,
            breakEven: [atmCall.strike - cost, atmCall.strike + cost],
            probProfit: 40,
          });
        }
      }
    }
  }

  return strategies.sort((a, b) => a.dte - b.dte);
}

export function calculatePayoff(strategy: Strategy, numPoints = 300): PayoffPoint[] {
  const xMin = strategy.spot * 0.75;
  const xMax = strategy.spot * 1.25;

  return Array.from({ length: numPoints }, (_, i) => {
    const price = xMin + (i / (numPoints - 1)) * (xMax - xMin);
    let pnl = 0;

    for (const leg of strategy.legs) {
      const { strike, type } = leg.option;
      const intrinsic =
        type === 'Call' ? Math.max(price - strike, 0) : Math.max(strike - price, 0);
      pnl += leg.side === 'Buy' ? intrinsic - leg.price : leg.price - intrinsic;
    }

    return {
      price,
      pnl,
      positivePnl: Math.max(pnl, 0),
      negativePnl: Math.min(pnl, 0),
    };
  });
}
