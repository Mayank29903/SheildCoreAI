// ShieldCore AI | Google Solution Challenge 2026 | First Prize Target
/** WHY: Core routing component. Added /assets route for Content Registry page. */
import React, { Suspense, lazy } from "react";
import { Routes, Route, useLocation, Navigate, useNavigate } from "react-router-dom";
import { AnimatePresence, motion } from "framer-motion";
import { Toaster } from "react-hot-toast";

import Sidebar from "./components/layout/Sidebar";
import TopBar from "./components/layout/TopBar";
import ProtectedRoute from "./components/layout/ProtectedRoute";
import ErrorBoundary from "./components/ui/ErrorBoundary";
import PageLoadingSpinner from "./components/layout/PageLoadingSpinner";

const Landing = lazy(() => import("./pages/Landing"));
const Dashboard = lazy(() => import("./pages/Dashboard"));
const RegisterAsset = lazy(() => import("./pages/RegisterAsset"));
const ScanContent = lazy(() => import("./pages/ScanContent"));
const ViolationsFeed = lazy(() => import("./pages/ViolationsFeed"));
const EvidenceReport = lazy(() => import("./pages/EvidenceReport"));
const AssetsRegistry = lazy(() => import("./pages/AssetsRegistry"));

const PageTransition = ({ children }) => (
  <motion.div
    initial={{ opacity: 0, x: 10 }}
    animate={{ opacity: 1, x: 0 }}
    exit={{ opacity: 0, x: -10 }}
    transition={{ duration: 0.25 }}
  >
    {children}
  </motion.div>
);

const AuthenticatedLayout = ({ children }) => (
  <div
    style={{
      display: "flex",
      height: "100vh",
      width: "100vw",
      overflow: "hidden",
    }}
  >
    <Sidebar />
    <div
      style={{ flex: 1, display: "flex", flexDirection: "column", minWidth: 0 }}
    >
      <TopBar />
      <main className="page" style={{ overflowY: "auto" }}>
        <div className="page-content">
          <ErrorBoundary>
            <Suspense
              fallback={
                <PageLoadingSpinner text="ASSEMBLING INTEL MODULES..." />
              }
            >
              {children}
            </Suspense>
          </ErrorBoundary>
        </div>
      </main>
    </div>
  </div>
);

const wrap = (Component) => (
  <AuthenticatedLayout>
    <PageTransition>
      <Component />
    </PageTransition>
  </AuthenticatedLayout>
);

export default function App() {
  const location = useLocation();
  const navigate = useNavigate();

  React.useEffect(() => {
    const handleKeyDown = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        navigate("/scan");
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [navigate]);

  return (
    <>
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: "var(--color-surface)",
            color: "var(--color-text)",
            fontFamily: "var(--font-mono)",
            fontSize: "12px",
            border: "1px solid var(--color-border)",
            borderRadius: "4px",
          },
          success: {
            iconTheme: {
              primary: "var(--color-neon)",
              secondary: "var(--color-deep)",
            },
          },
          error: {
            iconTheme: {
              primary: "var(--color-threat)",
              secondary: "var(--color-deep)",
            },
          },
        }}
      />
      <AnimatePresence mode="wait">
        <Routes location={location} key={location.pathname}>
          {/* Public */}
          <Route
            path="/"
            element={
              <Suspense fallback={<PageLoadingSpinner />}>
                <PageTransition>
                  <Landing />
                </PageTransition>
              </Suspense>
            }
          />

          {/* Protected */}
          <Route element={<ProtectedRoute />}>
            <Route path="/dashboard" element={wrap(Dashboard)} />
            <Route path="/scan" element={wrap(ScanContent)} />
            <Route path="/violations" element={wrap(ViolationsFeed)} />
            <Route path="/assets" element={wrap(AssetsRegistry)} />
            <Route path="/register" element={wrap(RegisterAsset)} />
            <Route path="/report/:scanId" element={wrap(EvidenceReport)} />
          </Route>

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AnimatePresence>
    </>
  );
}
