import { NextResponse } from 'next/server';

export async function GET() {
  try {
    const res = await fetch('https://api.binance.com/api/v3/ticker/price', {
      cache: 'no-store',
    });
    if (!res.ok) return NextResponse.json({ prices: {} });

    const data: { symbol: string; price: string }[] = await res.json();
    const prices: Record<string, number> = {};
    for (const item of data) {
      prices[item.symbol] = parseFloat(item.price);
    }

    return NextResponse.json(
      { prices },
      { headers: { 'Cache-Control': 's-maxage=60, stale-while-revalidate=30' } }
    );
  } catch {
    return NextResponse.json({ prices: {} });
  }
}
