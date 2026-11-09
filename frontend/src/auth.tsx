import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import { api, getToken, setToken } from "./api";
import type { User } from "./types";

interface AuthState {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, name: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    async function restore(): Promise<void> {
      if (!getToken()) {
        setLoading(false);
        return;
      }
      try {
        const profile = await api.profile();
        if (!cancelled) {
          setUser(profile);
        }
      } catch {
        setToken(null);
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    void restore();
    return () => {
      cancelled = true;
    };
  }, []);

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
  }, []);

  useEffect(() => {
    window.addEventListener("tms:unauthorized", logout);
    return () => window.removeEventListener("tms:unauthorized", logout);
  }, [logout]);

  const login = useCallback(async (email: string, password: string) => {
    const token = await api.login(email, password);
    setToken(token.access_token);
    setUser(await api.profile());
  }, []);

  const register = useCallback(async (email: string, password: string, name: string) => {
    await api.register(email, password, name);
    const token = await api.login(email, password);
    setToken(token.access_token);
    setUser(await api.profile());
  }, []);

  const value = useMemo(
    () => ({ user, loading, login, register, logout }),
    [user, loading, login, register, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth должен вызываться внутри AuthProvider");
  }
  return context;
}
