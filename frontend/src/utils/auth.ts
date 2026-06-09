const AUTH_KEY = 'smart_camara_auth_v1';
const VALID_USER = 'admin';
const VALID_PASS = 'admin4399';

export function isAuthenticated(): boolean {
  try {
    return localStorage.getItem(AUTH_KEY) === 'ok';
  } catch {
    return false;
  }
}

export function login(username: string, password: string): boolean {
  if (username === VALID_USER && password === VALID_PASS) {
    localStorage.setItem(AUTH_KEY, 'ok');
    return true;
  }
  return false;
}

export function logout(): void {
  localStorage.removeItem(AUTH_KEY);
}
