import { get } from './request'
import type { ApiResult } from './request'

export interface SalesTrend {
  date: string
  amount: number
  order_count: number
}

export interface DashboardStats {
  item_count: number
  today_order_count: number
  member_count: number
  today_sales: number
  week_sales_trend: SalesTrend[]
}

export function getDashboardStats(): Promise<ApiResult<DashboardStats>> {
  return get<DashboardStats>('/order/dashboard/stats')
}
