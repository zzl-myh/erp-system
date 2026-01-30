import { post, get, put, del } from './request'
import type { ApiResult, PageResult } from './request'

// ==================== 类型定义 ====================

export interface LoginForm {
  username: string
  password: string
}

export interface LoginResult {
  access_token: string
  token_type: string
}

export interface Role {
  id: number
  code: string
  name: string
  description?: string
}

export interface UserInfo {
  id: number
  username: string
  name?: string
  mobile?: string
  email?: string
  status: number
  org_id?: number
  roles: Role[]
  created_at?: string
  updated_at?: string
}

export interface UserCreate {
  username: string
  password: string
  name?: string
  mobile?: string
  email?: string
  org_id?: number
  roles?: string[]  // 角色编码列表
}

export interface UserUpdate {
  name?: string
  mobile?: string
  email?: string
  org_id?: number
  status?: number
}

export interface UserQuery {
  keyword?: string
  org_id?: number
  status?: number
  page?: number
  size?: number
}

export interface RoleAssign {
  user_id: number
  roles: string[]  // 后端字段名是 roles
}

export interface PasswordReset {
  user_id: number
  new_password: string
}

export interface PasswordChange {
  old_password: string
  new_password: string
}

// ==================== 认证接口 ====================

// 登录
export function login(data: LoginForm): Promise<ApiResult<LoginResult>> {
  return post<LoginResult>('/user/login', data)
}

// 注销
export function logout(): Promise<ApiResult<null>> {
  return post<null>('/user/logout')
}

// ==================== 用户接口 ====================

// 获取当前用户信息
export function getCurrentUser(): Promise<ApiResult<UserInfo>> {
  return get<UserInfo>('/user/me')
}

// 用户列表
export function getUserList(params?: UserQuery): Promise<ApiResult<PageResult<UserInfo>>> {
  return get<PageResult<UserInfo>>('/user/list', { params })
}

// 获取用户详情
export function getUser(userId: number): Promise<ApiResult<UserInfo>> {
  return get<UserInfo>(`/user/${userId}`)
}

// 创建用户
export function createUser(data: UserCreate): Promise<ApiResult<UserInfo>> {
  return post<UserInfo>('/user/create', data)
}

// 更新用户
export function updateUser(userId: number, data: UserUpdate): Promise<ApiResult<UserInfo>> {
  return put<UserInfo>(`/user/${userId}`, data)
}

// 分配角色
export function assignRoles(data: RoleAssign): Promise<ApiResult<UserInfo>> {
  return post<UserInfo>('/user/role/assign', data)
}

// 修改密码
export function changePassword(data: PasswordChange): Promise<ApiResult<null>> {
  return post<null>('/user/password/change', data)
}

// 重置密码（管理员）
export function resetPassword(data: PasswordReset): Promise<ApiResult<null>> {
  return post<null>('/user/password/reset', data)
}

// 删除用户
export function deleteUser(userId: number): Promise<ApiResult<null>> {
  return del<null>(`/user/${userId}`)
}

// ==================== 角色接口 ====================

// 角色列表
export function getRoleList(): Promise<ApiResult<Role[]>> {
  return get<Role[]>('/user/role/list')
}

// 创建角色
export interface RoleCreate {
  code: string
  name: string
  description?: string
}

export function createRole(data: RoleCreate): Promise<ApiResult<Role>> {
  return post<Role>('/user/role/create', data)
}

// 更新角色
export interface RoleUpdate {
  name?: string
  description?: string
}

export function updateRole(roleId: number, data: RoleUpdate): Promise<ApiResult<Role>> {
  return put<Role>(`/user/role/${roleId}`, data)
}

// 删除角色
export function deleteRole(roleId: number): Promise<ApiResult<null>> {
  return del<null>(`/user/role/${roleId}`)
}

// ==================== 权限接口 ====================

export interface Permission {
  id: number
  code: string
  name: string
  resource: string
  action: string
}

export interface RolePermissionAssign {
  role_id: number
  permission_codes: string[]
}

// 获取所有权限点
export function getPermissionList(): Promise<ApiResult<Permission[]>> {
  return get<Permission[]>('/user/permission/list')
}

// 获取当前用户权限
export function getMyPermissions(): Promise<ApiResult<string[]>> {
  return get<string[]>('/user/permission/me')
}

// 获取角色权限
export function getRolePermissions(roleId: number): Promise<ApiResult<string[]>> {
  return get<string[]>(`/user/permission/role/${roleId}`)
}

// 为角色分配权限
export function assignRolePermissions(data: RolePermissionAssign): Promise<ApiResult<null>> {
  return post<null>('/user/permission/assign', data)
}

// ==================== 组织接口 ====================

export interface Org {
  id: number
  code: string
  name: string
  type: string
  parent_id: number
  status: number
  created_at?: string
}

export interface OrgCreate {
  code: string
  name: string
  type: string
  parent_id?: number
}

export interface OrgUpdate {
  name?: string
  type?: string
  parent_id?: number
  status?: number
}

// 组织列表
export function getOrgList(params?: { type?: string; parent_id?: number; status?: number }): Promise<ApiResult<Org[]>> {
  return get<Org[]>('/user/org/list', { params })
}

// 组织详情
export function getOrg(orgId: number): Promise<ApiResult<Org>> {
  return get<Org>(`/user/org/${orgId}`)
}

// 创建组织
export function createOrg(data: OrgCreate): Promise<ApiResult<Org>> {
  return post<Org>('/user/org/create', data)
}

// 更新组织
export function updateOrg(orgId: number, data: OrgUpdate): Promise<ApiResult<Org>> {
  return put<Org>(`/user/org/${orgId}`, data)
}

// 删除组织
export function deleteOrg(orgId: number): Promise<ApiResult<null>> {
  return del<null>(`/user/org/${orgId}`)
}

// 兼容旧接口
export const getUserInfo = getCurrentUser
