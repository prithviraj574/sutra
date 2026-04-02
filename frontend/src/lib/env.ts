export type FirebaseClientConfig = {
  apiKey: string;
  authDomain: string;
  projectId: string;
  appId: string;
};

export type FrontendEnv = {
  apiBaseUrl: string;
  authMode: "firebase" | "dev_bypass";
  firebaseConfig: FirebaseClientConfig | null;
};

function readRequired(name: keyof ImportMetaEnv): string {
  return import.meta.env[name] ?? "";
}

export function readFrontendEnv(): FrontendEnv {
  const firebaseConfig = {
    apiKey: readRequired("VITE_FIREBASE_API_KEY"),
    authDomain: readRequired("VITE_FIREBASE_AUTH_DOMAIN"),
    projectId: readRequired("VITE_FIREBASE_PROJECT_ID"),
    appId: readRequired("VITE_FIREBASE_APP_ID"),
  };

  const isFirebaseConfigured = Object.values(firebaseConfig).every(Boolean);
  const authMode = import.meta.env.VITE_AUTH_MODE === "dev_bypass" ? "dev_bypass" : "firebase";

  return {
    apiBaseUrl: import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8001",
    authMode,
    firebaseConfig: authMode === "firebase" && isFirebaseConfigured ? firebaseConfig : null,
  };
}
