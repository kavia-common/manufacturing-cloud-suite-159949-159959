from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, func, delete, update


from src.db.models.security import User, Role, Permission, UserRole, RolePermission
from .base import BaseRepository


class SecurityRepository(BaseRepository):
    """Repository for user/role/permission management within a tenant."""

    # Users
    async def get_user_by_email(self, email: str) -> Optional[User]:
        stmt = select(User).where(User.email == email)
        return await self.scalar_one_or_none(stmt)

    async def get_user_by_id(self, user_id: UUID) -> Optional[User]:
        stmt = select(User).where(User.id == user_id)
        return await self.scalar_one_or_none(stmt)

    async def count_users(self) -> int:
        stmt = select(func.count(User.id))
        result = await self.execute(stmt)
        return int(result.scalar_one())

    async def list_users(self, limit: int = 100, offset: int = 0) -> List[User]:
        stmt = select(User).order_by(User.created_at.desc()).offset(offset).limit(limit)
        result = await self.scalars(stmt)
        return list(result)

    async def create_user(
        self,
        *,
        email: str,
        full_name: Optional[str],
        hashed_password: str,
        is_active: bool = True,
        is_superadmin: bool = False,
    ) -> User:
        user = User(
            email=email,
            full_name=full_name,
            hashed_password=hashed_password,
            is_active=is_active,
            is_superadmin=is_superadmin,
        )
        await self.add(user)
        await self.commit()
        # refresh loaded state by reloading
        return (await self.get_user_by_email(email))  # type: ignore

    async def update_user(
        self,
        user_id: UUID,
        *,
        email: Optional[str] = None,
        full_name: Optional[str] = None,
        hashed_password: Optional[str] = None,
        is_active: Optional[bool] = None,
        is_superadmin: Optional[bool] = None,
    ) -> Optional[User]:
        values = {}
        if email is not None:
            values["email"] = email
        if full_name is not None:
            values["full_name"] = full_name
        if hashed_password is not None:
            values["hashed_password"] = hashed_password
        if is_active is not None:
            values["is_active"] = is_active
        if is_superadmin is not None:
            values["is_superadmin"] = is_superadmin

        if not values:
            return await self.get_user_by_id(user_id)

        stmt = (
            update(User)
            .where(User.id == user_id)
            .values(**values)
            .execution_options(synchronize_session="fetch")
        )
        await self.execute(stmt)
        await self.commit()
        return await self.get_user_by_id(user_id)

    async def delete_user(self, user_id: UUID) -> None:
        stmt = delete(User).where(User.id == user_id)
        await self.execute(stmt)
        await self.commit()

    async def list_roles_for_user(self, user_id: UUID) -> List[Role]:
        stmt = (
            select(Role)
            .join(UserRole, Role.id == UserRole.role_id)
            .where(UserRole.user_id == user_id)
        )
        result = await self.scalars(stmt)
        return list(result)

    # Roles
    async def list_roles(self, limit: int = 100, offset: int = 0) -> List[Role]:
        stmt = select(Role).order_by(Role.name).offset(offset).limit(limit)
        res = await self.scalars(stmt)
        return list(res)

    async def get_role_by_id(self, role_id: UUID) -> Optional[Role]:
        stmt = select(Role).where(Role.id == role_id)
        return await self.scalar_one_or_none(stmt)

    async def get_role_by_name(self, name: str) -> Optional[Role]:
        stmt = select(Role).where(Role.name == name)
        return await self.scalar_one_or_none(stmt)

    async def create_role(self, name: str, description: Optional[str] = None) -> Role:
        role = Role(name=name, description=description)
        await self.add(role)
        await self.commit()
        return (await self.get_role_by_name(name))  # type: ignore

    async def delete_role(self, role_id: UUID) -> None:
        stmt = delete(Role).where(Role.id == role_id)
        await self.execute(stmt)
        await self.commit()

    # Permissions
    async def ensure_permission(self, code: str, description: Optional[str] = None) -> Permission:
        stmt = select(Permission).where(Permission.code == code)
        perm = await self.scalar_one_or_none(stmt)
        if perm:
            return perm
        perm = Permission(code=code, description=description or code)
        await self.add(perm)
        await self.commit()
        stmt = select(Permission).where(Permission.code == code)
        return (await self.scalar_one_or_none(stmt))  # type: ignore

    # Associations
    async def assign_role_to_user(self, user_id: UUID, role_id: UUID) -> None:
        assoc = UserRole(user_id=user_id, role_id=role_id)
        await self.add(assoc)
        await self.commit()

    async def remove_role_from_user(self, user_id: UUID, role_id: UUID) -> None:
        stmt = delete(UserRole).where(UserRole.user_id == user_id, UserRole.role_id == role_id)
        await self.execute(stmt)
        await self.commit()

    async def add_permission_to_role(self, role_id: UUID, permission_id: UUID) -> None:
        assoc = RolePermission(role_id=role_id, permission_id=permission_id)
        await self.add(assoc)
        await self.commit()

    async def remove_permission_from_role(self, role_id: UUID, permission_id: UUID) -> None:
        stmt = delete(RolePermission).where(
            RolePermission.role_id == role_id,
            RolePermission.permission_id == permission_id,
        )
        await self.execute(stmt)
        await self.commit()
