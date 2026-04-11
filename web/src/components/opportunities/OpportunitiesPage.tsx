'use client';

import { useState, useMemo } from 'react';
import { useOptionsData } from '@/hooks/useOptionsData';
import { Strategy, StrategyType } from '@/lib/types';
import { TopBar } from '@/components/layout/TopBar';
import { FilterBar } from './FilterBar';
import { OpportunityList } from './OpportunityList';
import { DetailPanel } from '@/components/detail/DetailPanel';

export function OpportunitiesPage() {
  const { strategies, spotPrices, isLoading, error, refresh } = useOptionsData();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [filterType, setFilterType] = useState<StrategyType | 'All'>('All');
  const [filterAsset, setFilterAsset] = useState<string>('All');

  const assets = useMemo(() => {
    const set = new Set<string>();
    strategies.forEach((s) => set.add(s.underlying));
    return Array.from(set).sort();
  }, [strategies]);

  const filtered = useMemo(() => {
    return strategies.filter((s) => {
      if (filterType !== 'All' && s.type !== filterType) return false;
      if (filterAsset !== 'All' && s.underlying !== filterAsset) return false;
      return true;
    });
  }, [strategies, filterType, filterAsset]);

  const selectedStrategy: Strategy | null = selectedId
    ? (strategies.find((s) => s.id === selectedId) ?? null)
    : null;

  function handleSelect(id: string) {
    setSelectedId((prev) => (prev === id ? null : id));
  }

  function handleFilterType(type: StrategyType | 'All') {
    setFilterType(type);
    setSelectedId(null);
  }

  function handleFilterAsset(asset: string) {
    setFilterAsset(asset);
    setSelectedId(null);
  }

  return (
    <div className="min-h-screen bg-gray-950">
      <TopBar spotPrices={spotPrices} onRefresh={refresh} />

      <FilterBar
        filterType={filterType}
        filterAsset={filterAsset}
        assets={assets}
        onFilterType={handleFilterType}
        onFilterAsset={handleFilterAsset}
      />

      {error && !isLoading && (
        <div className="mx-4 mt-4 p-4 bg-rose-500/10 border border-rose-500/20 rounded-xl">
          <p className="text-sm text-rose-400">
            Unable to load market data.{' '}
            <button onClick={refresh} className="underline font-medium">
              Retry
            </button>
          </p>
        </div>
      )}

      {/* Content shifts left on desktop when panel is open */}
      <div className={selectedStrategy ? 'md:mr-[440px] transition-all duration-300' : 'transition-all duration-300'}>
        <OpportunityList
          strategies={filtered}
          selectedId={selectedId}
          isLoading={isLoading}
          onSelect={handleSelect}
        />
      </div>

      <DetailPanel strategy={selectedStrategy} onClose={() => setSelectedId(null)} />
    </div>
  );
}
