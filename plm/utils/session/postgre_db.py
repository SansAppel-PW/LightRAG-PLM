from collections.abc import Generator
from contextlib import contextmanager
from typing import TypeVar, Type, Any, Optional, List

from sqlalchemy import exc
from sqlalchemy.engine.create import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker, Session
from plm.conf.settings import rep_settings
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession,
    async_sessionmaker,
)
from contextlib import asynccontextmanager


ModelType = TypeVar('ModelType', bound='Base')

class AsyncPostgreDatabase:
    def __init__(self, db_url: str, echo: bool = False):
        self.engine = create_async_engine(
            db_url,
            echo=echo,
            pool_size=64,
            max_overflow=20,
            pool_recycle=3600
        )
        self.async_session = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False  # 避免提交后对象过期
        )

    @asynccontextmanager
    async def get_db_session(self) -> AsyncSession:
        """获取可复用的异步 Session"""
        session = self.async_session()
        try:
            yield session
            # await session.commit() # 自动提交
        except Exception as e:
            await session.rollback()  # 自动回滚
            raise e
        finally:
            await session.close()

    @asynccontextmanager
    async def transaction(self) -> AsyncSession:
        """事务管理器（显式事务控制）"""
        async with self.get_db_session() as session:
            try:
                await session.begin()  # 显式开启事务
                yield session
                await session.commit()  # 手动提交
            except Exception as e:
                await session.rollback()
                raise e


class PostgreDataBase:
    def __init__(self, db_url: str, **engine_kwargs):
        """
            数据库操作封装类
        :param db_url: 数据库连接字符串
        :param engine_kwargs: 引擎配置参数
        """
        self.db_url = db_url
        self.engine = None
        self.session_factory = None
        self.connect(**engine_kwargs)

    def connect(self, **engine_kwargs) -> None:
        """ Create Database """
        self.engine = create_engine(
            self.db_url,
            pool_size=rep_settings.POSTGRES_POOL_SIZE,
            max_overflow=rep_settings.POSTGRES_MAX_OVERFLOW,
            pool_pre_ping=rep_settings.POSTGRES_POOL_PRE_PIN,
            **engine_kwargs
        )
        self.session_factory = scoped_session(
            sessionmaker(
                bind=self.engine,
                autocommit=rep_settings.POSTGRES_AUTO_COMMIT,
                autoflush=rep_settings.POSTGRES_AUTO_FLUSH,
            )
        )

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """ 获取数据库会话上下文 """
        session: Session = self.session_factory()
        try:
            yield session
            # session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    @contextmanager
    def transaction(self) -> Generator[Session, None, None]:
        """ 事务上下文管理器 """
        session: Session = self.session_factory()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def add(self, instance: ModelType) -> ModelType:
        """ 添加单个记录 """
        with self.get_session() as session:
            try:
                session.add(instance)
                session.flush()
                session.refresh(instance)
                return instance
            except exc.SQLAlchemyError as e:
                raise e

    def delete(self, model: Type[ModelType], record_id: Any) -> bool:
        """删除指定记录"""
        with self.get_session() as session:
            instance = session.get(model, record_id)
            if instance:
                session.delete(instance)
                return True
            return False

    def update(self, instance: ModelType, update_data: dict) -> ModelType:
        """更新记录"""
        with self.get_session() as session:
            try:
                for key, value in update_data.items():
                    setattr(instance, key, value)
                session.add(instance)
                session.flush()
                session.refresh(instance)
                return instance
            except exc.SQLAlchemyError as e:
                raise e

    def get_by_id(self, model: Type[ModelType], record_id: Any) -> Optional[ModelType]:
        """根据ID获取记录"""
        with self.get_session() as session:
            return session.get(model, record_id)

    def get_all(
            self,
            model: Type[ModelType],
            *,
            skip: int = 0,
            limit: int = 100
    ) -> List[ModelType]:
        """获取所有记录"""
        with self.get_session() as session:
            return session.query(model).offset(skip).limit(limit).all()

    def filter(
            self,
            model: Type[ModelType],
            *filters,
            order_by: Optional[Any] = None,
            skip: int = 0,
            limit: int = 100
    ) -> List[ModelType]:
        """条件查询"""
        with self.get_session() as session:
            query = session.query(model).filter(*filters)
            if order_by is not None:
                query = query.order_by(order_by)
            return query.offset(skip).limit(limit).all()

    def execute(self, sql: str, **params) -> Any:
        """执行原生SQL"""
        with self.get_session() as session:
            return session.execute(sql, params)

    def get_paginated(
            self,
            model: Type[ModelType],
            *,
            page: int = 1,
            per_page: int = 20,
            **filters
    ) -> dict:
        """分页查询"""
        with self.get_session() as session:
            query = session.query(model).filter_by(**filters)
            total = query.count()
            items = query.offset((page - 1) * per_page).limit(per_page).all()
            return {
                'total': total,
                'items': items,
                'page': page,
                'per_page': per_page
            }
