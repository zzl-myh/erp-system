import axios, { type AxiosRequestConfig, type AxiosResponse } from 'axios'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'
import router from '@/router'

// API 响应结构
export interface ApiResult<T = any> {
  success: boolean
  code: string
  message: string
  data: T | null
  timestamp: string
}

// 创建 axios 实例
const request = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器
request.interceptors.request.use(
  (config) => {
    const userStore = useUserStore()
    if (userStore.token) {
      config.headers.Authorization = `Bearer ${userStore.token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
request.interceptors.response.use(
  (response: AxiosResponse<ApiResult>) => {
    const res = response.data
    
    if (!res.success) {
      ElMessage.error(res.message || '请求失败')
      
      // 认证失败，跳转登录
      if (res.code === 'AUTHENTICATION_ERROR' || res.code === 'TOKEN_EXPIRED') {
        const userStore = useUserStore()
        userStore.logout()
        router.push('/login')
      }
      
      return Promise.reject(new Error(res.message))
    }
    
    return response
  },
  (error) => {
    const status = error.response?.status
    
    if (status === 401) {
      const userStore = useUserStore()
      userStore.logout()
      router.push('/login')
      ElMessage.error('登录已过期，请重新登录')
    } else if (status === 403) {
      ElMessage.error('没有权限访问')
    } else if (status === 404) {
      ElMessage.error('请求的资源不存在')
    } else if (status >= 500) {
      ElMessage.error('服务器错误，请稍后重试')
    } else {
      ElMessage.error(error.message || '网络错误')
    }
    
    return Promise.reject(error)
  }
)

// 封装请求方法
export async function get<T>(url: string, config?: AxiosRequestConfig): Promise<ApiResult<T>> {
  const response = await request.get<ApiResult<T>>(url, config)
  return response.data
}

export async function post<T>(url: string, data?: any, config?: AxiosRequestConfig): Promise<ApiResult<T>> {
  const response = await request.post<ApiResult<T>>(url, data, config)
  return response.data
}

export async function put<T>(url: string, data?: any, config?: AxiosRequestConfig): Promise<ApiResult<T>> {
  const response = await request.put<ApiResult<T>>(url, data, config)
  return response.data
}

export async function del<T>(url: string, config?: AxiosRequestConfig): Promise<ApiResult<T>> {
  const response = await request.delete<ApiResult<T>>(url, config)
  return response.data
}

export default request
