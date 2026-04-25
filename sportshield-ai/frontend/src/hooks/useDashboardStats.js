import { useState, useEffect } from 'react';
import { rtdb, ref, onValue, off } from '../lib/firebase';

export function useDashboardStats() {
  const [stats, setStats] = useState({
    total_assets: 0,
    total_scans: 0,
    total_violations: 0,
    total_value_protected: 0
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const statsRef = ref(rtdb, 'dashboard_stats');
    const unsubscribe = onValue(statsRef, (snapshot) => {
      if (snapshot.exists()) {
        const data = snapshot.val();
        setStats({
          total_assets: data.assets_protected || 0,
          total_scans: data.total_scans_today || 0,
          total_violations: data.violations_today || 0,
          total_value_protected: data.rights_value_protected_usd || 0
        });
      } else {
        setStats({
          total_assets: 0,
          total_scans: 0,
          total_violations: 0,
          total_value_protected: 0
        });
      }
      setLoading(false);
    });
    return () => off(statsRef, 'value', unsubscribe);
  }, []);

  return { ...stats, loading };
}
