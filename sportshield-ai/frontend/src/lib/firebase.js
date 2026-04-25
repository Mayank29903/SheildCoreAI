import { initializeApp } from 'firebase/app';
import { getAuth, signInWithPopup, signOut, GoogleAuthProvider } from 'firebase/auth';
import {
  getFirestore,
  collection,
  doc,
  getDoc,
  getDocs,
  addDoc,
  setDoc,
  updateDoc,
  deleteDoc,
  query,
  where,
  orderBy,
  limit,
  startAfter,
  onSnapshot,
  serverTimestamp,
  increment,
  Timestamp,
  writeBatch,
  runTransaction,
  documentId
} from 'firebase/firestore';
import { getDatabase, ref, onValue, set, push, update, remove, off } from 'firebase/database';
import { getStorage } from 'firebase/storage';

const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
  appId: import.meta.env.VITE_FIREBASE_APP_ID,
  databaseURL: import.meta.env.VITE_FIREBASE_DATABASE_URL
};

const AUTH_SESSION_STORAGE_KEY = 'sportshield.authSession';
const GUEST_USER = {
  uid: 'local-preview-user',
  displayName: 'Local Preview User',
  email: 'preview@local.sportshield',
  isGuest: true
};

const app = initializeApp(firebaseConfig);
const db = getFirestore(app);
const rtdb = getDatabase(app);
const storage = getStorage(app);

let auth = null;
let googleProvider = null;
let authConfigCheckPromise = null;
const authListeners = new Set();

export const hasFirebaseClientConfig = [
  firebaseConfig.apiKey,
  firebaseConfig.authDomain,
  firebaseConfig.projectId,
  firebaseConfig.appId,
].every(Boolean);

function getStoredSessionUser() {
  if (typeof window === 'undefined') {
    return null;
  }

  const raw = window.sessionStorage.getItem(AUTH_SESSION_STORAGE_KEY);
  if (!raw) {
    return null;
  }

  try {
    return JSON.parse(raw);
  } catch {
    window.sessionStorage.removeItem(AUTH_SESSION_STORAGE_KEY);
    return null;
  }
}

let currentUser = getStoredSessionUser();

function setStoredSessionUser(user) {
  if (typeof window === 'undefined') {
    return;
  }

  if (user) {
    window.sessionStorage.setItem(AUTH_SESSION_STORAGE_KEY, JSON.stringify(user));
  } else {
    window.sessionStorage.removeItem(AUTH_SESSION_STORAGE_KEY);
  }
}

function emitAuthChange(user) {
  currentUser = user;
  setStoredSessionUser(user);
  authListeners.forEach((listener) => listener(user));
}

function serializeUser(user) {
  if (!user) {
    return null;
  }

  return {
    uid: user.uid,
    displayName: user.displayName || user.email || 'Authenticated User',
    email: user.email || '',
    isGuest: Boolean(user.isGuest)
  };
}

function getAuthInstance() {
  if (!auth) {
    auth = getAuth(app);
  }
  return auth;
}

function getGoogleProvider() {
  if (!googleProvider) {
    googleProvider = new GoogleAuthProvider();
    googleProvider.setCustomParameters({ prompt: 'select_account' });
  }
  return googleProvider;
}

function normalizeAuthError(error) {
  const code = error?.code || '';
  const rawMessage = error?.message || '';

  if (
    code === 'auth/configuration-not-found' ||
    rawMessage.includes('CONFIGURATION_NOT_FOUND')
  ) {
    const friendly = new Error(
      'Firebase Authentication is not configured for this project yet. Enable a sign-in provider in Firebase Authentication or use Local Preview.'
    );
    friendly.code = code || 'auth/configuration-not-found';
    return friendly;
  }

  if (code === 'auth/unauthorized-domain') {
    const friendly = new Error(
      'This hostname is not authorized in Firebase Authentication. Add localhost to the authorized domains list.'
    );
    friendly.code = code;
    return friendly;
  }

  return error instanceof Error ? error : new Error(rawMessage || 'Authentication failed');
}

async function ensureFirebaseAuthConfigured() {
  if (!hasFirebaseClientConfig) {
    throw new Error('Firebase client configuration is incomplete. Check the VITE_FIREBASE_* values in frontend/.env.');
  }

  if (!authConfigCheckPromise) {
    const apiKey = encodeURIComponent(firebaseConfig.apiKey);
    const url = `https://www.googleapis.com/identitytoolkit/v3/relyingparty/getProjectConfig?key=${apiKey}`;

    authConfigCheckPromise = fetch(url)
      .then(async (response) => {
        if (response.ok) {
          return true;
        }

        let payload = null;
        try {
          payload = await response.json();
        } catch {
          payload = null;
        }

        const message = payload?.error?.message || `HTTP ${response.status}`;
        throw normalizeAuthError({ code: 'auth/configuration-not-found', message });
      })
      .catch((error) => {
        authConfigCheckPromise = null;
        throw normalizeAuthError(error);
      });
  }

  return authConfigCheckPromise;
}

export const signInWithGoogle = async () => {
  await ensureFirebaseAuthConfigured();

  try {
    const result = await signInWithPopup(getAuthInstance(), getGoogleProvider());
    const user = serializeUser(result.user);
    emitAuthChange(user);
    return { user };
  } catch (error) {
    throw normalizeAuthError(error);
  }
};

export const continueAsGuest = async () => {
  emitAuthChange(GUEST_USER);
  return { user: GUEST_USER };
};

export const logOut = async () => {
  if (auth) {
    try {
      await signOut(auth);
    } catch {
      // Local session cleanup still happens below.
    }
  }

  emitAuthChange(null);
};

export const onAuthChange = (cb) => {
  cb(currentUser);
  authListeners.add(cb);
  return () => authListeners.delete(cb);
};

export {
  auth,
  db,
  rtdb,
  storage,
  googleProvider,
  collection,
  doc,
  getDoc,
  getDocs,
  addDoc,
  setDoc,
  updateDoc,
  deleteDoc,
  query,
  where,
  orderBy,
  limit,
  startAfter,
  onSnapshot,
  serverTimestamp,
  increment,
  Timestamp,
  writeBatch,
  runTransaction,
  documentId,
  ref,
  onValue,
  set,
  push,
  update,
  remove,
  off
};
