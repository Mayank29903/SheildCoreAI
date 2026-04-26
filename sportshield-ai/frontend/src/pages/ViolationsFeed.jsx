// ShieldCore AI | Google Solution Challenge 2026 | First Prize Target
/**
 * WHY: Complete redesign of ViolationsFeed.
 * Old: Thin list of cards, no filtering, no stats.
 * New: Full intel command center with filter bar, stats row, sortable
 *      violation cards, empty-state, and real-time reload.
 */
import React, { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  collection,
  query,
  orderBy,
  limit,
  where,
  getDocs,
} from "firebase/firestore";
import { db } from "../lib/firebase";
import ViolationCard from "../components/features/ViolationCard";
import LoadingSpinner from "../components/ui/LoadingSpinner";
import { getViolations } from "../lib/api";
import {
  AlertOctagon,
  Filter,
  RefreshCw,
  ChevronDown,
  Shield,
  Zap,
  Globe,
  Download,
} from "lucide-react";

const FILTER_TYPES = ["all", "deepfake", "theft", "both"];
const FILTER_STATUS = ["all", "detected", "takedown_sent", "resolved"];

const StatBadge = ({ label, value, color = "var(--color-text-dim)" }) => (
  <div
    className="card"
    style={{
      padding: "14px 20px",
      display: "flex",
      flexDirection: "column",
      gap: "4px",
      minWidth: "120px",
    }}
  >
    <span
      style={{
        fontFamily: "var(--font-mono)",
        fontSize: "24px",
        fontWeight: 700,
        color,
      }}
    >
      {value}
    </span>
    <span
      style={{
        fontFamily: "var(--font-mono)",
        fontSize: "10px",
        color: "var(--color-text-ghost)",
        letterSpacing: "0.08em",
      }}
    >
      {label}
    </span>
  </div>
);

export default function ViolationsFeed() {
  const [violations, setViolations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filterType, setFilterType] = useState("all");
  const [filterStatus, setFilterStatus] = useState("all");
  const [refreshing, setRefreshing] = useState(false);

  const fetchViolations = useCallback(
    async (showLoader = true) => {
      if (showLoader) setLoading(true);
      else setRefreshing(true);
      try {
        const params = {};
        if (filterType !== "all") params.detection_type = filterType;
        if (filterStatus !== "all") params.status = filterStatus;
        const res = await getViolations(params);
        setViolations(Array.isArray(res.data) ? res.data : []);
      } catch {
        // Fallback: read directly from Firebase client
        try {
          let q = query(
            collection(db, "violations"),
            orderBy("detected_at", "desc"),
            limit(50),
          );
          const snap = await getDocs(q);
          let data = snap.docs.map((d) => d.data());
          if (filterType !== "all")
            data = data.filter((v) => v.detection_type === filterType);
          if (filterStatus !== "all")
            data = data.filter((v) => v.status === filterStatus);
          setViolations(data);
        } catch (e2) {
          console.error(e2);
          setViolations([]);
        }
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [filterType, filterStatus],
  );

  useEffect(() => {
    fetchViolations();
  }, [fetchViolations]);

  const handleExportCSV = () => {
    if (!violations.length) return;
    const header = "Violation ID,Asset Name,Detection Type,Source Domain,Status,Timestamp\n";
    const rows = violations.map(v => 
      `${v.violation_id},"${v.asset_name}",${v.detection_type},${v.source_domain},${v.status},${new Date(v.detected_at).toISOString()}`
    ).join("\n");
    const blob = new Blob([header + rows], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `violations_legal_log_${new Date().getTime()}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
  };

  const handleTakedownSent = (id) => {
    setViolations((prev) =>
      prev.map((v) =>
        v.violation_id === id ? { ...v, status: "takedown_sent" } : v,
      ),
    );
  };

  const deepfakeCount = violations.filter(
    (v) => v.detection_type === "deepfake" || v.detection_type === "both",
  ).length;
  const theftCount = violations.filter(
    (v) => v.detection_type === "theft",
  ).length;
  const unresolvedCount = violations.filter(
    (v) => v.status === "detected",
  ).length;

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      style={{ display: "flex", flexDirection: "column", gap: "24px" }}
    >
      {/* ── HEADER ── */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          flexWrap: "wrap",
          gap: "16px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <div
            style={{
              width: "48px",
              height: "48px",
              borderRadius: "12px",
              background: "rgba(239,68,68,0.15)",
              border: "1px solid rgba(239,68,68,0.3)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <AlertOctagon size={24} style={{ color: "var(--color-threat)" }} />
          </div>
          <div>
            <h2
              style={{
                fontFamily: "var(--font-display)",
                fontSize: "24px",
                letterSpacing: "0.1em",
                margin: 0,
              }}
            >
              VIOLATION INTEL FEED
            </h2>
            <p
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: "11px",
                color: "var(--color-text-ghost)",
                margin: 0,
                letterSpacing: "0.08em",
              }}
            >
              REAL-TIME CONTENT INFRINGEMENT REGISTRY
            </p>
          </div>
        </div>
        <div style={{ display: "flex", gap: "12px" }}>
          <button
            className="btn btn-outline btn-sm"
            onClick={handleExportCSV}
            disabled={violations.length === 0}
            style={{ display: "flex", alignItems: "center", gap: "6px" }}
          >
            <Download size={13} />
            EXPORT LEGAL LOG (CSV)
          </button>
          <button
            className="btn btn-outline btn-sm"
            onClick={() => fetchViolations(false)}
            disabled={refreshing}
            style={{ display: "flex", alignItems: "center", gap: "6px" }}
          >
            <RefreshCw size={13} className={refreshing ? "spin" : ""} />
            REFRESH
          </button>
        </div>
      </div>

      {/* ── STATS ROW ── */}
      <div style={{ display: "flex", gap: "16px", flexWrap: "wrap" }}>
        <StatBadge
          label="TOTAL VIOLATIONS"
          value={violations.length}
          color="var(--color-text)"
        />
        <StatBadge
          label="DEEPFAKES"
          value={deepfakeCount}
          color="var(--color-warn)"
        />
        <StatBadge
          label="ASSET THEFT"
          value={theftCount}
          color="var(--color-threat)"
        />
        <StatBadge
          label="UNRESOLVED"
          value={unresolvedCount}
          color="var(--color-threat)"
        />
      </div>

      {/* ── FILTER BAR ── */}
      <div className="card" style={{ padding: "16px 20px" }}>
        <div
          style={{
            display: "flex",
            gap: "24px",
            flexWrap: "wrap",
            alignItems: "center",
          }}
        >
          {/* Type filter */}
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <Zap size={13} style={{ color: "var(--color-neon)" }} />
            <span
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: "10px",
                color: "var(--color-text-ghost)",
                letterSpacing: "0.1em",
              }}
            >
              TYPE
            </span>
            <div style={{ display: "flex", gap: "6px" }}>
              {FILTER_TYPES.map((t) => (
                <button
                  key={t}
                  onClick={() => setFilterType(t)}
                  className={`btn btn-sm ${filterType === t ? "btn-primary" : "btn-outline"}`}
                  style={{
                    fontSize: "10px",
                    padding: "4px 10px",
                    textTransform: "uppercase",
                  }}
                >
                  {t}
                </button>
              ))}
            </div>
          </div>

          <div
            style={{
              height: "24px",
              width: "1px",
              background: "var(--color-border)",
            }}
          />

          {/* Status filter */}
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <Shield size={13} style={{ color: "var(--color-neon)" }} />
            <span
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: "10px",
                color: "var(--color-text-ghost)",
                letterSpacing: "0.1em",
              }}
            >
              STATUS
            </span>
            <div style={{ display: "flex", gap: "6px" }}>
              {FILTER_STATUS.map((s) => (
                <button
                  key={s}
                  onClick={() => setFilterStatus(s)}
                  className={`btn btn-sm ${filterStatus === s ? "btn-primary" : "btn-outline"}`}
                  style={{
                    fontSize: "10px",
                    padding: "4px 10px",
                    textTransform: "uppercase",
                  }}
                >
                  {s.replace("_", " ")}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* ── VIOLATIONS GRID ── */}
      {loading ? (
        <div
          style={{ display: "flex", justifyContent: "center", padding: "80px" }}
        >
          <LoadingSpinner size={48} />
        </div>
      ) : violations.length === 0 ? (
        <motion.div
          initial={{ opacity: 0, scale: 0.97 }}
          animate={{ opacity: 1, scale: 1 }}
          className="card"
          style={{
            padding: "60px",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: "16px",
          }}
        >
          <div
            style={{
              width: "64px",
              height: "64px",
              borderRadius: "50%",
              background: "rgba(0,240,170,0.1)",
              border: "1px solid rgba(0,240,170,0.2)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <Globe size={28} style={{ color: "var(--color-neon)" }} />
          </div>
          <h3
            style={{
              fontFamily: "var(--font-display)",
              fontSize: "18px",
              letterSpacing: "0.1em",
              margin: 0,
            }}
          >
            NO VIOLATIONS DETECTED
          </h3>
          <p
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: "12px",
              color: "var(--color-text-ghost)",
              textAlign: "center",
              maxWidth: "400px",
            }}
          >
            {filterType !== "all" || filterStatus !== "all"
              ? "No violations match the current filters. Try clearing the filters."
              : "All monitored assets are clean. Run a crawl or submit a scan to detect violations."}
          </p>
        </motion.div>
      ) : (
        <AnimatePresence mode="popLayout">
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fill, minmax(360px, 1fr))",
              gap: "20px",
            }}
          >
            {violations.map((v, i) => (
              <motion.div
                key={v.violation_id || i}
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.95 }}
                transition={{ delay: i * 0.04 }}
              >
                <ViolationCard
                  violation={v}
                  onTakedownSent={handleTakedownSent}
                />
              </motion.div>
            ))}
          </div>
        </AnimatePresence>
      )}
    </motion.div>
  );
}
