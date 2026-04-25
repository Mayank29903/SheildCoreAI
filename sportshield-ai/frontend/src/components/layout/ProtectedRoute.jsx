// SportShield AI | Google Solution Challenge 2026 | First Prize Target
/** WHY: Secures React Router paths to ensure only authenticated organizers can view Intel panels. */
import React from 'react';
import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import PageLoadingSpinner from './PageLoadingSpinner';

export default function ProtectedRoute() {
  const { user, loading } = useAuth();
  
  if (loading) return <PageLoadingSpinner text="Authenticating Operator..." />;
  return user ? <Outlet /> : <Navigate to="/" replace />;
}
