#
#  Copyright 2025 The InfiniFlow Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#

import logging
import time
from pathlib import Path

from minio import Minio
from minio.error import S3Error
from io import BytesIO
from plm.conf.settings import rep_settings
from plm.utils import singleton
from loguru import logger


@singleton
class PLMMinio:
    def __init__(self):
        self.conn = None
        self.__open__()

    def __open__(self):
        try:
            if self.conn:
                self.__close__()
        except Exception:
            pass

        try:
            self.conn = Minio(endpoint=rep_settings.MINIO_ENDPOINT.get_secret_value(),  # settings.MINIO["host"],
                              access_key=rep_settings.MINIO_ACCESSKEY.get_secret_value(),  # settings.MINIO["user"],
                              secret_key=rep_settings.MINIO_SECRETKEY.get_secret_value(),  # settings.MINIO["password"],
                              secure=False
                              )
        except Exception:
            logging.exception(
                "Fail to connect %s " % rep_settings.MINIO_ENDPOINT.get_secret_value())

    def __close__(self):
        del self.conn
        self.conn = None

    def health(self):
        bucket, fnm, binary = "txtxtxtxt1", "txtxtxtxt1", b"_t@@@1"
        if not self.conn.bucket_exists(bucket):
            self.conn.make_bucket(bucket)
        r = self.conn.put_object(bucket, fnm,
                                 BytesIO(binary),
                                 len(binary)
                                 )
        return r

    def fput(self, bucket, file_name, file_path):
        for _ in range(3):
            try:
                if not self.conn.bucket_exists(bucket):
                    self.conn.make_bucket(bucket)

                r = self.conn.fput_object(bucket_name=bucket,
                                          object_name=file_name,
                                          file_path=file_path
                                          )
                return r
            except Exception:
                logging.exception(f"Fail to put {bucket}/{file_name}:")
                self.__open__()
                time.sleep(1)

    def put(self, bucket, fnm, binary):
        for _ in range(3):
            try:
                if not self.conn.bucket_exists(bucket):
                    self.conn.make_bucket(bucket)

                r = self.conn.put_object(bucket, fnm,
                                         BytesIO(binary),
                                         len(binary)
                                         )
                return r
            except Exception:
                logging.exception(f"Fail to put {bucket}/{fnm}:")
                self.__open__()
                time.sleep(1)

    def rm(self, bucket, fnm):
        try:
            self.conn.remove_object(bucket, fnm)
        except Exception:
            logging.exception(f"Fail to remove {bucket}/{fnm}:")

    def fget(self, bucket, filename, file_path):
        """ download data of an object to local file path """
        for _ in range(1):
            try:
                self.conn.fget_object(bucket_name=bucket,
                                          object_name=filename,
                                          file_path=file_path
                                          )
                return file_path
            except Exception:
                logging.exception(f"Fail to get {bucket}/{filename}")
                self.__open__()
                time.sleep(1)
        return

    def get(self, bucket, filename):
        for _ in range(1):
            try:
                r = self.conn.get_object(bucket, filename)
                return r.read()
            except Exception:
                logging.exception(f"Fail to get {bucket}/{filename}")
                self.__open__()
                time.sleep(1)
        return

    def obj_exist(self, bucket, filename):
        try:
            if not self.conn.bucket_exists(bucket):
                return False
            if self.conn.stat_object(bucket, filename):
                return True
            else:
                return False
        except S3Error as e:
            if e.code in ["NoSuchKey", "NoSuchBucket", "ResourceNotFound"]:
                return False
        except Exception:
            logging.exception(f"obj_exist {bucket}/{filename} got exception")
            return False

    def get_presigned_url(self, bucket, fnm, expires):
        for _ in range(10):
            try:
                return self.conn.get_presigned_url("GET", bucket, fnm, expires)
            except Exception:
                logging.exception(f"Fail to get_presigned {bucket}/{fnm}:")
                self.__open__()
                time.sleep(1)
        return

    def remove_bucket(self, bucket):
        try:
            if self.conn.bucket_exists(bucket):
                objects_to_delete = self.conn.list_objects(bucket, recursive=True)
                for obj in objects_to_delete:
                    self.conn.remove_object(bucket, obj.object_name)
                self.conn.remove_bucket(bucket)
        except Exception:
            logging.exception(f"Fail to remove bucket {bucket}")


if __name__ == "__main__":
    # test
    minio_client = PLMMinio()
    logger.info(f'minio_client: {minio_client}')
    bucket = 'test'
    file_path = r'C:\Users\houzhimingwx1\Documents\01-code\00-hik-yf\Intelligent_QA\PLM2.0\assets\plm_docx\BOM 审核申请.docx'
    file_name = Path(file_path).name.replace(' ', '')
    logger.info(f'file name: {file_name}')
    fput_result = minio_client.fput(bucket, file_name, file_path)
    logger.info(f'file upload result: {fput_result}')
    # get_result = minio_client.get(bucket,file_name)
    # logger.info(f'file download: {get_result}')
    file_path = rf'C:\Users\houzhimingwx1\Documents\02-file\{file_name}'
    fget_result = minio_client.fget(bucket, file_name, file_path)
    logger.info(f'file download result: {fget_result}')


