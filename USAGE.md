# ERP/零售系统使用文档

## 1. 项目概述

本项目是一个基于微服务架构的ERP/零售混合系统，采用Nginx + FastAPI + Python技术栈，支持商品管理、采购、生产、库存、订单、会员、促销等完整的业务流程。

## 2. Linux 环境完整部署流程

### 2.1 第一阶段：环境准备

#### 2.1.1 安装 Python 3.11+
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y software-properties-common
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt install -y python3.11 python3.11-venv python3.11-dev python3-pip

# CentOS/RHEL
sudo yum install -y epel-release
sudo yum install -y python3.11 python3.11-devel python3-pip

# 验证安装
python3.11 --version
```

#### 2.1.2 安装 Docker
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y apt-transport-https ca-certificates curl gnupg lsb-release
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io

# CentOS/RHEL
sudo yum install -y yum-utils
sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
sudo yum install -y docker-ce docker-ce-cli containerd.io

# 启动 Docker 服务
sudo systemctl start docker
sudo systemctl enable docker

# 将当前用户加入 docker 组（免 sudo）
sudo usermod -aG docker $USER
newgrp docker

# 验证安装
docker --version
```

#### 2.1.3 安装 Docker Compose
```bash
# 下载最新版本
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose

# 添加执行权限
sudo chmod +x /usr/local/bin/docker-compose

# 验证安装
docker-compose --version
```

### 2.2 第二阶段：获取项目代码

```bash
# 克隆项目（如果是 Git 仓库）
git clone <your-repo-url> /opt/erp
cd /opt/erp

# 或者直接进入项目目录
cd /path/to/ERP
```

### 2.3 第三阶段：修改敏感配置（重要！）

#### 2.3.1 生成安全密钥
```bash
# 生成 JWT 密钥（32字符以上）
openssl rand -hex 32
# 输出示例：a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6

# 生成数据库密码
openssl rand -base64 16
# 输出示例：X7kL9mP2qR5tY8wZ
```

#### 2.3.2 修改 docker-compose.yml
```bash
# 编辑配置文件
vim docker-compose.yml

# 需要修改的位置：
# 1. MySQL 密码（搜索 MYSQL_ROOT_PASSWORD）
#    将 "password" 改为您生成的强密码
#
# 2. JWT 密钥（搜索 JWT_SECRET_KEY）
#    将 "your-secret-key-change-in-production" 改为您生成的密钥
#
# 3. 所有服务的 DATABASE_URL 中的密码部分
#    将 mysql+aiomysql://root:password@mysql:3306/erp
#    改为 mysql+aiomysql://root:您的密码@mysql:3306/erp
```

#### 2.3.3 使用 sed 批量替换（可选）
```bash
# 定义您的密码和密钥
DB_PASSWORD="您的数据库密码"
REDIS_PASSWORD="您的Redis密码"
JWT_KEY="您的JWT密钥"

# 批量替换数据库密码
sed -i "s/MYSQL_ROOT_PASSWORD: password/MYSQL_ROOT_PASSWORD: ${DB_PASSWORD}/g" docker-compose.yml
sed -i "s/root:password@mysql/root:${DB_PASSWORD}@mysql/g" docker-compose.yml

# 替换 Redis 密码
sed -i "s/redis123456/${REDIS_PASSWORD}/g" docker-compose.yml

# 替换 JWT 密钥
sed -i "s/JWT_SECRET_KEY=your-secret-key-change-in-production/JWT_SECRET_KEY=${JWT_KEY}/g" docker-compose.yml
```

#### 2.3.4 创建 .env 文件（可选）
```bash
cat > .env << EOF
# 数据库配置
DATABASE_URL=mysql+aiomysql://root:您的数据库密码@mysql:3306/erp
MYSQL_ROOT_PASSWORD=您的数据库密码

# Redis配置
REDIS_PASSWORD=您的Redis密码
REDIS_URL=redis://:您的Redis密码@redis:6379/0

# Kafka配置
KAFKA_BOOTSTRAP_SERVERS=kafka:9092

# JWT配置
JWT_SECRET_KEY=您的JWT密钥
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=30

# 调试模式（生产环境设为 false）
DEBUG=false
EOF

# 设置文件权限（保护敏感信息）
chmod 600 .env
```

### 2.4 第四阶段：数据库初始化

#### 2.4.1 检查初始化脚本
```bash
# 确认 init.sql 文件存在
ls -la scripts/init.sql

# 查看建表脚本内容
cat scripts/init.sql
```

#### 2.4.2 MySQL 自动初始化说明
MySQL 容器首次启动时，会自动执行 `scripts/init.sql` 中的建表语句。
这是通过 `docker-compose.yml` 中的卷挂载实现的：
```yaml
volumes:
  - ./scripts/init.sql:/docker-entrypoint-initdb.d/init.sql:ro
```

### 2.5 第五阶段：启动系统

#### 2.5.1 构建并启动所有服务
```bash
# 首次启动（构建镜像）
docker-compose up --build -d

# 后续启动（无需重新构建）
docker-compose up -d
```

#### 2.5.2 查看启动状态
```bash
# 查看所有容器状态
docker-compose ps

# 期望输出：所有服务状态为 Up
#   NAME                STATE
#   erp-mysql           Up (healthy)
#   erp-redis           Up (healthy)
#   erp-kafka           Up
#   erp-nginx           Up
#   erp-item-service    Up
#   erp-user-service    Up
#   ... 其他服务
```

#### 2.5.3 查看服务日志
```bash
# 查看所有服务日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f mysql
docker-compose logs -f user-service
docker-compose logs -f item-service

# 查看最近 100 行日志
docker-compose logs --tail 100 user-service
```

#### 2.5.4 等待服务就绪
```bash
# 等待 MySQL 就绪（约 30-60 秒）
until docker-compose exec mysql mysqladmin ping -h localhost -u root -p"您的密码" --silent; do
    echo "等待 MySQL 启动..."
    sleep 5
done
echo "MySQL 已就绪！"

# 检查健康状态
docker-compose ps | grep -E "(healthy|Up)"
```

### 2.6 第六阶段：验证部署

#### 2.6.1 检查 API 服务
```bash
# 检查 Nginx 网关
curl -I http://localhost/

# 检查各服务健康状态
curl http://localhost/item/health
curl http://localhost/user/health
curl http://localhost/stock/health
curl http://localhost/order/health
```

#### 2.6.2 访问 API 文档
```bash
# 在浏览器中访问以下地址查看 Swagger 文档：
# 商品中心: http://服务器IP/item/docs
# 用户中心: http://服务器IP/user/docs
# 库存中心: http://服务器IP/stock/docs
# 订单中心: http://服务器IP/order/docs
```

#### 2.6.3 验证数据库连接
```bash
# 进入 MySQL 容器
docker-compose exec mysql mysql -u root -p"您的密码" erp

# 查看已创建的表
SHOW TABLES;

# 退出
exit
```

#### 2.6.4 测试 API 调用
```bash
# 测试用户登录
curl -X POST http://localhost/user/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'

# 测试创建商品（需要先获取 token）
curl -X POST http://localhost/item/create \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your_token>" \
  -d '{"name": "测试商品", "category_id": 1, "price": 99.00}'
```

### 2.7 常用运维命令

```bash
# 停止所有服务
docker-compose down

# 停止并删除数据卷（警告：会删除所有数据）
docker-compose down -v

# 重启单个服务
docker-compose restart user-service

# 查看资源使用情况
docker stats

# 进入容器调试
docker-compose exec user-service /bin/sh

# 清理未使用的镜像
docker system prune -f
```

### 2.8 防火墙配置（如需外网访问）

```bash
# Ubuntu/Debian (ufw)
sudo ufw allow 80/tcp    # Nginx
sudo ufw allow 3306/tcp  # MySQL（建议仅内网开放）
sudo ufw allow 6379/tcp  # Redis（建议仅内网开放）
sudo ufw reload

# CentOS/RHEL (firewalld)
sudo firewall-cmd --permanent --add-port=80/tcp
sudo firewall-cmd --reload
```

### 2.9 设置开机自启

```bash
# 创建 systemd 服务文件
sudo cat > /etc/systemd/system/erp.service << EOF
[Unit]
Description=ERP System
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/erp
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down

[Install]
WantedBy=multi-user.target
EOF

# 启用服务
sudo systemctl daemon-reload
sudo systemctl enable erp.service

# 手动启动/停止
sudo systemctl start erp
sudo systemctl stop erp
sudo systemctl status erp
```

### 2.10 故障排查

```bash
# 1. 服务启动失败
docker-compose logs <service-name> | tail -50

# 2. 数据库连接失败
docker-compose exec mysql mysqladmin ping -h localhost -u root -p"密码"

# 3. 端口被占用
sudo netstat -tlnp | grep :80
sudo lsof -i :80

# 4. 磁盘空间不足
df -h
docker system df

# 5. 重新构建单个服务
docker-compose build --no-cache user-service
docker-compose up -d user-service
```

## 3. 配置项说明（重要：这些需要手动设置）

### 3.1 必须修改的安全配置
以下配置项在部署前**必须修改**，否则存在安全风险：

1. **JWT密钥** - 用于用户认证令牌
   - 默认值：`your-secret-key-change-in-production`
   - 位置：`docker-compose.yml` 中 `JWT_SECRET_KEY` 环境变量
   - 位置：`erp_common/config.py` 中 `jwt_secret_key` 配置
   - 修改方法：使用强随机密钥（至少32字符）

2. **数据库密码** - MySQL root 密码
   - 默认值：`password`
   - 位置：`docker-compose.yml` 中 `MYSQL_ROOT_PASSWORD` 环境变量
   - 修改方法：使用强密码

3. **Redis密码** - Redis 访问密码
   - 默认值：`redis123456`
   - 位置：`docker-compose.yml` 中 `REDIS_PASSWORD` 环境变量
   - 修改方法：通过 `.env` 文件或直接修改 docker-compose.yml

### 3.2 环境变量配置
创建 `.env` 文件并配置以下变量：

```env
# 数据库配置
DATABASE_URL=mysql+aiomysql://root:your_secure_password@mysql:3306/erp

# Redis配置
REDIS_PASSWORD=your_secure_redis_password
REDIS_URL=redis://:your_secure_redis_password@redis:6379/0

# Kafka配置
KAFKA_BOOTSTRAP_SERVERS=kafka:9092

# JWT配置（务必修改）
JWT_SECRET_KEY=your_very_strong_secret_key_that_is_at_least_32_characters_long
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=30

# 服务端口（可根据需要调整）
ITEM_SERVICE_PORT=8001
USER_SERVICE_PORT=8001
STOCK_SERVICE_PORT=8002
PURCHASE_SERVICE_PORT=8003
PRODUCTION_SERVICE_PORT=8004
JOB_SERVICE_PORT=8005
COST_SERVICE_PORT=8006
ORDER_SERVICE_PORT=8007
MEMBER_SERVICE_PORT=8008
PROMO_SERVICE_PORT=8009
```

### 3.3 Docker Compose 中的关键配置
在 `docker-compose.yml` 文件中，需要关注以下配置：

1. **数据库密码**:
   ```yaml
   mysql:
     environment:
       MYSQL_ROOT_PASSWORD: your_secure_password  # 必须修改
       MYSQL_DATABASE: erp
   ```

2. **JWT密钥** (仅在用户服务中):
   ```yaml
   user-service:
     environment:
       - JWT_SECRET_KEY=your_very_strong_secret_key  # 必须修改
   ```

3. **服务端口映射**:
   ```yaml
   nginx:
     ports:
       - "80:80"  # 可根据需要修改为其他端口如 "8080:80"
   ```

## 4. 业务流程示例

### 4.1 创建商品
```bash
curl -X POST http://localhost:8000/item/create \
  -H "Content-Type: application/json" \
  -d '{
    "name": "示例商品",
    "category_id": 1,
    "price": 100.00,
    "sku_specs": {
      "color": ["红色", "蓝色"],
      "size": ["S", "M", "L"]
    }
  }'
```

### 4.2 用户登录
```bash
curl -X POST http://localhost:8000/user/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "password"
  }'
```

### 4.3 创建订单
```bash
curl -X POST http://localhost:8000/order/create \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{
    "customer_id": 1,
    "details": [
      {
        "sku_id": "SKU001",
        "qty_ordered": 2,
        "unit_price": 100.00
      }
    ]
  }'
```

## 5. 数据备份方案

### 5.1 数据库备份
```bash
# 备份数据库
docker exec erp-db mysqldump -u root -p'your_password' erp > backup_$(date +%Y%m%d_%H%M%S).sql

# 恢复数据库
docker exec -i erp-db mysql -u root -p'your_password' erp < backup_file.sql
```

### 5.2 Redis数据持久化
Redis配置为RDB+AOF双重持久化：
- RDB快照：每15分钟保存一次
- AOF日志：每秒同步一次

### 5.3 Kafka数据保留
Kafka主题配置数据保留策略：
```yaml
# kafka配置
log.retention.hours: 168  # 保留7天
log.retention.bytes: 1073741824  # 1GB
```

### 5.4 自动备份脚本
```bash
#!/bin/bash
# backup.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACK_UP_DIR="/backup/erp"

mkdir -p $BACK_UP_DIR

# 数据库备份
docker exec erp-db mysqldump -u root -p'your_password' erp > $BACK_UP_DIR/db_$DATE.sql

# Redis备份
docker exec erp-redis redis-cli BGSAVE
sleep 5
docker cp erp-redis:/data/dump.rdb $BACK_UP_DIR/redis_$DATE.rdb

# 压缩备份文件
tar -czf $BACK_UP_DIR/backup_$DATE.tar.gz -C $BACK_UP_DIR .

# 删除7天前的备份
find $BACK_UP_DIR -name "*.tar.gz" -mtime +7 -delete
```

## 6. 集群化部署可能性

### 6.1 服务横向扩展
所有微服务都支持水平扩展，可通过docker-compose scale命令扩展实例数量：

```yaml
# docker-compose.scale.yml
version: '3.8'

services:
  item_service:
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
      restart_policy:
        condition: on-failure

  user_service:
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
      restart_policy:
        condition: on-failure

  # ... 其他服务
```

### 6.2 数据库集群
- **MySQL主从复制**: 实现读写分离
- **Redis Cluster**: 实现高可用和分片存储
- **Kafka集群**: 多副本保证数据可靠性

### 6.3 负载均衡
- **Nginx负载均衡**: Upstream配置多实例
- **服务发现**: 可集成Consul或etcd
- **API网关**: 可使用Kong或Traefik

### 6.4 监控方案
```yaml
# 监控服务配置
prometheus:
  image: prom/prometheus
  ports:
    - "9090:9090"
  volumes:
    - ./prometheus.yml:/etc/prometheus/prometheus.yml

grafana:
  image: grafana/grafana
  ports:
    - "3000:3000"
  environment:
    - GF_SECURITY_ADMIN_PASSWORD=admin

jaeger:
  image: jaegertracing/all-in-one:latest
  ports:
    - "16686:16686"
    - "14268:14268"
```

### 6.5 高可用部署
```yaml
# docker-compose.ha.yml
version: '3.8'

services:
  # MySQL主从配置
  mysql-master:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: your_password
      MYSQL_DATABASE: erp
    command: --server-id=1 --log-bin=mysql-bin --sync-binlog=1 --gtid-mode=ON --enforce-gtid-consistency=true
  
  mysql-slave:
    image: mysql:8.0
    environment:
      MYSQL_ROOT_PASSWORD: your_password
    command: --server-id=2 --relay-log=relay-bin --read-only=1
    depends_on:
      - mysql-master

  # Redis哨兵模式
  redis-master:
    image: redis:alpine
    command: redis-server --appendonly yes --cluster-enabled yes --cluster-config-file nodes.conf --cluster-node-timeout 5000 --appendfilename appendonly.aof --appendfsync always
  
  redis-sentinel:
    image: redis:alpine
    command: redis-sentinel /etc/redis/sentinel.conf
    volumes:
      - ./sentinel.conf:/etc/redis/sentinel.conf
```

## 7. 性能优化建议

### 7.1 缓存策略
- Redis缓存热点数据
- 应用层缓存计算结果
- CDN加速静态资源

### 7.2 数据库优化
- 合理设计索引
- 分库分表策略
- 读写分离

### 7.3 消息队列优化
- 合理设置分区数量
- 批量消费提高效率
- 死信队列处理异常

## 8. 故障排查

### 8.1 日志查看
```bash
# 查看特定服务日志
docker-compose logs -f --tail 100 <service-name>

# 查看错误日志
docker-compose logs --tail 100 | grep ERROR
```

### 8.2 健康检查
```bash
# 检查服务健康状态
curl http://localhost:8000/health

# 检查特定服务健康状态
curl http://localhost:8000/item/health
curl http://localhost:8000/user/health
```

## 9. 安全建议

### 9.1 认证授权
- JWT Token认证
- RBAC权限控制
- API限流保护

### 9.2 数据安全
- 敏感数据加密存储
- HTTPS传输加密
- 定期安全审计

### 9.3 必须修改的默认配置
- [ ] 更改JWT密钥 (当前默认: `your-secret-key-change-in-production`)
- [ ] 更改数据库密码 (当前默认: `password`)
- [ ] 更改Redis密码 (当前默认: `redis123456`)
- [ ] 配置HTTPS证书

---

此文档提供了系统的完整使用指南，包括部署、配置、运维和扩展等方面的详细说明。特别注意安全配置部分，必须在生产环境中修改默认凭据。如需进一步定制化部署方案，请联系开发团队。