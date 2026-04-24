import { apiFetch } from './client'

export async function login(username: string, password: string): Promise<string> {
  const body = new URLSearchParams({ username, password })
  const data = await apiFetch<{ access_token: string }>('/auth/login', {
    method: 'POST',
    body,
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  })
  return data.access_token
}
