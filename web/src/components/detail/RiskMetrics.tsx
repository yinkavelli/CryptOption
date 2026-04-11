'use client';

import { Strategy } from '@/lib/types';
import { cn } from '@/lib/utils';

interface MetricCardProps {
  label: string;
  value: string;
  sub: string;
  highlight?: boolean;
}

function MetricCard({ label, value, sub, highlight }: MetricCardProps) {
  return (
    <div className="bg-white/[0.04] border border-white/[0.07] rounded-xl p-3 text-center">
      <div className="text-[10px] text-gray-600 mb-1 font-medium">{label}</div>
      <div
        className={cn(
          'text-base font-bold font-mono',
          highlight ? 'text-neon-cyan' : 'text-white'
        )}
      >
        {value}
      </div>
      <div className="text-[9px] text-gray-600 mt-0.5">{sub}</div>
    </div>
  );
}

export function RiskMetrics({ strategy }: { strategy: Strategy }) {
  const breakEvenDisplay = Array.isArray(strategy.breakEven)
    ? `$${strategy.breakEven[0].toFixed(0)} / $${strategy.breakEven[1].toFixed(0)}`
    : `$${strategy.breakEven.toLocaleString('en-US', { maximumFractionDigits: 0 })}`;

  return (
    <div className="grid grid-cols-2 gap-2">
      <MetricCard
        label="Est. Cost (Debit)"
        value={`$${Math.abs(strategy.credit).toFixed(2)}`}
        sub="Cash paid upfront"
        highlight
      />
      <MetricCard
        label="Max Loss"
        value={`$${strategy.maxRisk.toFixed(2)}`}
        sub="Total premium at risk"
      />
      <MetricCard
        label="Break Even"
        value={breakEvenDisplay}
        sub="Price needed at expiry"
      />
      <MetricCard
        label="Prob. Profit"
        value={`${strategy.probProfit.toFixed(1)}%`}
        sub="Estimated probability"
      />
    </div>
  );
}
