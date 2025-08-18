from pymilvus import MilvusClient

client = MilvusClient(
    uri="http://10.5.69.41:19053",
    token="root:Milvus"
)

print(client)

