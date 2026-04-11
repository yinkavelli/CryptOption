'use client';

import { useCountdown } from '@/hooks/useCountdown';

interface TopBarProps {
  spotPrices: Record<string, number>;
  onRefresh: () => void;
}

const TRACKED = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT'];

export function TopBar({ spotPrices, onRefresh }: TopBarProps) {
  const remaining = useCountdown(60);
  const progress = remaining / 60;
  const circumference = 75.4; // 2π × 12

  return (
    <header className="sticky top-0 z-50 bg-gray-950/95 backdrop-blur-xl border-b border-white/[0.06]">
      <div className="flex items-center h-14 px-4 gap-3">
        {/* Brand */}
        <div className="flex items-center gap-2 shrink-0">
          <span className="text-base font-bold tracking-tight">
            <span className="text-neon-cyan">Crypt</span>
            <span className="text-white">Option</span>
          </span>
          <span className="w-1.5 h-1.5 rounded-full bg-neon-cyan animate-pulse" />
        </div>

        {/* Live price strip */}
        <div className="flex-1 overflow-hidden mx-2 hidden sm:block">
          <div className="flex gap-5 overflow-x-auto scrollbar-none">
            {TRACKED.map((sym) => {
              const price = spotPrices[sym];
              const label = sym.replace('USDT', '');
              if (!price) return null;
              return (
                <div key={sym} className="flex items-center gap-1.5 shrink-0">
                  <span className="text-[11px] text-gray-500 font-medium">{label}</span>
                  <span className="text-[11px] font-mono text-gray-200">
                    ${price.toLocaleString('en-US', { maximumFractionDigits: 0 })}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Refresh countdown ring */}
        <button
          onClick={onRefresh}
          title="Refresh data"
          className="relative w-9 h-9 flex items-center justify-center ml-auto shrink-0 hover:opacity-80 transition-opacity"
        >
          <svg className="absolute inset-0 w-9 h-9 -rotate-90" viewBox="0 0 36 36">
            <circle cx="18" cy="18" r="12" fill="none" stroke="#ffffff0d" strokeWidth="2" />
            <circle
              cx="18"
              cy="18"
              r="12"
              fill="none"
              stroke="#00f5ff"
              strokeWidth="2"
              strokeDasharray={`${circumference * progress} ${circumference}`}
              strokeLinecap="round"
            />
          </svg>
          <span className="text-[9px] font-mono text-neon-cyan font-bold">{remaining}s</span>
        </button>
      </div>
    </header>
  );
}
