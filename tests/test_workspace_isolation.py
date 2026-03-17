"""Tests for workspace-level memory isolation."""

import pytest

from mnemos.dao import MemoryDao, UserDao
from mnemos.schemas import MemoryType


async def _setup_two_workspaces(session):
    """Create two users with separate workspaces. Return (ws1_id, ws2_id)."""
    dao = UserDao(session)
    _, ws1 = await dao.create_user_with_workspace("iso_user1", "pass1")
    _, ws2 = await dao.create_user_with_workspace("iso_user2", "pass2")
    return ws1, ws2


async def test_memories_isolated_by_workspace(session):
    ws1, ws2 = await _setup_two_workspaces(session)

    dao1 = MemoryDao(session, ws1)
    dao2 = MemoryDao(session, ws2)

    mid1, _ = await dao1.create("workspace 1 secret", MemoryType.fact, {}, [])
    mid2, _ = await dao2.create("workspace 2 secret", MemoryType.fact, {}, [])

    # ws1 cannot see ws2's memory
    assert await dao1.get(mid2) is None
    # ws2 cannot see ws1's memory
    assert await dao2.get(mid1) is None

    # Each workspace sees its own
    assert await dao1.get(mid1) is not None
    assert await dao2.get(mid2) is not None


async def test_cross_workspace_delete_rejected(session):
    ws1, ws2 = await _setup_two_workspaces(session)

    dao1 = MemoryDao(session, ws1)
    dao2 = MemoryDao(session, ws2)

    mid1, _ = await dao1.create("delete isolation test", MemoryType.fact, {}, [])

    # ws2 cannot delete ws1's memory
    with pytest.raises(ValueError):
        await dao2.delete(mid1)

    # ws1 can delete its own memory
    await dao1.delete(mid1)


async def test_cross_workspace_update_rejected(session):
    ws1, ws2 = await _setup_two_workspaces(session)

    dao1 = MemoryDao(session, ws1)
    dao2 = MemoryDao(session, ws2)

    mid1, _ = await dao1.create("update isolation test", MemoryType.fact, {}, [])

    # ws2 cannot update ws1's memory
    with pytest.raises(ValueError):
        await dao2.update(id=mid1, content="hacked", memory_type=MemoryType.fact)


async def test_workspace_search_isolation(session):
    from mnemos.search import hybrid_search

    ws1, ws2 = await _setup_two_workspaces(session)

    dao1 = MemoryDao(session, ws1)
    dao2 = MemoryDao(session, ws2)

    await dao1.create("unique phrase alpha in workspace one", MemoryType.fact, {}, [])
    await dao2.create("unique phrase beta in workspace two", MemoryType.fact, {}, [])

    results1 = await hybrid_search(
        session, "unique phrase", similarity_threshold=0.0, workspace_id=ws1
    )
    contents1 = [r.content for r in results1]
    assert any("alpha" in c for c in contents1)
    assert not any("beta" in c for c in contents1)

    results2 = await hybrid_search(
        session, "unique phrase", similarity_threshold=0.0, workspace_id=ws2
    )
    contents2 = [r.content for r in results2]
    assert any("beta" in c for c in contents2)
    assert not any("alpha" in c for c in contents2)


async def test_no_workspace_sees_all(session):
    """When workspace_id=None, no filtering is applied (dev mode)."""
    ws1, ws2 = await _setup_two_workspaces(session)

    dao1 = MemoryDao(session, ws1)
    dao2 = MemoryDao(session, ws2)

    mid1, _ = await dao1.create("global visible alpha", MemoryType.fact, {}, [])
    mid2, _ = await dao2.create("global visible beta", MemoryType.fact, {}, [])

    dao_global = MemoryDao(session, None)
    assert await dao_global.get(mid1) is not None
    assert await dao_global.get(mid2) is not None


async def test_multi_workspace_read(session):
    """User A can read from both own workspace and B's workspace after joining."""
    from mnemos.search import hybrid_search

    dao = UserDao(session)
    a_user_id, a_ws_id = await dao.create_user_with_workspace("multi_user_a", "passA")
    b_user_id, b_ws_id = await dao.create_user_with_workspace("multi_user_b", "passB")

    dao_b = MemoryDao(session, b_ws_id)
    await dao_b.create("multi workspace beta memory", MemoryType.fact, {}, [])

    # A accepts B's invite → A is now member of B's workspace too
    token = await dao.create_invite(b_ws_id, b_user_id)
    await dao.use_invite(token, a_user_id)

    # A reads with both workspaces
    results = await hybrid_search(
        session,
        "multi workspace",
        similarity_threshold=0.0,
        workspace_ids=[a_ws_id, b_ws_id],
    )
    assert any("beta" in r.content for r in results)

    # Store via A still goes to A's owned workspace only
    dao_a_write = MemoryDao(session, a_ws_id)
    await dao_a_write.create("multi workspace alpha memory", MemoryType.fact, {}, [])

    # B cannot see A's memory (B only reads from b_ws_id)
    results_b = await hybrid_search(
        session, "multi workspace", similarity_threshold=0.0, workspace_ids=[b_ws_id]
    )
    assert not any("alpha" in r.content for r in results_b)

    # A can see both
    results_a = await hybrid_search(
        session,
        "multi workspace",
        similarity_threshold=0.0,
        workspace_ids=[a_ws_id, b_ws_id],
    )
    contents = [r.content for r in results_a]
    assert any("alpha" in c for c in contents)
    assert any("beta" in c for c in contents)
