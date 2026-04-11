'use client';

import { useMemo } from 'react';
import {
  ComposedChart,
  Area,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
} from 'recharts';
import { Strategy, PayoffPoint } from '@/lib/types';
import { calculatePayoff } from '@/lib/strategy';

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const CustomTooltip = ({ active, payload }: any) => {
  if (!active || !payload?.[0]) return null;
  const d = payload[0].payload as PayoffPoint;
  return (
    <div className="bg-gray-900 border border-white/10 rounded-xl px-3 py-2 text-xs shadow-xl">
      <div className="text-gray-400 mb-1">
        Price:{' '}
        <span className="text-white font-mono">
          ${d.price.toLocaleString('en-US', { maximumFractionDigits: 0 })}
        </span>
      </div>
      <div className={d.pnl >= 0 ? 'text-emerald-400' : 'text-rose-400'}>
        P/L:{' '}
        <span className="font-mono font-bold">
          {d.pnl >= 0 ? '+' : ''}${d.pnl.toFixed(2)}
        </span>
      </div>
    </div>
  );
};

export function PayoffChart({ strategy }: { strategy: Strategy }) {
  const data = useMemo(() => calculatePayoff(strategy), [strategy]);

  const breakEvens = Array.isArray(strategy.breakEven)
    ? strategy.breakEven
    : [strategy.breakEven];

  return (
    <div className="w-full h-[240px]">
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={data} margin={{ top: 8, right: 8, left: -8, bottom: 0 }}>
          <defs>
            <linearGradient id="fillPos" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#10b981" stopOpacity={0.25} />
              <stop offset="100%" stopColor="#10b981" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="fillNeg" x1="0" y1="1" x2="0" y2="0">
              <stop offset="0%" stopColor="#f43f5e" stopOpacity={0.25} />
              <stop offset="100%" stopColor="#f43f5e" stopOpacity={0} />
            </linearGradient>
          </defs>

          <CartesianGrid stroke="#ffffff07" strokeDasharray="3 3" vertical={false} />

          <XAxis
            dataKey="price"
            type="number"
            domain={['dataMin', 'dataMax']}
            tickFormatter={(v: number) =>
              v >= 1000 ? `$${(v / 1000).toFixed(0)}k` : `$${v.toFixed(0)}`
            }
            tick={{ fill: '#4b5563', fontSize: 10 }}
            axisLine={{ stroke: '#ffffff0d' }}
            tickLine={false}
            minTickGap={40}
          />
          <YAxis
            tickFormatter={(v: number) => `$${v.toFixed(0)}`}
            tick={{ fill: '#4b5563', fontSize: 10 }}
            axisLine={false}
            tickLine={false}
            width={48}
          />

          <Tooltip content={<CustomTooltip />} />

          <Area
            type="monotone"
            dataKey="positivePnl"
            fill="url(#fillPos)"
            stroke="none"
            isAnimationActive={false}
          />
          <Area
            type="monotone"
            dataKey="negativePnl"
            fill="url(#fillNeg)"
            stroke="none"
            isAnimationActive={false}
          />

          <Line
            type="monotone"
            dataKey="pnl"
            stroke="#00f5ff"
            strokeWidth={2}
            dot={false}
            isAnimationActive={false}
          />

          <ReferenceLine y={0} stroke="#ffffff15" strokeDasharray="4 3" />

          <ReferenceLine
            x={strategy.spot}
            stroke="#fbbf24"
            strokeDasharray="4 3"
            label={{ value: 'Spot', fill: '#fbbf2490', fontSize: 9, position: 'insideTopRight' }}
          />

          {breakEvens.map((be, i) => (
            <ReferenceLine
              key={i}
              x={be}
              stroke="#fb923c"
              strokeDasharray="4 3"
              label={{ value: 'B/E', fill: '#fb923c90', fontSize: 9, position: 'insideTopLeft' }}
            />
          ))}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
