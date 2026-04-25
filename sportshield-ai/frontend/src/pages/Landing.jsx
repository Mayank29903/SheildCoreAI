// SportShield AI | Google Solution Challenge 2026 | First Prize Target
/** WHY: The primary gateway. Handles Auth redirection automatically ensuring organizers route straight into mission control. */
import React from 'react';
import { Navigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { useAuth } from '../hooks/useAuth';
import { ShieldAlert, Fingerprint } from 'lucide-react';
import PageLoadingSpinner from '../components/layout/PageLoadingSpinner';

export default function Landing() {
  const { user, loading, signIn, continueAsGuest } = useAuth();

  const handleSignIn = async () => {
    try {
      await signIn();
    } catch (error) {
      toast.error(error?.message || 'Authentication failed');
    }
  };

  const handleLocalPreview = async () => {
    try {
      await continueAsGuest();
    } catch (error) {
      toast.error(error?.message || 'Local preview unavailable');
    }
  };

  if (loading) return <PageLoadingSpinner text="Establishing Secure Connection..." />;
  if (user) return <Navigate to="/dashboard" replace />;

  return (
    <div className="page" style={{ alignItems: 'center', justifyContent: 'center', textAlign: 'center', background: 'radial-gradient(circle at center, rgba(0,212,170,0.05) 0%, var(--color-void) 70%)' }}>
      <div className="slide-up max-w-[600px]">
        <div style={{ marginBottom: '40px', display: 'flex', justifyContent: 'center', position: 'relative' }}>
          <div style={{ position: 'absolute', inset: 0, filter: 'blur(40px)', background: 'var(--color-neon)', opacity: 0.2, borderRadius: '50%' }} />
          <ShieldAlert size={80} style={{ color: 'var(--color-neon)' }} className="pulse-safe" />
        </div>
        
        <h1 style={{ fontFamily: 'var(--font-display)', fontSize: '48px', fontWeight: 900, letterSpacing: '0.1em', marginBottom: '16px', textShadow: '0 0 20px rgba(0,212,170,0.4)' }}>
          SPORTSHIELD<span style={{ color: 'var(--color-neon)' }}>.AI</span>
        </h1>
        
        <p style={{ fontFamily: 'var(--font-mono)', fontSize: '14px', color: 'var(--color-text-dim)', marginBottom: '48px', lineHeight: 1.6, letterSpacing: '0.05em' }}>
          Real-time Sports Media Rights Intelligence.<br/>
          Proprietary Contextual DNA. Cryptographic Provenance.
        </p>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', alignItems: 'center' }}>
          <button onClick={handleSignIn} className="btn" style={{ background: 'var(--color-neon)', color: 'var(--color-deep)', padding: '16px 32px', fontSize: '16px', boxShadow: '0 0 30px rgba(0,212,170,0.4)', minWidth: '280px' }}>
            <Fingerprint size={20} />
            SIGN IN WITH GOOGLE
          </button>
          <button onClick={handleLocalPreview} className="btn btn-outline" style={{ minWidth: '280px' }}>
            OPEN LOCAL PREVIEW
          </button>
        </div>
        
        <div style={{ marginTop: '64px', display: 'flex', justifyContent: 'center', gap: '32px' }}>
          {['SDG 8: DECENT WORK', 'SDG 16: STRONG INSTITUTIONS'].map(sdg => (
            <span key={sdg} className="badge badge-neutral" style={{ letterSpacing: '0.1em' }}>{sdg}</span>
          ))}
        </div>
      </div>
    </div>
  );
}
