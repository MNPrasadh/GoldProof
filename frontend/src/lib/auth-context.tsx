"use client";

import React, { createContext, useCallback, useContext, useEffect, useState } from "react";
import { apiRequest, getStoredToken, setStoredToken } from "./api";
import { Language, User } from "./types";

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  language: Language;
  setLanguage: (lang: Language) => void;
  loginWithCredentials: (email: string, password: string) => Promise<User>;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);
const LANG_KEY = "goldproof_ui_lang";

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [language, setLanguageState] = useState<Language>("en");

  const setLanguage = useCallback((lang: Language) => {
    setLanguageState(lang);
    if (typeof window !== "undefined") {
      localStorage.setItem(LANG_KEY, lang);
    }
  }, []);

  const refreshUser = useCallback(async () => {
    const token = getStoredToken();
    if (!token) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      const me = await apiRequest<User>("/api/auth/me");
      setUser(me);
      if (typeof window !== "undefined" && !localStorage.getItem(LANG_KEY)) {
        setLanguageState(me.preferred_language || "en");
      }
    } catch {
      setStoredToken(null);
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (typeof window !== "undefined") {
      const savedLang = localStorage.getItem(LANG_KEY);
      if (savedLang === "en" || savedLang === "ta") {
        setLanguageState(savedLang);
      }
      if ("serviceWorker" in navigator) {
        navigator.serviceWorker.register("/sw.js").catch(() => undefined);
      }
    }
    refreshUser();
  }, [refreshUser]);

  const loginWithCredentials = useCallback(
    async (email: string, password: string): Promise<User> => {
      const resp = await apiRequest<{ access_token: string; user: User }>("/api/auth/login", {
        method: "POST",
        skipAuth: true,
        body: JSON.stringify({ email, password }),
      });
      setStoredToken(resp.access_token);
      setUser(resp.user);
      setLanguage(resp.user.preferred_language || "en");
      return resp.user;
    },
    [setLanguage]
  );

  const logout = useCallback(() => {
    setStoredToken(null);
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        language,
        setLanguage,
        loginWithCredentials,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return ctx;
}
