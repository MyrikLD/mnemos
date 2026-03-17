import pytest

from mnemos.dao.user import UserDao


async def test_register_creates_workspace(session):
    dao = UserDao(session)
    user_id, workspace_id = await dao.create_user_with_workspace("alice", "password123")
    assert user_id > 0
    assert workspace_id > 0


async def test_duplicate_username_raises(session):
    dao = UserDao(session)
    await dao.create_user_with_workspace("bob", "password123")
    with pytest.raises(ValueError, match="already taken"):
        await dao.create_user_with_workspace("bob", "differentpassword")


async def test_authenticate_success(session):
    dao = UserDao(session)
    user_id, workspace_id = await dao.create_user_with_workspace("carol", "mypassword")
    result = await dao.authenticate("carol", "mypassword")
    assert result is not None
    assert result[0] == user_id
    assert result[1] == workspace_id


async def test_authenticate_wrong_password(session):
    dao = UserDao(session)
    await dao.create_user_with_workspace("dave", "correctpassword")
    result = await dao.authenticate("dave", "wrongpassword")
    assert result is None


async def test_authenticate_unknown_user(session):
    dao = UserDao(session)
    result = await dao.authenticate("noone", "password")
    assert result is None


async def test_invite_flow(session):
    dao = UserDao(session)
    owner_id, workspace_id = await dao.create_user_with_workspace("owner1", "pass123")
    invitee_id, _ = await dao.create_user_with_workspace("invitee1", "pass456")

    token = await dao.create_invite(workspace_id, owner_id)
    assert len(token) == 64

    # First use succeeds
    result_ws = await dao.use_invite(token, invitee_id)
    assert result_ws == workspace_id

    # Second use returns None (already used)
    result2 = await dao.use_invite(token, invitee_id)
    assert result2 is None


async def test_invite_expired(session):
    from datetime import datetime, timedelta
    import sqlalchemy as sa
    from mnemos.models.workspace_invite import WorkspaceInvite

    dao = UserDao(session)
    owner_id, workspace_id = await dao.create_user_with_workspace("owner2", "pass123")
    user_id, _ = await dao.create_user_with_workspace("user2", "pass456")

    token = await dao.create_invite(workspace_id, owner_id)

    # Force-expire the token
    await session.execute(
        sa.update(WorkspaceInvite)
        .where(WorkspaceInvite.token == token)
        .values(expires_at=datetime(2000, 1, 1))
    )

    result = await dao.use_invite(token, user_id)
    assert result is None
