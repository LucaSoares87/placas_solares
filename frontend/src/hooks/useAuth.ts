import { useCallback, useMemo, useState } from "react";

import {
  getStoredToken,
  getStoredUser,
  isAuthenticated,
  login,
  logout,
  type AuthUser,
  type LoginPayload
} from "../services/authService";

export function useAuth() {
  const [token, setToken] = useState<string | null>(() => getStoredToken());
  const [user, setUser] = useState<AuthUser | null>(() => getStoredUser());
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const authenticated = useMemo(() => Boolean(token) && isAuthenticated(), [token]);

  const signIn = useCallback(async (payload: LoginPayload) => {
    setIsLoading(true);
    setError(null);

    try {
      const result = await login(payload);
      setToken(result.access_token);
      setUser(result.user ?? getStoredUser());
      return result;
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Não foi possível realizar login.";
      setError(message);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const signOut = useCallback(() => {
    logout();
    setToken(null);
    setUser(null);
  }, []);

  return {
    token,
    user,
    authenticated,
    isLoading,
    error,
    signIn,
    signOut
  };
}