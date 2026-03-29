import {
  type PropsWithChildren,
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import {
  onAuthStateChanged,
  signInWithPopup,
  signOut,
  type User,
} from "firebase/auth";

import { firebaseAuth, firebaseEnabled, googleProvider } from "../../lib/firebase";

type AuthContextValue = {
  firebaseEnabled: boolean;
  loading: boolean;
  user: User | null;
  getAccessToken: () => Promise<string | null>;
  signIn: () => Promise<void>;
  signOutUser: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: PropsWithChildren) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!firebaseEnabled || !firebaseAuth) {
      setLoading(false);
      return;
    }

    return onAuthStateChanged(firebaseAuth, (nextUser) => {
      setUser(nextUser);
      setLoading(false);
    });
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      firebaseEnabled,
      loading,
      user,
      getAccessToken: async () => (user ? user.getIdToken() : null),
      signIn: async () => {
        if (!firebaseEnabled || !firebaseAuth || !googleProvider) {
          throw new Error("Firebase is not configured for this frontend.");
        }
        await signInWithPopup(firebaseAuth, googleProvider);
      },
      signOutUser: async () => {
        if (!firebaseAuth) {
          return;
        }
        await signOut(firebaseAuth);
      },
    }),
    [loading, user],
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
