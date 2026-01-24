FROM python:3.11-slim

WORKDIR /app

# 安装依赖
COPY pyproject.toml .
RUN pip install --no-cache-dir -e .

# 复制代码
COPY erp_common/ ./erp_common/
COPY services/item_service/ ./services/item_service/

# 暴露端口
EXPOSE 8001

# 启动命令
CMD ["uvicorn", "services.item_service.main:app", "--host", "0.0.0.0", "--port", "8001"]
