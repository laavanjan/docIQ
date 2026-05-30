"use client";

import { useRouter } from "next/navigation";
import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";

import * as api from "@/lib/api";
import { tokenStore } from "@/lib/auth";
import { logger } from "@/lib/logger";
import type { UserRead } from "@/lib/types";

interface AuthContextValue {
  user: UserRead | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserRead | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    (async () => {
      if (!tokenStore.getAccess()) {
        setLoading(false);
        return;
      }
      try {
        setUser(await api.fetchMe());
      } catch {
        tokenStore.clear();
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const login = useCallback(
    async (email: string, password: string) => {
      await api.login(email, password);
      setUser(await api.fetchMe());
      logger.info("logged in");
      router.push("/documents");
    },
    [router],
  );

  const register = useCallback(
    async (email: string, password: string) => {
      await api.register(email, password);
      await api.login(email, password);
      setUser(await api.fetchMe());
      router.push("/documents");
    },
    [router],
  );

  const logout = useCallback(() => {
    tokenStore.clear();
    setUser(null);
    router.push("/login");
  }, [router]);

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}
