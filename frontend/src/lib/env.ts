export type FirebaseClientConfig = {
  apiKey: string;
  authDomain: string;
  projectId: string;
  appId: string;
};

export type FrontendEnv = {
  apiBaseUrl: string;
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

  return {
    apiBaseUrl: import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000",
    firebaseConfig: isFirebaseConfigured ? firebaseConfig : null,
  };
}
