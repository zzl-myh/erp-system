import { post, get } from './request'

// 类型定义
export interface LoginForm {
  username: string
  password: string
}

export interface LoginResult {
  access_token: string
  token_type: string
}

export interface UserInfo {
  id: number
  username: string
  name: string
  mobile?: string
  email?: string
  status: number
}

// 登录
export function login(data: LoginForm) {
  return post<LoginResult>('/user/login', data)
}

// 获取用户信息
export function getUserInfo() {
  return get<UserInfo>('/user/me')
}

// 用户列表
export function getUserList(params?: { page?: number; size?: number }) {
  return get<{ items: UserInfo[]; total: number }>('/user/', { params })
}
