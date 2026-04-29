from auth_service.infrastructure.db.base import Base as AuthBase
from auth_service.infrastructure.db.models import UserAuthRecord
from user_service.infrastructure.db.base import Base as UserBase
from user_service.infrastructure.db.models import (
    DepartmentRecord,
    MenuRecord,
    RoleRecord,
    UserRecord,
    role_menus,
    user_roles,
)


def test_user_service_models_use_user_metadata() -> None:
    assert UserRecord.__tablename__ == "users"
    assert DepartmentRecord.__tablename__ == "departments"
    assert RoleRecord.__tablename__ == "roles"
    assert MenuRecord.__tablename__ == "menus"
    assert user_roles.name == "user_roles"
    assert role_menus.name == "role_menus"
    assert "user_auths" not in UserBase.metadata.tables


def test_auth_service_model_is_independent_from_user_metadata() -> None:
    assert UserAuthRecord.__tablename__ == "user_auths"
    assert "users" not in AuthBase.metadata.tables
    assert "user_auths" in AuthBase.metadata.tables
