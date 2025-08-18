from pymilvus import MilvusClient

client = MilvusClient(
    # uri="http://10.5.69.41:19053",
    uri="http://10.5.69.41:19530",
    token="root:Milvus"
)

print(client)

# 创建数据库
# client.create_database(
#     db_name="test",
# )

# 查看数据库列表
print('-----------client.list_databases()-------------')
print(client.list_databases())

# 查看数据库详情
print('-----------client.describe_database-------------')
print(client.describe_database(
    db_name="default"
))

client.use_database(db_name="test")


client.close()

