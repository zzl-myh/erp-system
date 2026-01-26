#!/bin/bash
#
# ERP 系统健康检测脚本
# 用于检测所有服务的运行状态
#

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 计数器
TOTAL=0
PASSED=0
FAILED=0

# 打印分隔线
print_line() {
    echo "=============================================="
}

# 检测结果输出
check_result() {
    local name=$1
    local status=$2
    TOTAL=$((TOTAL + 1))
    if [ "$status" -eq 0 ]; then
        echo -e "  ${GREEN}✓${NC} $name"
        PASSED=$((PASSED + 1))
    else
        echo -e "  ${RED}✗${NC} $name"
        FAILED=$((FAILED + 1))
    fi
}

# 检测 Docker 容器状态
check_container() {
    local container=$1
    local status=$(docker inspect -f '{{.State.Status}}' "$container" 2>/dev/null)
    if [ "$status" == "running" ]; then
        return 0
    else
        return 1
    fi
}

# 检测服务健康（是否在重启循环中）
check_not_restarting() {
    local container=$1
    local status=$(docker inspect -f '{{.State.Status}}' "$container" 2>/dev/null)
    local restarting=$(docker inspect -f '{{.State.Restarting}}' "$container" 2>/dev/null)
    if [ "$status" == "running" ] && [ "$restarting" != "true" ]; then
        return 0
    else
        return 1
    fi
}

# 检测 HTTP 服务
check_http() {
    local url=$1
    local response=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$url" 2>/dev/null)
    if [ "$response" == "200" ] || [ "$response" == "404" ]; then
        return 0
    else
        return 1
    fi
}

# 检测端口
check_port() {
    local host=$1
    local port=$2
    nc -z -w 3 "$host" "$port" 2>/dev/null
    return $?
}

echo ""
print_line
echo "       ERP 系统健康检测"
echo "       $(date '+%Y-%m-%d %H:%M:%S')"
print_line

# ========== 1. 基础设施服务 ==========
echo ""
echo -e "${YELLOW}[1] 基础设施服务${NC}"

check_container "erp-mysql-1"
check_result "MySQL 容器" $?

check_container "erp-redis-1"
check_result "Redis 容器" $?

check_container "erp-kafka-1"
check_result "Kafka 容器" $?

check_container "erp-zookeeper-1"
check_result "Zookeeper 容器" $?

check_container "erp-nginx-1"
check_result "Nginx 容器" $?

# ========== 2. 微服务状态 ==========
echo ""
echo -e "${YELLOW}[2] 微服务容器状态${NC}"

SERVICES=(
    "erp-user-service-1:用户服务"
    "erp-item-service-1:商品服务"
    "erp-stock-service-1:库存服务"
    "erp-order-service-1:订单服务"
    "erp-member-service-1:会员服务"
    "erp-purchase-service-1:采购服务"
    "erp-production-service-1:生产服务"
    "erp-job-service-1:报工服务"
    "erp-cost-service-1:成本服务"
    "erp-promo-service-1:促销服务"
)

for item in "${SERVICES[@]}"; do
    container="${item%%:*}"
    name="${item##*:}"
    check_not_restarting "$container"
    check_result "$name ($container)" $?
done

# ========== 3. 端口连通性 ==========
echo ""
echo -e "${YELLOW}[3] 端口连通性${NC}"

check_port "localhost" 80
check_result "Nginx (80)" $?

check_port "localhost" 3306
check_result "MySQL (3306)" $?

check_port "localhost" 6379
check_result "Redis (6379)" $?

check_port "localhost" 9092
check_result "Kafka (9092)" $?

# ========== 4. API 健康检测 ==========
echo ""
echo -e "${YELLOW}[4] API 健康检测${NC}"

# 通过 Nginx 反向代理检测各服务
API_ENDPOINTS=(
    "http://localhost/api/user/health:用户服务 API"
    "http://localhost/api/item/health:商品服务 API"
    "http://localhost/api/stock/health:库存服务 API"
    "http://localhost/api/order/health:订单服务 API"
    "http://localhost/api/member/health:会员服务 API"
)

for item in "${API_ENDPOINTS[@]}"; do
    url="${item%%:*}"
    name="${item##*:}"
    check_http "$url"
    check_result "$name" $?
done

# ========== 5. 数据库连接测试 ==========
echo ""
echo -e "${YELLOW}[5] 数据库连接测试${NC}"

# MySQL 连接测试
MYSQL_PWD="${MYSQL_ROOT_PASSWORD:-a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4lyzm}"
mysql_result=$(docker exec erp-mysql-1 mysql -uroot -p"$MYSQL_PWD" -e "SELECT 1" 2>/dev/null)
if [ $? -eq 0 ]; then
    check_result "MySQL 连接" 0
else
    check_result "MySQL 连接" 1
fi

# Redis 连接测试
REDIS_PWD="${REDIS_PASSWORD:-X7kL9mP2qR5tlyzm}"
redis_result=$(docker exec erp-redis-1 redis-cli -a "$REDIS_PWD" ping 2>/dev/null | grep -c PONG)
if [ "$redis_result" -eq 1 ]; then
    check_result "Redis 连接" 0
else
    check_result "Redis 连接" 1
fi

# ========== 汇总 ==========
echo ""
print_line
echo -e "  检测完成: 共 ${TOTAL} 项"
echo -e "  ${GREEN}通过: ${PASSED}${NC}  ${RED}失败: ${FAILED}${NC}"

if [ "$FAILED" -gt 0 ]; then
    echo ""
    echo -e "  ${RED}[!] 系统存在异常，请检查失败的服务${NC}"
    echo ""
    echo "  故障排查命令:"
    echo "    docker-compose ps                    # 查看容器状态"
    echo "    docker-compose logs <服务名>         # 查看服务日志"
    echo "    docker-compose restart <服务名>      # 重启服务"
    print_line
    exit 1
else
    echo ""
    echo -e "  ${GREEN}[✓] 系统运行正常${NC}"
    print_line
    exit 0
fi
