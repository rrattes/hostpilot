import { createContext, type ReactNode, useContext, useEffect, useMemo, useState } from "react";

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
  logout: () => void;
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

  useEffect(() => {
    let isMounted = true;

    async function loadCurrentUser() {
      if (!token) {
        setCurrentUser(null);
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
        sessionStorage.removeItem(TOKEN_KEY);
        if (isMounted) {
          setToken(null);
          setCurrentUser(null);
          setPermissions([]);
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
      logout: () => {
        sessionStorage.removeItem(TOKEN_KEY);
        setToken(null);
        setCurrentUser(null);
        setPermissions([]);
      },
    }),
    [currentUser, isLoading, permissions],
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
