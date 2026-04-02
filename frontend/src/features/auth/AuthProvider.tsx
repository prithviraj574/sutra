import {
  type PropsWithChildren,
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import {
  onIdTokenChanged,
  signInWithPopup,
  signOut,
  type AuthError,
} from "firebase/auth";

import { firebaseAuth, firebaseEnabled, frontendAuthMode, googleProvider } from "../../lib/firebase";

type AuthUser = {
  uid: string;
};

const DEV_BYPASS_USER_UID = "00000000-0000-0000-0000-000000000000";

type AuthContextValue = {
  authMode: "firebase" | "dev_bypass";
  firebaseEnabled: boolean;
  loading: boolean;
  authError: string | null;
  tokenVersion: number;
  user: AuthUser | null;
  getAccessToken: () => Promise<string | null>;
  signIn: () => Promise<void>;
  signOutUser: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: PropsWithChildren) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [authError, setAuthError] = useState<string | null>(null);
  const [tokenVersion, setTokenVersion] = useState(0);

  useEffect(() => {
    if (frontendAuthMode === "dev_bypass") {
      setAuthError(null);
      setUser({ uid: DEV_BYPASS_USER_UID });
      setTokenVersion((current) => current + 1);
      setLoading(false);
      return;
    }

    if (!firebaseEnabled || !firebaseAuth) {
      setLoading(false);
      return;
    }

    return onIdTokenChanged(firebaseAuth, (nextUser) => {
      setAuthError(null);
      setUser(nextUser ? { uid: nextUser.uid } : null);
      setTokenVersion((current) => current + 1);
      setLoading(false);
    });
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      authMode: frontendAuthMode,
      firebaseEnabled,
      loading,
      authError,
      tokenVersion,
      user,
      getAccessToken: async () => {
        if (frontendAuthMode === "dev_bypass") {
          return null;
        }
        return firebaseAuth?.currentUser ? firebaseAuth.currentUser.getIdToken() : null;
      },
      signIn: async () => {
        if (frontendAuthMode === "dev_bypass") {
          setAuthError(null);
          setUser({ uid: DEV_BYPASS_USER_UID });
          setTokenVersion((current) => current + 1);
          return;
        }
        if (!firebaseEnabled || !firebaseAuth || !googleProvider) {
          throw new Error("Firebase is not configured for this frontend.");
        }
        setAuthError(null);
        try {
          const credential = await signInWithPopup(firebaseAuth, googleProvider);
          await credential.user.getIdToken(true);
        } catch (error) {
          const nextError =
            typeof error === "object" &&
            error !== null &&
            "message" in error &&
            typeof (error as AuthError).message === "string"
              ? (error as AuthError).message
              : "Google sign-in did not complete.";
          setAuthError(nextError);
          throw error;
        }
      },
      signOutUser: async () => {
        if (frontendAuthMode === "dev_bypass") {
          setAuthError(null);
          setUser(null);
          setTokenVersion((current) => current + 1);
          return;
        }
        if (!firebaseAuth) {
          return;
        }
        setAuthError(null);
        await signOut(firebaseAuth);
      },
    }),
    [authError, loading, tokenVersion, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider.");
  }
  return context;
}
