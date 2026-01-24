# 订单中心服务 Dockerfile
FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY pyproject.toml ./

# 安装 Python 依赖
RUN pip install --no-cache-dir -e .

# 复制公共模块
COPY erp_common ./erp_common

# 复制服务代码
COPY services/order_service ./services/order_service

# 暴露端口
EXPOSE 8007

# 启动服务
CMD ["uvicorn", "services.order_service.main:app", "--host", "0.0.0.0", "--port", "8007"]
