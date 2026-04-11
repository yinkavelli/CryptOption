'use client';

import { Strategy } from '@/lib/types';
import { cn } from '@/lib/utils';

export function LegsTable({ strategy }: { strategy: Strategy }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-white/[0.06]">
            {['Action', 'Type', 'Strike', 'Expiry', 'Limit'].map((h) => (
              <th
                key={h}
                className={cn(
                  'py-2 font-medium text-gray-600',
                  h === 'Action' ? 'text-left' : 'text-right'
                )}
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {strategy.legs.map((leg, i) => (
            <tr key={i} className="border-b border-white/[0.03] last:border-0">
              <td className="py-2.5 pr-3">
                <span
                  className={cn(
                    'px-2 py-0.5 rounded-full text-[10px] font-semibold',
                    leg.side === 'Buy'
                      ? 'text-emerald-400 bg-emerald-400/10'
                      : 'text-rose-400 bg-rose-400/10'
                  )}
                >
                  {leg.side}
                </span>
              </td>
              <td className="py-2.5 text-right text-gray-400">{leg.option.type}</td>
              <td className="py-2.5 text-right font-mono text-white pl-3">
                ${leg.option.strike.toLocaleString('en-US')}
              </td>
              <td className="py-2.5 text-right font-mono text-gray-500 pl-3">
                {leg.option.expiry}
              </td>
              <td className="py-2.5 text-right font-mono text-cyan-400 pl-3">
                ${leg.price.toFixed(2)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
