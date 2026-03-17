import asyncio

import pytest
import pytest_asyncio
import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.engine.url import make_url
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from mnemos.config import settings
from mnemos.models.base import Base


@pytest.fixture(scope="session")
def test_db_url(worker_id):
    url = make_url(settings.db_url)
    root_url = url.set(database=None)
    test_db_name = f"test_{worker_id}"

    async def setup():
        root_engine = create_async_engine(root_url)
        async with root_engine.connect() as conn:
            conn = await conn.execution_options(isolation_level="AUTOCOMMIT")
            await conn.execute(text(f"DROP DATABASE IF EXISTS {test_db_name}"))
            await conn.execute(text(f"CREATE DATABASE {test_db_name}"))
        await root_engine.dispose()

        engine = create_async_engine(url.set(database=test_db_name))
        async with engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            await conn.run_sync(Base.metadata.create_all)
        await engine.dispose()

    asyncio.run(setup())
    yield url.set(database=test_db_name)

    async def cleanup():
        root_engine = create_async_engine(root_url)
        async with root_engine.connect() as conn:
            conn = await conn.execution_options(isolation_level="AUTOCOMMIT")
            await conn.execute(text(f"DROP DATABASE IF EXISTS {test_db_name}"))
        await root_engine.dispose()

    try:
        asyncio.run(cleanup())
    except Exception as e:
        print(f"Warning: failed to drop test database: {e}")


@pytest_asyncio.fixture
async def session(test_db_url):
    engine = create_async_engine(test_db_url)
    async with engine.connect() as conn:
        async with AsyncSession(bind=conn, expire_on_commit=False) as s:
            yield s
    await engine.dispose()


@pytest_asyncio.fixture
async def workspace_id(session):
    """Create a test user + workspace and return the workspace_id."""
    from mnemos.dao.user import UserDao

    dao = UserDao(session)
    try:
        _, ws_id = await dao.create_user_with_workspace("_test_default", "testpassword")
    except ValueError:
        # Already exists (e.g., in parallel runs) - look it up
        from mnemos.models.workspace import Workspace
        from mnemos.models.user import User

        ws_id = await session.scalar(
            sa.select(Workspace.id)
            .join(User, Workspace.owner_id == User.id)
            .where(User.username == "_test_default")
            .limit(1)
        )
    return ws_id
