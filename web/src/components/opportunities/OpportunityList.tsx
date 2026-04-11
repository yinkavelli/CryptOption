'use client';

import { motion, AnimatePresence } from 'framer-motion';
import { Strategy } from '@/lib/types';
import { OpportunityCard } from './OpportunityCard';

function SkeletonCard() {
  return (
    <div className="rounded-2xl border border-white/[0.06] bg-white/[0.03] p-4 animate-pulse">
      <div className="flex justify-between mb-3">
        <div className="flex gap-2">
          <div className="h-5 w-20 bg-white/10 rounded-full" />
          <div className="h-5 w-10 bg-white/10 rounded-full" />
        </div>
        <div className="h-5 w-8 bg-white/10 rounded-full" />
      </div>
      <div className="flex justify-between items-end mb-3">
        <div>
          <div className="h-3 w-14 bg-white/10 rounded mb-1.5" />
          <div className="h-7 w-20 bg-white/10 rounded" />
        </div>
        <div>
          <div className="h-3 w-14 bg-white/10 rounded mb-1.5" />
          <div className="h-6 w-12 bg-white/10 rounded" />
        </div>
      </div>
      <div className="flex gap-3 pt-3 border-t border-white/[0.04]">
        <div className="h-3 w-10 bg-white/10 rounded" />
        <div className="h-3 w-10 bg-white/10 rounded" />
      </div>
    </div>
  );
}

interface Props {
  strategies: Strategy[];
  selectedId: string | null;
  isLoading: boolean;
  onSelect: (id: string) => void;
}

export function OpportunityList({ strategies, selectedId, isLoading, onSelect }: Props) {
  if (isLoading) {
    return (
      <div className="p-4 space-y-3">
        {Array.from({ length: 7 }).map((_, i) => (
          <SkeletonCard key={i} />
        ))}
      </div>
    );
  }

  if (strategies.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-24 text-center px-8">
        <div className="text-5xl mb-4">📉</div>
        <p className="text-gray-400 text-sm leading-relaxed">
          No strategies match your filters.
          <br />
          Try a different asset or strategy type.
        </p>
      </div>
    );
  }

  return (
    <div className="p-4 space-y-3">
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs text-gray-600">{strategies.length} opportunities</span>
        <span className="text-xs text-gray-600">sorted by DTE ↑</span>
      </div>
      <AnimatePresence mode="popLayout">
        {strategies.map((strategy) => (
          <motion.div
            key={strategy.id}
            layout
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96 }}
            transition={{ duration: 0.18 }}
          >
            <OpportunityCard
              strategy={strategy}
              isSelected={selectedId === strategy.id}
              onClick={() => onSelect(strategy.id)}
            />
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}
