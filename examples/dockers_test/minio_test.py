from minio import Minio
from minio.error import S3Error

# 初始化 MinIO 客户端
client = Minio(
    "10.5.69.41:9900",  # MinIO 服务地址（不带 http:// 或 https://）
    access_key="admin",
    secret_key="admin123",
    secure=False  # 如果使用 HTTPS 则设为 True
)

print(client)

# 测试连接：列出所有存储桶
try:
    buckets = client.list_buckets()
    for bucket in buckets:
        print(f"Bucket: {bucket.name}, Created: {bucket.creation_date}")
except S3Error as e:
    print(f"连接或操作失败: {e}")