import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";

import { createApiClient } from "../../lib/api";
import { readFrontendEnv } from "../../lib/env";
import { useAuth } from "./AuthProvider";

export function useApiClient() {
  const auth = useAuth();
  const env = useMemo(() => readFrontendEnv(), []);

  return useMemo(
    () =>
      createApiClient({
        baseUrl: env.apiBaseUrl,
        getAccessToken: auth.getAccessToken,
      }),
    [auth.getAccessToken, env.apiBaseUrl],
  );
}

export function useBackendSession() {
  const auth = useAuth();
  const api = useApiClient();

  return useQuery({
    queryKey: ["backend-session", auth.user?.uid],
    queryFn: () => api.readSession(),
    enabled: !!auth.user,
  });
}
