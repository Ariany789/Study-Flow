const API = import.meta.env.VITE_API_URL || '/api/v1';

export async function request(path: string, token: string, options: RequestInit = {}) {
  return fetch(`${API}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
      ...(options.headers || {}),
    },
  });
}

export async function publicRequest(path: string, options: RequestInit = {}) {
  return fetch(`${API}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
  });
}
