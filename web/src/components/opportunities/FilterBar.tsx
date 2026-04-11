'use client';

import { StrategyType } from '@/lib/types';
import { cn } from '@/lib/utils';

const STRATEGY_TYPES: (StrategyType | 'All')[] = [
  'All',
  'Long Call',
  'Long Put',
  'Long Straddle',
];

interface Props {
  filterType: StrategyType | 'All';
  filterAsset: string;
  assets: string[];
  onFilterType: (type: StrategyType | 'All') => void;
  onFilterAsset: (asset: string) => void;
}

export function FilterBar({ filterType, filterAsset, assets, onFilterType, onFilterAsset }: Props) {
  return (
    <div className="sticky top-14 z-40 bg-gray-950/95 backdrop-blur-xl border-b border-white/[0.05] px-4 py-3 space-y-2.5">
      {/* Strategy type pills */}
      <div className="flex gap-2 overflow-x-auto scrollbar-none">
        {STRATEGY_TYPES.map((type) => (
          <button
            key={type}
            onClick={() => onFilterType(type)}
            className={cn(
              'shrink-0 px-3 py-1.5 rounded-full text-xs font-medium transition-all duration-200',
              filterType === type
                ? 'bg-neon-cyan text-gray-950 shadow-[0_0_12px_#00f5ff50]'
                : 'text-gray-400 bg-white/[0.06] hover:bg-white/[0.1] hover:text-gray-200'
            )}
          >
            {type}
          </button>
        ))}
      </div>

      {/* Asset chips */}
      {assets.length > 0 && (
        <div className="flex gap-1.5 overflow-x-auto scrollbar-none">
          {(['All', ...assets] as string[]).map((asset) => (
            <button
              key={asset}
              onClick={() => onFilterAsset(asset)}
              className={cn(
                'shrink-0 px-2.5 py-1 rounded-full text-[11px] font-medium transition-all duration-200',
                filterAsset === asset
                  ? 'bg-cyan-400/20 text-cyan-400 border border-cyan-400/30'
                  : 'text-gray-600 bg-white/[0.04] border border-transparent hover:text-gray-400'
              )}
            >
              {asset}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
