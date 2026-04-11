'use client';

import useSWR from 'swr';
import { useMemo } from 'react';
import { OptionContract, Strategy } from '@/lib/types';
import { generateStrategies } from '@/lib/strategy';

const fetcher = (url: string) => fetch(url).then((r) => r.json());

export function useOptionsData() {
  const {
    data: optionsData,
    error: optionsError,
    isLoading: optionsLoading,
    mutate: mutateOptions,
  } = useSWR<{ contracts: OptionContract[]; error?: string }>(
    '/api/options',
    fetcher,
    { refreshInterval: 60_000, revalidateOnFocus: false }
  );

  const {
    data: spotData,
    error: spotError,
    isLoading: spotLoading,
    mutate: mutateSpot,
  } = useSWR<{ prices: Record<string, number> }>(
    '/api/spot',
    fetcher,
    { refreshInterval: 60_000, revalidateOnFocus: false }
  );

  const strategies = useMemo<Strategy[]>(() => {
    if (!optionsData?.contracts || !spotData?.prices) return [];
    return generateStrategies(optionsData.contracts, spotData.prices);
  }, [optionsData, spotData]);

  const spotPrices = spotData?.prices ?? {};

  function refresh() {
    mutateOptions();
    mutateSpot();
  }

  return {
    strategies,
    spotPrices,
    isLoading: optionsLoading || spotLoading,
    error: optionsError || spotError || optionsData?.error,
    refresh,
  };
}
