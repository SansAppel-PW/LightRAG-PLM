#!/bin/bash

# 等待依赖服务就绪
echo "Waiting for services to be ready..."
wait-for-it -t 0 ${REDIS_HOST}:${REDIS_PORT}
wait-for-it -t 0 ${POSTGRES_HOST}:${POSTGRES_PORT}
wait-for-it -t 0 ${MINIO_ENDPOINT}
wait-for-it -t 0 ${ELASTIC_HOST}:${ELASTIC_PORT}

# 运行数据迁移（若需要）
# python manage.py migrate

# 启动应用
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
