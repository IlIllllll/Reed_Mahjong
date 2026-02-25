import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

const API_BASE_URL = "http://localhost:8000/api";
const AUTH_STORAGE_KEY = "mahjong_auth_state";
const defaultAuthState = {
  token: null,
  user: null,
  stats: null,
};

const AuthContext = createContext(null);

function loadStoredAuthState() {
  const stored = localStorage.getItem(AUTH_STORAGE_KEY);
  if (!stored) {
    return defaultAuthState;
  }

  try {
    const parsed = JSON.parse(stored);
    if (!parsed.token || !parsed.user?.username) {
      return defaultAuthState;
    }
    return parsed;
  } catch (error) {
    return defaultAuthState;
  }
}

async function callAuthApi(path, payload) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  return {
    ok: response.ok,
    status: response.status,
    data,
  };
}

export const useAuth = () => useContext(AuthContext);

export const useUsername = () => {
  const auth = useAuth();
  return auth?.user?.username || "";
};

export const UsernameProvider = ({ children }) => {
  const [authState, setAuthState] = useState(loadStoredAuthState);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (!authState.token) {
      localStorage.removeItem(AUTH_STORAGE_KEY);
      return;
    }
    localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(authState));
  }, [authState]);

  const applyAuthResponse = useCallback((responseData) => {
    setAuthState({
      token: responseData.token,
      user: responseData.user,
      stats: responseData.stats,
    });
  }, []);

  const login = useCallback(async (username, password) => {
    setIsLoading(true);
    try {
      const result = await callAuthApi("/auth/login/", { username, password });
      if (!result.ok) {
        return { ok: false, message: result.data.message || "登录失败。" };
      }
      applyAuthResponse(result.data);
      return { ok: true };
    } finally {
      setIsLoading(false);
    }
  }, [applyAuthResponse]);

  const register = useCallback(async (username, password) => {
    setIsLoading(true);
    try {
      const result = await callAuthApi("/auth/register/", { username, password });
      if (!result.ok) {
        return { ok: false, message: result.data.message || "注册失败。" };
      }
      applyAuthResponse(result.data);
      return { ok: true };
    } finally {
      setIsLoading(false);
    }
  }, [applyAuthResponse]);

  const refreshProfile = useCallback(async () => {
    if (!authState.token) {
      return false;
    }

    const response = await fetch(`${API_BASE_URL}/auth/me/`, {
      headers: {
        Authorization: `Bearer ${authState.token}`,
      },
    });

    if (!response.ok) {
      setAuthState(defaultAuthState);
      return false;
    }

    const data = await response.json();
    setAuthState((prev) => ({
      ...prev,
      user: data.user,
      stats: data.stats,
    }));
    return true;
  }, [authState.token]);

  useEffect(() => {
    if (authState.token) {
      refreshProfile();
    }
  }, [authState.token, refreshProfile]);

  const logout = useCallback(() => {
    setAuthState(defaultAuthState);
  }, []);

  const contextValue = useMemo(
    () => ({
      token: authState.token,
      user: authState.user,
      stats: authState.stats,
      isAuthenticated: Boolean(authState.token && authState.user),
      isLoading,
      login,
      register,
      refreshProfile,
      logout,
    }),
    [authState, isLoading, login, logout, refreshProfile, register]
  );

  return <AuthContext.Provider value={contextValue}>{children}</AuthContext.Provider>;
};
