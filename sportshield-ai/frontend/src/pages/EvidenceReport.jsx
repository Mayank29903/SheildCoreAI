// SportShield AI | Google Solution Challenge 2026 | First Prize Target
/** WHY: Fills the direct /report/:id routing link generating immutable proof directly out from isolated parameters securely mapping DB hashes. */
import React, { useEffect, useState } from "react";
import { useParams, useLocation } from "react-router-dom";
import { doc, getDoc } from "firebase/firestore";
import { db } from "../lib/firebase";
import PageLoadingSpinner from "../components/layout/PageLoadingSpinner";
import ScanResults from "../components/features/ScanResults";
import { FileText } from "lucide-react";

export default function EvidenceReport() {
  const { scanId } = useParams();
  const location = useLocation();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const demoResult = location.state?.demoResult || null;

  useEffect(() => {
    let active = true;
    if (!scanId) return;
    if (demoResult) {
      setData(demoResult);
      setLoading(false);
      return () => {
        active = false;
      };
    }
    getDoc(doc(db, "scans", scanId))
      .then((snap) => {
        if (active) {
          if (snap.exists()) setData(snap.data());
          setLoading(false);
        }
      })
      .catch(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [scanId]);

  if (loading)
    return <PageLoadingSpinner text="RETRIEVING CRYPTOGRAPHIC EVIDENCE..." />;
  if (!data)
    return (
      <div
        className="card"
        style={{
          display: "flex",
          flexDirection: "column",
          gap: "16px",
          maxWidth: "720px",
        }}
      >
        <h2
          style={{
            fontFamily: "var(--font-display)",
            fontSize: "20px",
            letterSpacing: "0.08em",
          }}
        >
          REPORT NOT READY
        </h2>
        <p
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: "12px",
            color: "var(--color-text-dim)",
          }}
        >
          The legal report for scan ID <strong>{scanId}</strong> was not found in
          Firestore yet. If this came from a live scan, wait a few seconds and
          try again. Demo sample reports open directly from the demo gallery.
        </p>
      </div>
    );

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
        <FileText size={24} style={{ color: "var(--color-neon)" }} />
        <div>
          <h2
            style={{
              fontFamily: "var(--font-display)",
              fontSize: "20px",
              letterSpacing: "0.1em",
            }}
          >
            DECENTRALIZED EVIDENCE FILE
          </h2>
          <span
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: "11px",
              color: "var(--color-text-ghost)",
            }}
          >
            ID: {scanId}
          </span>
        </div>
      </div>
      <ScanResults scanResult={data} />
    </div>
  );
}
