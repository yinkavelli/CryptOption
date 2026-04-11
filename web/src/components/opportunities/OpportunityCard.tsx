'use client';

import { motion } from 'framer-motion';
import { TrendingUp, TrendingDown, Activity } from 'lucide-react';
import { Strategy } from '@/lib/types';
import { cn } from '@/lib/utils';

const TYPE_CONFIG = {
  'Long Call': {
    label: 'Long Call',
    textColor: 'text-cyan-400',
    badgeBg: 'bg-cyan-400/10',
    accent: 'bg-cyan-400',
    icon: TrendingUp,
  },
  'Long Put': {
    label: 'Long Put',
    textColor: 'text-rose-400',
    badgeBg: 'bg-rose-400/10',
    accent: 'bg-rose-400',
    icon: TrendingDown,
  },
  'Long Straddle': {
    label: 'Straddle',
    textColor: 'text-violet-400',
    badgeBg: 'bg-violet-400/10',
    accent: 'bg-violet-400',
    icon: Activity,
  },
} as const;

function dteBadge(dte: number) {
  if (dte <= 7) return 'text-red-400 bg-red-400/10';
  if (dte <= 14) return 'text-orange-400 bg-orange-400/10';
  if (dte <= 30) return 'text-yellow-400 bg-yellow-400/10';
  return 'text-gray-500 bg-white/5';
}

interface Props {
  strategy: Strategy;
  isSelected: boolean;
  onClick: () => void;
}

export function OpportunityCard({ strategy, isSelected, onClick }: Props) {
  const cfg = TYPE_CONFIG[strategy.type];
  const Icon = cfg.icon;

  return (
    <motion.button
      layout
      onClick={onClick}
      whileHover={{ scale: 1.012 }}
      whileTap={{ scale: 0.988 }}
      className={cn(
        'relative w-full text-left rounded-2xl p-4 overflow-hidden',
        'bg-white/[0.04] border border-white/[0.07]',
        'transition-colors duration-200',
        isSelected && 'bg-white/[0.08] border-white/20'
      )}
    >
      {/* Left accent bar */}
      <div className={cn('absolute left-0 top-0 bottom-0 w-[3px]', cfg.accent)} />

      {/* Header */}
      <div className="flex items-center justify-between mb-3 pl-1">
        <div className="flex items-center gap-2">
          <span
            className={cn(
              'inline-flex items-center gap-1 text-[11px] font-semibold px-2 py-0.5 rounded-full',
              cfg.badgeBg,
              cfg.textColor
            )}
          >
            <Icon size={10} />
            {cfg.label}
          </span>
          <span className="text-white font-bold text-sm">{strategy.underlying}</span>
        </div>
        <span className={cn('text-[11px] font-mono px-2 py-0.5 rounded-full', dteBadge(strategy.dte))}>
          {strategy.dte}d
        </span>
      </div>

      {/* Main metrics */}
      <div className="flex items-end justify-between pl-1">
        <div>
          <div className="text-[10px] text-gray-500 mb-0.5">Est. Cost</div>
          <div className="text-xl font-bold font-mono text-white">
            ${Math.abs(strategy.credit).toFixed(2)}
          </div>
        </div>
        <div className="text-right">
          <div className="text-[10px] text-gray-500 mb-0.5">Prob. Profit</div>
          <div className={cn('text-lg font-semibold font-mono', cfg.textColor)}>
            {strategy.probProfit.toFixed(0)}%
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="flex items-center gap-3 mt-3 pt-3 border-t border-white/[0.05] pl-1">
        <div className="flex items-center gap-1">
          <span className="text-[10px] text-gray-600">Δ</span>
          <span className="text-[11px] font-mono text-gray-400">
            {strategy.netDelta.toFixed(2)}
          </span>
        </div>
        <div className="flex items-center gap-1">
          <span className="text-[10px] text-gray-600">Θ</span>
          <span className="text-[11px] font-mono text-gray-400">
            {strategy.netTheta.toFixed(2)}
          </span>
        </div>
        <div className="flex-1" />
        <span className="text-[10px] font-mono text-gray-600">{strategy.expiry}</span>
      </div>
    </motion.button>
  );
}
