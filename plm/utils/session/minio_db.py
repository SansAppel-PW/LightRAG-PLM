import asyncio
from minio import Minio
from minio.error import S3Error
import os
import io
import aiofiles
from minio.datatypes import Part
from concurrent.futures import ThreadPoolExecutor


class AsyncMinioClient:
    def __init__(self, endpoint: str, access_key: str, secret_key: str, secure: bool = False):
        self.client = Minio(
            endpoint=endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure
        )

        self._executor = ThreadPoolExecutor(max_workers=16)  # 线程池，根据实际需求调整大小

    async def _run_sync(self, func, *args, **kwargs):
        loop = asyncio.get_running_loop()
        try:
            return await loop.run_in_executor(self._executor, lambda: func(*args, **kwargs))
        except S3Error as e:
            print(f"S3 Error: {e}")
            raise

    # 创建bucket
    async def create_bucket(self, bucket_name: str):
        if not await self._run_sync(self.client.bucket_exists, bucket_name):
            await self._run_sync(self.client.make_bucket, bucket_name)

    # 分片上传
    async def multipart_upload(self, bucket: str, object_name: str, file_path: str,
                               chunk_size: int = 5 * 1024 * 1024) -> None:
        """
        异步分片上传大文件
        """
        # 初始化分片上传
        upload_id = await self._run_sync(
            self.client._create_multipart_upload,
            bucket_name=bucket,
            object_name=object_name,
            headers={"Content-Type": "application/octet-stream"}
        )

        print(f"uplaod_id ={upload_id}")

        parts = []
        part_number = 1

        try:
            async with aiofiles.open(file_path, 'rb') as file:
                while True:
                    chunk = await file.read(chunk_size)
                    if not chunk:
                        break

                    # 上传分片
                    result = await self._run_sync(
                        self.client._upload_part,
                        bucket_name=bucket,
                        object_name=object_name,
                        part_number=part_number,
                        upload_id=upload_id,
                        data=chunk,
                        headers={}
                    )

                    parts.append(Part(part_number, result))
                    part_number += 1

            # 完成分片上传
            await self._run_sync(
                self.client._complete_multipart_upload,
                bucket_name=bucket,
                object_name=object_name,
                upload_id=upload_id,
                parts=parts
            )
        except Exception as e:
            await self._run_sync(
                self.client._abort_multipart_upload,
                bucket_name=bucket,
                object_name=object_name,
                upload_id=upload_id
            )
            raise e

    # 分片下载
    async def concurrent_download(self, bucket: str, object_name: str, file_path: str,
                                  chunk_size: int = 5 * 1024 * 1024) -> None:
        """
        并发分片下载文件
        """
        # 获取文件大小
        stat = await self._run_sync(
            self.client.stat_object,
            bucket_name=bucket,
            object_name=object_name
        )
        total_size = stat.size

        # 预创建空文件
        async with aiofiles.open(file_path, 'wb') as f:
            await f.truncate(total_size)

        # 创建下载任务
        tasks = []
        for offset in range(0, total_size, chunk_size):
            remaining = total_size - offset
            length = min(remaining, chunk_size)
            end = offset + length - 1

            tasks.append(
                self._download_chunk(
                    bucket=bucket,
                    object_name=object_name,
                    file_path=file_path,
                    start=offset,
                    end=end
                )
            )

        await asyncio.gather(*tasks)

    async def _download_chunk(self, bucket: str, object_name: str,
                              file_path: str, start: int, end: int):
        response = await self._run_sync(
            self.client.get_object,
            bucket_name=bucket,
            object_name=object_name,
            offset=start,
            length=end - start + 1
        )

        async with aiofiles.open(file_path, 'r+b') as f:
            await f.seek(start)
            chunk = await self._run_sync(response.read)
            await f.write(chunk)
            response.close()
            response.release_conn()

    # 上传
    async def upload_file(self, bucket_name, object_name, file_path):
        """
        异步上传文件
        """
        try:
            return await self._run_sync(self.client.fput_object,
                                        bucket_name=bucket_name,
                                        object_name=object_name,
                                        file_path=file_path)
        except S3Error as e:
            return False, f"Error uploading file: {e}"

    # 下载
    async def download_file(self, bucket_name, object_name, file_path):
        """
        异步下载文件
        :param bucket_name:
        :param object_name:
        :param file_path:
        :return:
        """
        try:
            # 确保保存路径的目录存在
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            return await self._run_sync(self.client.fget_object,
                                        bucket_name=bucket_name,
                                        object_name=object_name,
                                        file_path=file_path)
        except S3Error as e:
            raise e

    async def upload_object(self, bucket_name, object_name, file_stream, length):
        """
        异步上传对象
        """
        try:
            return await self._run_sync(self.client.put_object,
                                        bucket_name=bucket_name,
                                        object_name=object_name,
                                        data=file_stream,
                                        length=length)
        except S3Error as e:
            return False, f"Error uploading file: {e}"


class MinIOClient:
    def __init__(self, endpoint, access_key, secret_key, secure=False):
        """
        初始化 MinIO 客户端
        :param endpoint: MinIO 服务器的地址，例如: "play.min.io"
        :param access_key: 访问密钥 (Access Key)
        :param secret_key: 密钥 (Secret Key)
        :param secure: 是否启用 HTTPS，默认为 True
        """
        self.client = Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=secure)
        self.__chunk_size = 16 * 1024 * 1024  # 16MB（Minio分片最小要求）

    @property
    def chunk_size(self):
        return self.__chunk_size

    def create_bucket(self, bucket_name):
        """
        创建一个新的 bucket
        :param bucket_name: bucket 名称
        """
        try:
            if not self.client.bucket_exists(bucket_name):
                self.client.make_bucket(bucket_name)
                print(f"Bucket '{bucket_name}' 已创建。")
            else:
                print(f"Bucket '{bucket_name}' 已存在。")
        except S3Error as e:
            print(f"创建 bucket 时出错: {e}")
            raise e

    def upload_file(self, bucket_name, object_name, file_path):
        """
        上传文件到指定的 bucket
        :param bucket_name: bucket 名称
        :param object_name: 上传到 MinIO 后的文件名称
        :param file_path: 本地文件路径
        """
        try:
            self.create_bucket(bucket_name)  # 自动创建 bucket
            self.client.fput_object(bucket_name, object_name, file_path)
            print(f"文件 '{file_path}' 已上传为 '{object_name}'。")
        except S3Error as e:
            print(f"上传文件时出错: {e}")

    def upload_object(self, bucket_name, object_name, file_stream, length):
        try:
            return self.client.put_object(bucket_name=bucket_name,
                                          object_name=object_name,
                                          data=file_stream,
                                          length=length)
        except S3Error as e:
            return False, f"Error uploading file: {e}"

    def download_file(self, bucket_name, object_name, file_path):
        """
        从指定的 bucket 下载文件
        :param bucket_name: bucket 名称
        :param object_name: MinIO 中的文件名称
        :param file_path: 本地保存路径
        """
        try:
            # 确保保存路径的目录存在
            os.makedirs(os.path.dirname(file_path), exist_ok=True)

            self.client.fget_object(bucket_name, object_name, file_path)
            print(f"文件 '{object_name}' 已下载到 '{file_path}'。")
        except S3Error as e:
            print(f"下载文件时出错: {e}")

    def list_files(self, bucket_name, prefix=""):
        """
        列出 bucket 中的所有文件
        :param bucket_name: bucket 名称
        :param prefix: 文件前缀（可选）
        :return: 文件对象列表
        """
        try:
            objects = self.client.list_objects(bucket_name, prefix=prefix, recursive=True)
            print(f"Bucket '{bucket_name}' 中的文件列表：")
            for obj in objects:
                print(f"文件名: {obj.object_name}, 大小: {obj.size} B")
            return objects
        except S3Error as e:
            print(f"列出文件时出错: {e}")
            return []

    def multipart_upload(self, bucket_name: str, object_name: str, in_bytes):
        upload_id = None
        try:
            # 初始化分片上传
            upload_id = self.client._create_multipart_upload(
                bucket_name=bucket_name,
                object_name=object_name,
                headers={"Content-Type": "application/octet-stream"}
            )
            part_number = 1
            parts = []
            buffer = b''
            input_io = io.BytesIO(in_bytes)
            while True:
                chunk = input_io.read(1024 * 1024 * 16)  # 每次读取16MB
                if not chunk:
                    break  # 结束
                buffer += chunk

                # 当缓冲区达到分块大小时上传
                while len(buffer) >= self.chunk_size:
                    part_data = buffer[:self.chunk_size]
                    buffer = buffer[self.chunk_size:]

                    # 上传分片
                    result = self.client._upload_part(
                        bucket_name=bucket_name,
                        object_name=object_name,
                        upload_id=upload_id,
                        part_number=part_number,
                        data=part_data,
                        headers={},
                    )
                    parts.append(Part(part_number, result))
                    part_number += 1
            # 处理剩余数据
            if buffer:
                result = self.client._upload_part(
                    bucket_name=bucket_name,
                    object_name=object_name,
                    upload_id=upload_id,
                    part_number=part_number,
                    data=buffer,
                    headers={},
                )
                parts.append(Part(part_number, result))
            # 完成分片上传
            self.client._complete_multipart_upload(
                bucket_name=bucket_name,
                object_name=object_name,
                upload_id=upload_id,
                parts=parts
            )

            return {"message": "File converted and uploaded successfully",
                    "object_name": object_name}  # TODO maybe address
        except Exception as e:
            # 错误处理
            if upload_id:
                try:
                    self.client._abort_multipart_upload(
                        bucket_name=bucket_name,
                        object_name=object_name,
                        upload_id=upload_id,
                    )
                except S3Error:
                    raise S3Error
            raise e


# 使用示例
async def main():
    # 初始化客户端
    minio_client = AsyncMinioClient(
        endpoint="localhost:9000",
        access_key="xUOqfgZFZIn5AtC1",
        secret_key="4idsuQLCaq7lNfMBBdqug6zhCPGy2zjB",
        secure=False
    )

    # 分片上传示例
    await minio_client.multipart_upload(
        bucket="test",
        object_name="large-file.zip",
        file_path="/home/mluo/Documents/xiaohai_project/方案文档.7z",
        chunk_size=10 * 1024 * 1024  # 10MB chunks
    )

    # 并发下载示例
    await minio_client.concurrent_download(
        bucket="test",
        object_name="large-file.zip",
        file_path="/home/mluo/Documents/xiaohai_project/方案文档_download.7z",
        chunk_size=10 * 1024 * 1024
    )

    #
    await minio_client.upload_file("test", "large-file-0.zip", "/home/mluo/Documents/xiaohai_project/方案文档.7z")

    #
    await minio_client.download_file("test", 'large-file-0.zip', "/home/mluo/Documents/xiaohai_project/XXX.7z")


from plm.conf.settings import rep_settings

minio_client = MinIOClient(
    endpoint=rep_settings.MINIO_ENDPOINT,
    access_key=rep_settings.MINIO_ACCESSKEY,
    secret_key=rep_settings.MINIO_SECRETKEY
)

if __name__ == "__main__":
    asyncio.run(main())
