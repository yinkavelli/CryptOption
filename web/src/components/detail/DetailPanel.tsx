'use client';

import { motion, AnimatePresence, useDragControls } from 'framer-motion';
import { X } from 'lucide-react';
import { Strategy } from '@/lib/types';
import { PayoffChart } from './PayoffChart';
import { GreeksGrid } from './GreeksGrid';
import { RiskMetrics } from './RiskMetrics';
import { LegsTable } from './LegsTable';

interface Props {
  strategy: Strategy | null;
  onClose: () => void;
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section>
      <h3 className="text-[10px] font-semibold text-gray-600 uppercase tracking-widest mb-3">
        {title}
      </h3>
      {children}
    </section>
  );
}

function PanelContent({ strategy, onClose }: { strategy: Strategy; onClose: () => void }) {
  return (
    <>
      {/* Header */}
      <div className="flex items-start justify-between px-5 py-4 border-b border-white/[0.06] shrink-0">
        <div>
          <div className="text-[11px] text-gray-500 mb-0.5">{strategy.type}</div>
          <div className="text-sm font-semibold text-white leading-snug">{strategy.symbol}</div>
          <div className="text-[11px] font-mono text-gray-600 mt-0.5">
            Spot ${strategy.spot.toLocaleString('en-US', { maximumFractionDigits: 0 })} · {strategy.dte}d to expiry
          </div>
        </div>
        <button
          onClick={onClose}
          className="p-2 rounded-full bg-white/[0.05] hover:bg-white/[0.1] transition-colors shrink-0"
        >
          <X size={14} className="text-gray-400" />
        </button>
      </div>

      {/* Scrollable body */}
      <div className="flex-1 overflow-y-auto px-5 py-4 space-y-6">
        <Section title="Payoff at Expiry">
          <PayoffChart strategy={strategy} />
        </Section>
        <Section title="Risk Metrics">
          <RiskMetrics strategy={strategy} />
        </Section>
        <Section title="Greeks">
          <GreeksGrid strategy={strategy} />
        </Section>
        <Section title="Strategy Legs">
          <div className="bg-white/[0.03] border border-white/[0.06] rounded-xl p-3">
            <LegsTable strategy={strategy} />
          </div>
        </Section>
      </div>
    </>
  );
}

export function DetailPanel({ strategy, onClose }: Props) {
  const dragControls = useDragControls();

  return (
    <AnimatePresence>
      {strategy && (
        <>
          {/* Mobile backdrop */}
          <motion.div
            key="backdrop"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40 md:hidden"
          />

          {/* Mobile bottom sheet */}
          <motion.div
            key="sheet"
            drag="y"
            dragControls={dragControls}
            dragConstraints={{ top: 0, bottom: 0 }}
            dragElastic={{ top: 0, bottom: 0.4 }}
            onDragEnd={(_, info) => {
              if (info.velocity.y > 400 || info.offset.y > 140) onClose();
            }}
            initial={{ y: '100%' }}
            animate={{ y: 0 }}
            exit={{ y: '100%' }}
            transition={{ type: 'spring', damping: 28, stiffness: 280 }}
            className="fixed inset-x-0 bottom-0 z-50 md:hidden flex flex-col bg-gray-950 border-t border-white/10 rounded-t-[28px] max-h-[90dvh]"
            style={{ paddingBottom: 'env(safe-area-inset-bottom)' }}
          >
            {/* Drag handle */}
            <div
              onPointerDown={(e) => dragControls.start(e)}
              className="flex justify-center pt-3 pb-1 cursor-grab active:cursor-grabbing shrink-0"
            >
              <div className="w-10 h-1 bg-white/20 rounded-full" />
            </div>

            <PanelContent strategy={strategy} onClose={onClose} />
          </motion.div>

          {/* Desktop side panel */}
          <motion.div
            key="sidepanel"
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 28, stiffness: 280 }}
            className="hidden md:flex fixed right-0 top-0 bottom-0 w-[440px] z-50 flex-col bg-gray-950 border-l border-white/[0.08]"
          >
            <PanelContent strategy={strategy} onClose={onClose} />
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
