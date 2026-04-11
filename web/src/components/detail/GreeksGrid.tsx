'use client';

import { motion } from 'framer-motion';
import { Strategy } from '@/lib/types';

interface TileProps {
  symbol: string;
  name: string;
  value: number;
  decimals: number;
  description: string;
  color: string;
  index: number;
}

function GreekTile({ symbol, name, value, decimals, description, color, index }: TileProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.06, duration: 0.2 }}
      className="bg-white/[0.04] border border-white/[0.07] rounded-xl p-3"
    >
      <div className="flex items-center justify-between mb-1.5">
        <span className={`text-lg font-bold leading-none ${color}`}>{symbol}</span>
        <span className="text-[10px] text-gray-600 font-medium">{name}</span>
      </div>
      <div className="text-base font-bold font-mono text-white">
        {value.toFixed(decimals)}
      </div>
      <div className="text-[10px] text-gray-600 mt-0.5">{description}</div>
    </motion.div>
  );
}

export function GreeksGrid({ strategy }: { strategy: Strategy }) {
  const greeks = [
    {
      symbol: 'Δ',
      name: 'Delta',
      value: strategy.netDelta,
      decimals: 3,
      description: 'Directional exposure',
      color: 'text-sky-400',
    },
    {
      symbol: 'Γ',
      name: 'Gamma',
      value: strategy.netGamma,
      decimals: 4,
      description: 'Delta rate of change',
      color: 'text-emerald-400',
    },
    {
      symbol: 'Θ',
      name: 'Theta',
      value: strategy.netTheta,
      decimals: 2,
      description: 'Daily time decay',
      color: 'text-rose-400',
    },
    {
      symbol: 'ν',
      name: 'Vega',
      value: strategy.netVega,
      decimals: 2,
      description: 'Vol sensitivity',
      color: 'text-violet-400',
    },
  ];

  return (
    <div className="grid grid-cols-2 gap-2">
      {greeks.map((g, i) => (
        <GreekTile key={g.symbol} {...g} index={i} />
      ))}
    </div>
  );
}
