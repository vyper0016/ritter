import { apiFetch } from './client'
import type { User } from '../types'

export const getUsers = () => apiFetch<User[]>('/users')

export const getUser = (id: number) => apiFetch<User>(`/users/${id}`)

export const getDefaults = () => apiFetch<number[]>('/users/me/defaults')

export const setDefaults = (ids: number[]) =>
  apiFetch<number[]>('/users/me/defaults', { method: 'PUT', body: JSON.stringify(ids) })

export const uploadPicture = (file: File) => {
  const form = new FormData()
  form.append('image', file)
  return apiFetch<User>('/users/me/picture', { method: 'PUT', body: form })
}

export const deletePicture = () =>
  apiFetch<void>('/users/me/picture', { method: 'DELETE' })

export const pictureUrl = (id: number) => `/api/users/${id}/picture`
