import { api } from "./api";

export type LoginPayload = {
  matricula: string;
  password: string;
};

export type AuthUser = {
  id?: number;
  nome?: string;
  name?: string;
  email?: string;
  matricula?: string;
  perfil?: string;
};

export type TokenData = {
  access_token: string;
  token_type?: string;
  expires_in?: number;
  user?: AuthUser;
};

type ApiResponse<T> = {
  success?: boolean;
  data?: T;
  error?: string;
  code?: string;
};

const TOKEN_KEY = "access_token";
const USER_KEY = "auth_user";

export async function login(payload: LoginPayload): Promise<TokenData> {
  const response = await api.post<ApiResponse<TokenData>>("/api/v1/auth/login", payload);
  const tokenData = response.data.data;

  if (!tokenData?.access_token) {
    throw new Error(response.data.error ?? "Falha ao autenticar usuário.");
  }

  localStorage.setItem(TOKEN_KEY, tokenData.access_token);

  if (tokenData.user) {
    localStorage.setItem(USER_KEY, JSON.stringify(tokenData.user));
  }

  return tokenData;
}

export function logout() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
}

export function getStoredToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function getStoredUser(): AuthUser | null {
  const stored = localStorage.getItem(USER_KEY);

  if (!stored) {
    return null;
  }

  try {
    return JSON.parse(stored) as AuthUser;
  } catch {
    localStorage.removeItem(USER_KEY);
    return null;
  }
}

export function isAuthenticated(): boolean {
  return Boolean(getStoredToken());
}