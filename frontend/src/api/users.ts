import { apiFetch } from './client'
import type { User } from '../types'

export const getUsers = () => apiFetch<User[]>('/users')

export const updateUserName = (userId: number, name: string) =>
  apiFetch<User>(`/users/${userId}/name`, {
    method: 'PATCH',
    body: JSON.stringify({ name }),
  })

export const getUser = (id: number) => apiFetch<User>(`/users/${id}`)

export const uploadPicture = (file: File) => {
  const form = new FormData()
  form.append('image', file)
  return apiFetch<User>('/users/me/picture', { method: 'PUT', body: form })
}

export const deletePicture = () =>
  apiFetch<void>('/users/me/picture', { method: 'DELETE' })

export const pictureUrl = (id: number) => `/api/users/${id}/picture`

export const changePassword = (current_password: string, new_password: string) =>
  apiFetch<void>('/users/me/password', {
    method: 'PUT',
    body: JSON.stringify({ current_password, new_password }),
  })

export interface ApiKey {
  id: number
  name: string
  key_prefix: string
  created_at: string
  last_used_at: string | null
}

export interface CreatedApiKey extends ApiKey {
  key: string
}

export const listApiKeys = () => apiFetch<ApiKey[]>('/users/me/api-keys')

export const createApiKey = (name: string) =>
  apiFetch<CreatedApiKey>('/users/me/api-keys', {
    method: 'POST',
    body: JSON.stringify({ name }),
  })

export const deleteApiKey = (id: number) =>
  apiFetch<void>(`/users/me/api-keys/${id}`, { method: 'DELETE' })
