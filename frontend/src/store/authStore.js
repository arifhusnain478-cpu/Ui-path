import { create } from "zustand";
import { login as loginRequest } from "../api/auth.js";

const token_key = "qualitrace_token";
const user_key = "qualitrace_user";

function readStoredUser() {
  const stored_user = window.localStorage.getItem(user_key);

  if (!stored_user) {
    return null;
  }

  try {
    return JSON.parse(stored_user);
  } catch {
    window.localStorage.removeItem(user_key);
    return null;
  }
}

function readStoredToken() {
  return window.localStorage.getItem(token_key);
}

function persistAuth(token, user) {
  window.localStorage.setItem(token_key, token);
  window.localStorage.setItem(user_key, JSON.stringify(user));
}

export const useAuthStore = create((set) => ({
  token: readStoredToken(),
  user: readStoredUser(),
  isAuthenticated: Boolean(readStoredToken()),
  isHydrated: false,
  loading: false,
  error: null,
  setToken: (token) => {
    window.localStorage.setItem(token_key, token);
    set({ token, isAuthenticated: Boolean(token), error: null });
  },
  setUser: (user) => {
    if (user) {
      window.localStorage.setItem(user_key, JSON.stringify(user));
    } else {
      window.localStorage.removeItem(user_key);
    }

    set({ user });
  },
  clearToken: () => {
    window.localStorage.removeItem(token_key);
    set({ token: null, isAuthenticated: false, error: null });
  },
  logout: () => {
    window.localStorage.removeItem(token_key);
    window.localStorage.removeItem(user_key);
    set({
      token: null,
      user: null,
      isAuthenticated: false,
      loading: false,
      error: null,
      isHydrated: true,
    });
  },
  hydrateFromStorage: () => {
    const token = readStoredToken();
    const user = readStoredUser();
    set({ token, user, isAuthenticated: Boolean(token), isHydrated: true });
  },
  login: async ({ email, password }) => {
    set({ loading: true, error: null });

    try {
      const { token, user } = await loginRequest({ email, password });
      persistAuth(token, user);
      set({
        token,
        user,
        isAuthenticated: true,
        loading: false,
        error: null,
        isHydrated: true,
      });
      return { token, user };
    } catch (error) {
      window.localStorage.removeItem(token_key);
      window.localStorage.removeItem(user_key);

      const message =
        error?.response?.data && typeof error.response.data === "string"
          ? error.response.data
          : "Login failed. Check your email and password.";

      set({
        token: null,
        user: null,
        isAuthenticated: false,
        loading: false,
        error: message,
        isHydrated: true,
      });

      throw error;
    }
  },
  clearError: () => set({ error: null }),
}));
