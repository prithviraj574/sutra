import { initializeApp } from "firebase/app";
import { getAuth, GoogleAuthProvider } from "firebase/auth";

import { readFrontendEnv } from "./env";

const env = readFrontendEnv();

export const firebaseEnabled = env.firebaseConfig !== null;

export const firebaseApp = env.firebaseConfig ? initializeApp(env.firebaseConfig) : null;
export const firebaseAuth = firebaseApp ? getAuth(firebaseApp) : null;
export const googleProvider = firebaseApp ? new GoogleAuthProvider() : null;
