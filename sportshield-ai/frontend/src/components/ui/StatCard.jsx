// SportShield AI | Google Solution Challenge 2026 | First Prize Target
/** WHY: Generic dynamic data aggregation indicator using smooth CountUp behavior natively attached to CSS tags. */
import React from 'react';
import { useCountUp } from '../../hooks/useCountUp';

export default function StatCard({ value, label, prefix = '', suffix = '', color = 'green', icon: Icon }) {
  const normalizedNumber =
    typeof value === 'number' && Number.isFinite(value) ? value : 0;
  const animatedValue = useCountUp(normalizedNumber, 1200);
  const displayValue =
    typeof value === 'string' && value.trim() !== ''
      ? value
      : animatedValue.toLocaleString();

  return (
    <div className={`stat-card ${color} slide-in`}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <div className={`stat-number ${color}`}>
            {prefix}{displayValue}{suffix}
          </div>
          <div className="stat-label">{label}</div>
        </div>
        {Icon && (
          <div style={{ opacity: 0.2, color: `var(--color-${color === 'green' ? 'neon' : color === 'red' ? 'threat' : color === 'amber' ? 'warn' : 'info'})` }}>
            <Icon size={32} />
          </div>
        )}
      </div>
    </div>
  );
}
