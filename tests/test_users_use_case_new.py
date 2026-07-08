from uuid import uuid4

from app.domain.users import User
from app.use_cases.users import (
    CreateUserCommand,
    CreateUserUseCase,
    DeleteUserUseCase,
    GetUserUseCase,
    ListUsersUseCase,
    RestoreUserUseCase,
    SoftDeleteUserUseCase,
    UpdateUserCommand,
    UpdateUserUseCase,
    UserListQuery,
)


class FakeRepository:
    def __init__(self, user: User | None = None):
        self.user = user
        self.created = None
        self.updated = None
        self.deleted = None
        self.listed_query = None

    def create_user(self, command: CreateUserCommand) -> User | None:
        self.created = command
        self.user = User(
            user_id=uuid4(),
            login=command.login,
            name=command.name,
            role=command.role,
            category=command.category or 0,
            city=command.city,
            created_by=command.created_by,
            created_at=1,
            position=command.position,
            is_active=command.is_active,
            deleted=False,
        )
        return self.user

    def get_user(self, user_id):
        if self.user and self.user.user_id == user_id:
            return self.user
        return None

    def update_user(self, user_id, **kwargs):
        if self.user is None or self.user.user_id != user_id:
            return None
        self.updated = kwargs
        self.user = self.user.with_updates(
            login=kwargs.get("login"),
            name=kwargs.get("name"),
            role=kwargs.get("role"),
            category=kwargs.get("category"),
            city=kwargs.get("city"),
            position=kwargs.get("position"),
            is_active=kwargs.get("is_active"),
            deleted=kwargs.get("deleted"),
        )
        return self.user

    def delete_user(self, user_id):
        self.deleted = user_id
        return self.user is not None and self.user.user_id == user_id

    def list_users(self, query: UserListQuery):
        self.listed_query = query
        return [self.user] if self.user is not None else []


def test_create_user_use_case():
    repository = FakeRepository()
    command = CreateUserCommand(
        login="test_user",
        password="secret",
        name="Test User",
        role="admin",
        category=1,
        city=uuid4(),
        created_by=uuid4(),
        position=uuid4(),
        is_active=False,
    )

    result = CreateUserUseCase(repository=repository).execute(command)

    assert result.login == "test_user"
    assert repository.created is not None


def test_update_user_use_case():
    existing_user = User(
        user_id=uuid4(),
        login="test_user",
        name="Test User",
        role="admin",
        category=1,
        city=uuid4(),
        created_by=uuid4(),
        created_at=1,
        position=uuid4(),
        is_active=True,
        deleted=False,
    )
    repository = FakeRepository(user=existing_user)

    result = UpdateUserUseCase(repository=repository).execute(
        UpdateUserCommand(
            user_id=existing_user.user_id,
            login="updated_user",
            position=uuid4(),
            is_active=False,
            deleted=True,
        )
    )

    assert result.login == "updated_user"
    assert result.deleted is True
    assert result.position is not None
    assert result.is_active is False


def test_soft_delete_user_use_case():
    existing_user = User(
        user_id=uuid4(),
        login="test_user",
        name="Test User",
        role="admin",
        category=1,
        city=uuid4(),
        created_by=uuid4(),
        created_at=1,
        position=uuid4(),
        is_active=True,
        deleted=False,
    )
    repository = FakeRepository(user=existing_user)

    result = SoftDeleteUserUseCase(repository=repository).execute(
        existing_user.user_id
    )

    assert result.deleted is True


def test_restore_user_use_case():
    existing_user = User(
        user_id=uuid4(),
        login="test_user",
        name="Test User",
        role="admin",
        category=1,
        city=uuid4(),
        created_by=uuid4(),
        created_at=1,
        position=uuid4(),
        is_active=True,
        deleted=True,
    )
    repository = FakeRepository(user=existing_user)

    result = RestoreUserUseCase(repository=repository).execute(existing_user.user_id)

    assert result.deleted is False


def test_delete_user_use_case():
    existing_user = User(
        user_id=uuid4(),
        login="test_user",
        name="Test User",
        role="admin",
        category=1,
        city=uuid4(),
        created_by=uuid4(),
        created_at=1,
        position=uuid4(),
        is_active=True,
        deleted=False,
    )
    repository = FakeRepository(user=existing_user)

    result = DeleteUserUseCase(repository=repository).execute(existing_user.user_id)

    assert result is True


def test_get_and_list_user_use_cases():
    existing_user = User(
        user_id=uuid4(),
        login="test_user",
        name="Test User",
        role="admin",
        category=1,
        city=uuid4(),
        created_by=uuid4(),
        created_at=1,
        deleted=False,
    )
    repository = FakeRepository(user=existing_user)

    found = GetUserUseCase(repository=repository).execute(existing_user.user_id)
    listed = ListUsersUseCase(repository=repository).execute(
        UserListQuery(position=existing_user.position, is_active=True)
    )

    assert found.user_id == existing_user.user_id
    assert listed[0].user_id == existing_user.user_id
    assert repository.listed_query is not None
    assert repository.listed_query.position == existing_user.position
    assert repository.listed_query.is_active is True
