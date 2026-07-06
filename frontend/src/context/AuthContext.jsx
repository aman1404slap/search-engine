import { createContext, useContext, useEffect, useState } from "react";
import { api } from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(undefined); // undefined = checking, null = logged out
  const [error, setError] = useState(null);

  useEffect(() => {
    api
      .me()
      .then((res) => setUser(res.username))
      .catch(() => setUser(null));
  }, []);

  async function login(username, password) {
    setError(null);
    try {
      await api.getCsrf();
      const res = await api.login(username, password);
      setUser(res.username);
    } catch (err) {
      setError(err.message || "Login failed");
      throw err;
    }
  }

  async function logout() {
    try {
      await api.logout();
    } finally {
      setUser(null);
    }
  }

  return (
    <AuthContext.Provider value={{ user, checking: user === undefined, error, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
