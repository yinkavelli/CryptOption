export type OptionType = 'Call' | 'Put';
export type StrategyType = 'Long Call' | 'Long Put' | 'Long Straddle';
export type LegSide = 'Buy' | 'Sell';

export interface OptionContract {
  symbol: string;
  underlying: string;
  expiry: string; // YYYY-MM-DD
  dte: number;
  strike: number;
  type: OptionType;
  price: number;
  bid: number;
  ask: number;
  vol: number;
  iv: number;
  delta: number;
  gamma: number;
  theta: number;
  vega: number;
}

export interface StrategyLeg {
  side: LegSide;
  option: OptionContract;
  price: number;
}

export interface Strategy {
  id: string;
  type: StrategyType;
  symbol: string;
  underlying: string;
  expiry: string;
  dte: number;
  spot: number;
  legs: StrategyLeg[];
  credit: number; // negative = debit paid
  maxRisk: number;
  netDelta: number;
  netGamma: number;
  netTheta: number;
  netVega: number;
  breakEven: number | [number, number];
  probProfit: number;
}

export interface PayoffPoint {
  price: number;
  pnl: number;
  positivePnl: number;
  negativePnl: number;
}
