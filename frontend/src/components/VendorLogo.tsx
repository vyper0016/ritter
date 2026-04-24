import { useEffect, useMemo, useState } from 'react'

const KNOWN_VENDOR_DOMAINS: Record<string, string> = {
  aldi: 'aldi.com',
  lidl: 'lidl.com',
  rewe: 'rewe.de',
  edeka: 'edeka.de',
  kaufland: 'kaufland.de',
  penny: 'penny.de',
  dm: 'dm.de',
  rossmann: 'rossmann.de',
  ikea: 'ikea.com',
  amazon: 'amazon.com',
}

function getInitials(name: string | null): string {
  if (!name) return '?'
  const parts = name
    .split(/\s+/)
    .map((p) => p.trim())
    .filter(Boolean)
  if (parts.length === 0) return '?'
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase()
  return (parts[0][0] + parts[1][0]).toUpperCase()
}

function getCandidateDomains(vendorName: string | null): string[] {
  if (!vendorName) return []
  const key = vendorName.trim().toLowerCase()
  const known = Object.entries(KNOWN_VENDOR_DOMAINS).find(([k]) => key.includes(k))
  if (known) return [known[1]]

  const slug = key
    .replace(/[^a-z0-9\s-]/g, '')
    .trim()
    .replace(/\s+/g, '')

  if (!slug) return []
  return [`${slug}.com`, `${slug}.de`]
}

export default function VendorLogo({
  vendorName,
  vendorLogoUrl,
}: {
  vendorName: string | null
  vendorLogoUrl?: string | null
}) {
  const initials = getInitials(vendorName)
  const urls = useMemo(
    () => {
      const fallbackUrls = getCandidateDomains(vendorName).map((d) => `https://logo.clearbit.com/${d}`)
      if (vendorLogoUrl) return [vendorLogoUrl, ...fallbackUrls]
      return fallbackUrls
    },
    [vendorName, vendorLogoUrl],
  )
  const [idx, setIdx] = useState(0)

  useEffect(() => {
    setIdx(0)
  }, [vendorName, vendorLogoUrl])

  const hasLogo = idx < urls.length
  return hasLogo ? (
    <img
      src={urls[idx]}
      alt={vendorName ?? 'Vendor'}
      className="w-8 h-8 rounded-md border border-gray-200 object-cover bg-white"
      onError={() => setIdx((i) => i + 1)}
      loading="lazy"
    />
  ) : (
    <div className="w-8 h-8 rounded-md bg-blue-100 text-blue-700 border border-blue-200 flex items-center justify-center text-xs font-semibold">
      {initials}
    </div>
  )
}
