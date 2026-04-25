// SportShield AI | Google Solution Challenge 2026 | First Prize Target
/** WHY: Central intel hub for the Operator. Fuses real-time DB states directly into propagation maps and live metrics. */
import React from 'react';
import { motion } from 'framer-motion';
import { useDashboardStats } from '../hooks/useDashboardStats';
import { useViralAlerts } from '../hooks/useViralAlerts';
import StatCard from '../components/ui/StatCard';
import PropagationMap from '../components/features/PropagationMap';
import RealtimeFeed from '../components/features/RealtimeFeed';
import { ShieldCheck, Crosshair, AlertOctagon, Activity } from 'lucide-react';

export default function Dashboard() {
  const stats = useDashboardStats();
  const { currentAlert } = useViralAlerts();

  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }} style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      
      {currentAlert?.is_active && (
        <div className="viral-banner slide-in">
          <Activity size={24} className="pulse-threat" />
          <div style={{ flex: 1 }}>
            <h4 style={{ fontFamily: 'var(--font-display)', fontSize: '14px', letterSpacing: '0.1em' }}>VIRAL SPREAD DETECTED</h4>
            <p style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', marginTop: '4px' }}>{currentAlert.asset_name} is propagating across {currentAlert.source_count} unauthorized networks.</p>
          </div>
          <span className="badge badge-critical">IMMEDIATE ACTION REQUIRED</span>
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '24px' }}>
        <StatCard value={stats.total_assets} label="SECURITIZED ASSETS" icon={ShieldCheck} color="safe" />
        <StatCard value={stats.total_scans} label="ACTIVE SCANS" icon={Crosshair} color="info" />
        <StatCard value={stats.total_violations} label="THREATS DETECTED" icon={AlertOctagon} color="threat" />
        <StatCard value={stats.total_value_protected} label="VALUE PROTECTED" prefix="$" icon={Activity} color="warn" />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 350px', gap: '24px' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          <div className="card">
            <h4 style={{ fontFamily: 'var(--font-display)', fontSize: '13px', letterSpacing: '0.1em', marginBottom: '16px' }}>GLOBAL PROPAGATION MATRIX</h4>
            <PropagationMap />
          </div>
        </div>
        <RealtimeFeed />
      </div>

    </motion.div>
  );
}
