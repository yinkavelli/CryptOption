import { NextResponse } from 'next/server';

const TICKER_URL = 'https://eapi.binance.com/eapi/v1/ticker';
const MARK_URL = 'https://eapi.binance.com/eapi/v1/mark';

function parseExpiry(s: string): Date | null {
  if (s.length !== 6) return null;
  const year = 2000 + parseInt(s.slice(0, 2));
  const month = parseInt(s.slice(2, 4)) - 1;
  const day = parseInt(s.slice(4, 6));
  const d = new Date(year, month, day);
  if (isNaN(d.getTime())) return null;
  return d;
}

export async function GET() {
  try {
    const [tickerRes, markRes] = await Promise.all([
      fetch(TICKER_URL, { cache: 'no-store' }),
      fetch(MARK_URL, { cache: 'no-store' }),
    ]);

    if (!tickerRes.ok) {
      return NextResponse.json({
        contracts: [],
        error: `Ticker API returned ${tickerRes.status}`,
      });
    }

    const tickers: Array<{
      symbol: string;
      lastPrice: string;
      bidPrice: string;
      askPrice: string;
      volume: string;
    }> = await tickerRes.json();

    const marks: Array<{
      symbol: string;
      markIV: string;
      delta: string;
      gamma: string;
      theta: string;
      vega: string;
    }> = markRes.ok ? await markRes.json() : [];

    const markMap = new Map(marks.map((m) => [m.symbol, m]));
    const now = new Date();
    const MS_PER_DAY = 1000 * 60 * 60 * 24;
    const contracts = [];

    for (const t of tickers) {
      const parts = t.symbol.split('-');
      if (parts.length !== 4) continue;

      const [underlying, expiryStr, strikeStr, typeCode] = parts;
      const strike = parseFloat(strikeStr);
      if (isNaN(strike)) continue;

      const expiryDate = parseExpiry(expiryStr);
      if (!expiryDate) continue;

      const dte = Math.floor((expiryDate.getTime() - now.getTime()) / MS_PER_DAY);
      if (dte < 0) continue;

      const m = markMap.get(t.symbol);

      contracts.push({
        symbol: t.symbol,
        underlying,
        expiry: expiryDate.toISOString().split('T')[0],
        dte,
        strike,
        type: typeCode === 'C' ? 'Call' : 'Put',
        price: parseFloat(t.lastPrice) || 0,
        bid: parseFloat(t.bidPrice) || 0,
        ask: parseFloat(t.askPrice) || 0,
        vol: parseFloat(t.volume) || 0,
        iv: m ? parseFloat(m.markIV) || 0 : 0,
        delta: m ? parseFloat(m.delta) || 0 : 0,
        gamma: m ? parseFloat(m.gamma) || 0 : 0,
        theta: m ? parseFloat(m.theta) || 0 : 0,
        vega: m ? parseFloat(m.vega) || 0 : 0,
      });
    }

    return NextResponse.json(
      { contracts },
      { headers: { 'Cache-Control': 's-maxage=60, stale-while-revalidate=30' } }
    );
  } catch (err) {
    console.error('Options API error:', err);
    return NextResponse.json({ contracts: [], error: String(err) });
  }
}
