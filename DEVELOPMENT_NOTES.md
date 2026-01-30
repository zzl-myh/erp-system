# ERP 系统开发注意事项

> 本文档记录项目开发过程中遇到的问题、解决方案和最佳实践，供后续开发参考。

---

## 1. 后端开发 (FastAPI/Python)

### 1.1 路由顺序问题 ⚠️ 重要

**问题**：FastAPI 路由按定义顺序匹配。当存在 `/{user_id}` 这样的路径参数路由时，如果定义在 `/role/list` 之前，请求 `/role/list` 会被错误匹配到 `/{user_id}`，导致 400 错误。

**解决方案**：
- 所有带路径参数的路由（如 `/{id}`、`/{user_id}`）必须放在**文件末尾**
- 固定路径路由（如 `/list`、`/create`、`/role/list`）放在前面

```python
# ✅ 正确顺序
@router.get("/list")          # 固定路径在前
@router.get("/role/list")     # 固定路径在前
@router.post("/create")       # 固定路径在前
@router.get("/{user_id}")     # 路径参数在最后
@router.put("/{user_id}")     # 路径参数在最后
@router.delete("/{user_id}")  # 路径参数在最后
```

### 1.2 Pydantic Schema 配置

使用 `from_attributes = True` 支持从 ORM 模型自动转换：

```python
class UserResponse(BaseModel):
    id: int
    username: str
    
    class Config:
        from_attributes = True  # Pydantic v2
```

### 1.3 异步数据库操作

使用 SQLAlchemy 2.0 异步语法：

```python
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

async def get_user(self, user_id: int) -> User:
    result = await self.db.execute(
        select(User).where(User.id == user_id)
    )
    return result.scalar_one_or_none()
```

---

## 2. 前端开发 (Vue 3 + TypeScript)

### 2.1 新增路由/Store 类型声明

**问题**：新增路由或 Store 时，IDE 可能报"找不到模块"错误。

**说明**：这是 IDE 类型声明问题，不影响实际运行。确保 `node_modules` 已安装即可。

### 2.2 API 调用封装

统一使用封装的请求方法：

```typescript
import { get, post, put, del } from '@/api/request'

export function getUserList(params?: UserQuery): Promise<ApiResult<PageResult<UserInfo>>> {
  return get<PageResult<UserInfo>>('/user/list', { params })
}
```

### 2.3 请求参数空值过滤 ⚠️ 重要

**问题**：axios 会将 `undefined`、空字符串 `''` 等值也发送到后端，导致 400 错误。

**解决方案**：在请求拦截器中过滤空值参数：

```typescript
// request.ts 请求拦截器
if (config.params) {
  const cleanParams: Record<string, any> = {}
  for (const [key, value] of Object.entries(config.params)) {
    if (value !== undefined && value !== null && value !== '') {
      cleanParams[key] = value
    }
  }
  config.params = cleanParams
}
```

### 2.4 错误处理统一

前端统一兜底错误提示：

```typescript
try {
  const res = await apiCall()
  if (res.success) {
    // 成功处理
  } else {
    ElMessage.error(res.message || '操作失败')
  }
} catch (error) {
  ElMessage.error('服务器错误，请稍后重试')
}
```

---

## 3. Nginx 配置

### 3.1 字符编码 ⚠️ 重要

**问题**：中文响应显示乱码。

**解决方案**：在 server 块添加字符集配置：

```nginx
server {
    listen 80;
    charset utf-8;  # 必须添加
    ...
}
```

### 3.2 DNS 缓存问题

**问题**：微服务容器重启后，IP 地址变化，但 Nginx 缓存了旧的 DNS 解析结果，导致 502 错误。

**解决方案**：微服务重启后，同时重启 Nginx：

```bash
docker-compose restart user-service nginx
```

### 3.3 认证路由白名单

以下路由无需认证，在 Nginx 中单独配置：
- `/user/login` - 登录
- `/user/register` - 注册
- `/*/docs` - API 文档
- `/*/health` - 健康检查

---

## 4. Docker 容器编排

### 4.1 服务启动顺序 ⚠️ 重要

**问题**：微服务启动时 Kafka 未就绪，导致连接失败。

**解决方案**：使用 healthcheck + service_healthy：

```yaml
kafka:
  healthcheck:
    test: ["CMD-SHELL", "kafka-broker-api-versions --bootstrap-server localhost:9092 || exit 1"]
    interval: 10s
    timeout: 10s
    retries: 5
    start_period: 30s

order-service:
  depends_on:
    kafka:
      condition: service_healthy  # 等待健康检查通过
```

### 4.2 数据持久化

`docker-compose down` 不会删除 volume 数据，MySQL 数据安全。
如需完全清除：`docker-compose down -v`（谨慎使用）

---

## 5. 数据库设计

### 5.1 必要字段

确保表包含以下字段：
- `created_at` - 创建时间
- `updated_at` - 更新时间（可选）
- `status` - 状态字段（0=禁用, 1=启用）
- `deleted` - 软删除标记（如需要）

### 5.2 字符集

建表时指定 UTF-8：

```sql
CREATE TABLE xxx (
    ...
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

---

## 6. 常见问题排查

### 6.1 "服务器错误，请稍后重试"

排查步骤：
1. 检查 Nginx 日志：`docker logs erp-nginx-1`
2. 检查对应服务日志：`docker logs erp-xxx-service-1`
3. 如果是 502 错误，尝试重启 Nginx

### 6.2 400 Bad Request

可能原因：
1. 路由顺序问题（参见 1.1）
2. 请求参数类型不匹配
3. Pydantic 校验失败

### 6.3 401 Unauthorized

可能原因：
1. Token 过期或无效
2. 请求未携带 Authorization 头
3. 访问了需要认证的接口

---

## 7. 部署流程

### 7.1 标准部署步骤

```bash
# 1. 本地推送
push.bat

# 2. 服务器拉取并重启
cd /path/to/erp
git pull
docker-compose restart <service-name>
# 或全部重启
docker-compose down && docker-compose up -d
```

### 7.2 重启特定服务

```bash
# 单个服务
docker-compose restart user-service

# 多个服务
docker-compose restart user-service nginx

# 查看日志
docker-compose logs -f user-service
```

---

## 8. 待优化项

- [ ] 添加操作日志记录功能
- [ ] 完善权限控制粒度
- [ ] 添加接口缓存机制
- [ ] 前端添加请求重试机制

---

## 更新记录

| 日期 | 内容 | 作者 |
|------|------|------|
| 2026-01-19 | 初始版本，记录路由顺序、Nginx 编码、容器启动顺序等问题 | - |
