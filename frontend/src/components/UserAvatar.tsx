import { useState } from 'react'
import { pictureUrl } from '../api/users'
import type { User } from '../types'

export default function UserAvatar({ user, size = 8 }: { user: User; size?: number }) {
  const [err, setErr] = useState(false)
  const cls = `w-${size} h-${size} rounded-full object-cover`
  if (!err && user.profile_picture_filename) {
    return (
      <img
        src={pictureUrl(user.id)}
        alt={user.name}
        className={cls}
        onError={() => setErr(true)}
      />
    )
  }
  return (
    <div className={`${cls} bg-blue-100 flex items-center justify-center text-blue-700 font-medium text-sm`}>
      {user.name.charAt(0).toUpperCase()}
    </div>
  )
}
