"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { apiFetch, clearToken, getToken, setToken } from "./api";
import { clearPersistedSWRCache } from "@/components/SWRProvider";

interface AuthContextValue {
  isAuthenticated: boolean | null; // null = todavía no se ha comprobado (evita parpadeo)
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, inviteCode?: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState<boolean | null>(null);

  useEffect(() => {
    // localStorage solo existe en cliente: hay que leerlo tras montar para
    // no desincronizar el render SSR (que siempre ve "sin token").
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setIsAuthenticated(getToken() !== null);
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const result = await apiFetch<{ access_token: string }>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    setToken(result.access_token);
    setIsAuthenticated(true);
  }, []);

  const register = useCallback(async (email: string, password: string, inviteCode?: string) => {
    const result = await apiFetch<{ access_token: string }>("/api/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password, invite_code: inviteCode || null }),
    });
    setToken(result.access_token);
    setIsAuthenticated(true);
  }, []);

  const logout = useCallback(() => {
    clearToken();
    clearPersistedSWRCache();
    setIsAuthenticated(false);
  }, []);

  return <AuthContext.Provider value={{ isAuthenticated, login, register, logout }}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth debe usarse dentro de AuthProvider");
  return ctx;
}
