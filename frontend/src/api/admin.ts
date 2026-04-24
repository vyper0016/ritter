import { apiFetch } from './client'
import type { User } from '../types'

export const createUser = (data: {
  username: string
  password: string
  name: string
  is_admin: boolean
}) => apiFetch<User>('/users', { method: 'POST', body: JSON.stringify(data) })

export const setUserAdmin = (userId: number, is_admin: boolean) =>
  apiFetch<User>(`/users/${userId}/admin`, {
    method: 'PATCH',
    body: JSON.stringify({ is_admin }),
  })

export const deleteUser = (userId: number) =>
  apiFetch<void>(`/users/${userId}`, { method: 'DELETE' })
