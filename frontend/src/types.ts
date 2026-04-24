export type OcrStatus = 'pending' | 'processing' | 'done' | 'failed'
export type SplitType = 'equal' | 'percentage' | 'fraction'

export interface User {
  id: number
  username: string
  name: string
  is_admin: boolean
  profile_picture_filename: string | null
  profile_picture_mimetype: string | null
  created_at: string
}

export interface Receipt {
  id: number
  created_by_id: number
  payer_id: number
  participant_ids: number[]
  ocr_status: OcrStatus
  date: string | null
  total: number | null
  vendor_name: string | null
  vendor_logo_url: string | null
  settled: boolean
  settled_at: string | null
  image_filename: string | null
  created_at: string
}

export interface LineItem {
  id: number
  description: string | null
  quantity: number | null
  price: number | null
  total: number
  item_order: number | null
  type: string | null
}

export interface Allocation {
  id: number
  line_item_id: number
  user_id: number
  split_type: SplitType
  split_value: number | null
  amount: number
}
