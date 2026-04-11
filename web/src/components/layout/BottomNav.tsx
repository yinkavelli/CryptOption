'use client';

import { useState } from 'react';
import { motion } from 'framer-motion';
import { BarChart2, Star, Settings } from 'lucide-react';
import { cn } from '@/lib/utils';

const tabs = [
  { id: 'markets', label: 'Markets', icon: BarChart2 },
  { id: 'watchlist', label: 'Watchlist', icon: Star },
  { id: 'settings', label: 'Settings', icon: Settings },
];

export function BottomNav() {
  const [active, setActive] = useState('markets');

  return (
    <nav
      className="fixed bottom-0 left-0 right-0 z-50 md:hidden bg-gray-950/95 backdrop-blur-xl border-t border-white/[0.06]"
      style={{ paddingBottom: 'env(safe-area-inset-bottom)' }}
    >
      <div className="flex">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = active === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActive(tab.id)}
              className="flex-1 flex flex-col items-center py-3 gap-1 relative min-h-[56px]"
            >
              {isActive && (
                <motion.div
                  layoutId="bottomNavBar"
                  className="absolute top-0 left-1/4 right-1/4 h-[2px] bg-neon-cyan rounded-full"
                />
              )}
              <Icon
                size={20}
                className={cn(
                  'transition-colors duration-200',
                  isActive ? 'text-neon-cyan' : 'text-gray-600'
                )}
              />
              <span
                className={cn(
                  'text-[10px] font-medium transition-colors duration-200',
                  isActive ? 'text-neon-cyan' : 'text-gray-600'
                )}
              >
                {tab.label}
              </span>
            </button>
          );
        })}
      </div>
    </nav>
  );
}
