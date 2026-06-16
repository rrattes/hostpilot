import { createContext, type ReactNode, useCallback, useContext, useEffect, useMemo, useState } from "react";

import { logoutSession } from "../api/auth";
import { apiRequest } from "../api/client";
import type { CurrentAccess, CurrentUser, LoginResponse } from "./types";

const TOKEN_KEY = "hostpilot_access_token";

interface AuthContextValue {
  currentUser: CurrentUser | null;
  token: string | null;
  permissions: string[];
  hasPermission: (permission: string) => boolean;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [token, setToken] = useState<string | null>(() => sessionStorage.getItem(TOKEN_KEY));
  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null);
  const [permissions, setPermissions] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  const clearSession = useCallback(() => {
    sessionStorage.removeItem(TOKEN_KEY);
    setToken(null);
    setCurrentUser(null);
    setPermissions([]);
  }, []);

  useEffect(() => {
    window.addEventListener("hostpilot:auth-expired", clearSession);
    return () => window.removeEventListener("hostpilot:auth-expired", clearSession);
  }, [clearSession]);

  useEffect(() => {
    let isMounted = true;

    async function loadCurrentUser() {
      if (!token) {
        setCurrentUser(null);
        setPermissions([]);
        setIsLoading(false);
        return;
      }

      try {
        const [user, access] = await Promise.all([
          apiRequest<CurrentUser>("/api/core/auth/me", { token }),
          apiRequest<CurrentAccess>("/api/core/auth/permissions", { token }),
        ]);
        if (isMounted) {
          setCurrentUser(user);
          setPermissions(access.permissions);
        }
      } catch {
        if (isMounted) {
          clearSession();
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    }

    setIsLoading(true);
    void loadCurrentUser();

    return () => {
      isMounted = false;
    };
  }, [token]);

  const value = useMemo<AuthContextValue>(
    () => ({
      currentUser,
      token,
      permissions,
      hasPermission: (permission: string) => permissions.includes(permission),
      isAuthenticated: currentUser !== null,
      isLoading,
      login: async (email: string, password: string) => {
        const response = await apiRequest<LoginResponse>("/api/core/auth/login", {
          method: "POST",
          body: { email, password },
        });
        sessionStorage.setItem(TOKEN_KEY, response.access_token);
        setToken(response.access_token);
      },
      logout: async () => {
        const activeToken = token;
        clearSession();
        if (!activeToken) return;
        try {
          await logoutSession(activeToken);
        } catch {
          // Client state is already cleared; logout remains best-effort for stateless JWT audit.
        }
      },
    }),
    [clearSession, currentUser, isLoading, permissions, token],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === null) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return context;
}
