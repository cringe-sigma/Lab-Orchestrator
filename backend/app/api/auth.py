"""用户认证 + 角色权限控制"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Callable
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import bcrypt as _bcrypt
from jose import jwt, JWTError
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.config import settings
from app.db.database import get_db
from app.models.user import User, UserRole
from app.models.permission import PermissionRequest
from app.models.user_permission import UserPermissionOverride

router = APIRouter(prefix="/api/auth", tags=["认证"])
security = HTTPBearer()

# ================================================================
#  密码 & Token 工具
# ================================================================

def hash_password(password: str) -> str:
    return _bcrypt.hashpw(password.encode(), _bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    return _bcrypt.checkpw(password.encode(), hashed.encode())


def create_token(user_id: int, username: str, role: str) -> str:
    payload = {
        "sub": str(user_id),
        "username": username,
        "role": role,
        "exp": datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

# ================================================================
#  角色权限定义
# ================================================================
# 权限层级:
#   admin  — 全部权限 (管理用户/板子/实验/审批)
#   user   — 操作板子 + 创建实验 + 预约 (默认)
#   viewer — 只读查看 (不能操作板子)

ROLE_PERMISSIONS: dict[str, set[str]] = {
    "admin": {
        "boards:read", "boards:create", "boards:exec", "boards:delete",
        "experiments:read", "experiments:create", "experiments:run",
        "bookings:read", "bookings:create", "bookings:cancel",
        "users:read", "users:manage",       # 管理其他用户
        "permissions:read", "permissions:approve",  # 审批权限申请
        "ai:chat",                          # 使用AI助手
    },
    "user": {
        "boards:read", "boards:exec",
        "experiments:read", "experiments:create", "experiments:run",
        "bookings:read", "bookings:create", "bookings:cancel",
        "ai:chat",
        "permissions:read",                 # 查看自己的权限
    },
    "viewer": {
        "boards:read",
        "experiments:read",
        "bookings:read",
        "permissions:read",
    },
}

ROLE_LABELS = {"admin": "管理员", "user": "普通用户", "viewer": "观察者"}

PERMISSION_LABELS: dict[str, str] = {
    "boards:read": "查看板子列表",
    "boards:create": "添加/删除板子",
    "boards:exec": "操作板子(执行命令)",
    "boards:delete": "删除板子",
    "experiments:read": "查看实验",
    "experiments:create": "创建实验",
    "experiments:run": "运行实验",
    "bookings:read": "查看预约",
    "bookings:create": "创建预约",
    "bookings:cancel": "取消预约",
    "users:read": "查看用户列表",
    "users:manage": "管理用户(角色/禁用)",
    "permissions:read": "查看权限信息",
    "permissions:approve": "审批权限申请",
    "ai:chat": "使用AI助手",
}

ALL_PERMISSIONS = sorted(PERMISSION_LABELS.keys())


async def get_effective_permissions(user: User, db: AsyncSession) -> set[str]:
    """计算用户的有效权限 = 角色默认 + 个人 grants - 个人 revokes"""
    base = ROLE_PERMISSIONS.get(user.role, set()).copy()

    # 查询个人覆写
    result = await db.execute(
        select(UserPermissionOverride).where(
            UserPermissionOverride.user_id == user.id
        )
    )
    for override in result.scalars().all():
        if override.action == "grant":
            base.add(override.permission_key)
        elif override.action == "revoke":
            base.discard(override.permission_key)
    return base


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = int(payload["sub"])
    except (JWTError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的认证令牌")

    user = await db.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在或已禁用")
    return user


def require_permission(permission: str):
    """依赖: 检查当前用户是否有指定权限(角色+个人覆写)"""
    async def checker(
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ):
        effective = await get_effective_permissions(user, db)
        if permission not in effective:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"权限不足: 需要 '{PERMISSION_LABELS.get(permission, permission)}'",
            )
        return user
    return checker


async def require_admin(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """要求 admin 角色（或拥有 users:manage）"""
    effective = await get_effective_permissions(user, db)
    if "users:manage" not in effective:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要管理员权限")
    return user

# ================================================================
#  Pydantic 模型
# ================================================================

class UserCreate(BaseModel):
    username: str
    password: str
    display_name: str = ""


class UserLogin(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    username: str
    role: str


class UserInfo(BaseModel):
    id: int
    username: str
    display_name: str
    role: str
    is_active: bool


class UserListItem(BaseModel):
    id: int
    username: str
    display_name: str
    role: str
    is_active: bool
    created_at: str
    last_login: str | None


class PermissionApply(BaseModel):
    requested_role: str  # 申请的角色
    reason: str = ""


class PermissionReview(BaseModel):
    request_id: int
    action: str  # "approve" | "reject"
    comment: str = ""


class RoleInfo(BaseModel):
    """角色信息（供前端展示）"""
    role: str
    label: str           # 中文名
    permissions: list[str]
    can_apply: bool      # 是否可以申请此角色


# ================================================================
#  认证路由
# ================================================================

@router.post("/register", response_model=TokenResponse)
async def register(data: UserCreate, db: AsyncSession = Depends(get_db)):
    """注册新用户（默认 role=user）"""
    existing = await db.execute(select(User).where(User.username == data.username))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="用户名已存在")

    user = User(
        username=data.username,
        hashed_password=hash_password(data.password),
        display_name=data.display_name or data.username,
        role=UserRole.USER.value,  # 新注册默认 user 角色
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_token(user.id, user.username, user.role)
    return TokenResponse(access_token=token, user_id=user.id, username=user.username, role=user.role)


@router.post("/login", response_model=TokenResponse)
async def login(data: UserLogin, db: AsyncSession = Depends(get_db)):
    """用户登录"""
    result = await db.execute(select(User).where(User.username == data.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    user.last_login = datetime.utcnow()
    await db.commit()

    token = create_token(user.id, user.username, user.role)
    return TokenResponse(access_token=token, user_id=user.id, username=user.username, role=user.role)


@router.get("/me", response_model=UserInfo)
async def get_me(user: User = Depends(get_current_user)):
    """获取当前用户信息"""
    return UserInfo(id=user.id, username=user.username, display_name=user.display_name, role=user.role, is_active=user.is_active)


# ================================================================
#  权限信息查询 (所有角色可用)
# ================================================================

@router.get("/roles", response_model=list[RoleInfo])
async def list_roles(user: User = Depends(get_current_user)):
    """查看系统所有角色及其权限"""
    role_labels = {"admin": "管理员", "user": "普通用户", "viewer": "观察者"}
    roles = []
    for role_name, perms in ROLE_PERMISSIONS.items():
        can_apply = role_name != user.role  # 不能申请自己已有的角色
        roles.append(RoleInfo(
            role=role_name,
            label=role_labels.get(role_name, role_name),
            permissions=sorted(perms),
            can_apply=can_apply,
        ))
    return roles


@router.get("/my-permissions")
async def my_permissions(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """查看当前用户的有效权限列表(角色+个体覆写)"""
    effective = await get_effective_permissions(user, db)

    # 权限详情: 哪些来自角色，哪些是个体额外授予/被收回
    role_base = ROLE_PERMISSIONS.get(user.role, set())

    details = []
    for pk in sorted(ALL_PERMISSIONS):
        has = pk in effective
        from_role = pk in role_base
        detail = {"key": pk, "label": PERMISSION_LABELS.get(pk, pk), "has": has}
        if has and not from_role:
            detail["source"] = "grant"  # 个体额外授予
        elif not has and from_role:
            detail["source"] = "revoked"  # 角色本有但被收回
        elif has and from_role:
            detail["source"] = "role"  # 角色默认
        else:
            detail["source"] = None  # 没有此权限
        details.append(detail)

    return {
        "role": user.role,
        "role_label": ROLE_LABELS.get(user.role, user.role),
        "permissions": sorted(effective),
        "details": details,
        "all_permissions": ALL_PERMISSIONS,
    }


@router.get("/roles", response_model=list[RoleInfo])
async def list_roles(user: User = Depends(get_current_user)):
    """查看系统所有角色及其默认权限"""
    roles = []
    for role_name, perms in ROLE_PERMISSIONS.items():
        roles.append(RoleInfo(
            role=role_name,
            label=ROLE_LABELS.get(role_name, role_name),
            permissions=sorted(perms),
            can_apply=role_name != user.role,
        ))
    return roles


# ================================================================
#  权限申请 (可申请特定权限)
# ================================================================

@router.post("/apply-permission")
async def apply_permission(data: PermissionApply, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """申请权限 — 可以是整个角色升级或单个权限"""
    # 如果申请的是角色升级
    if data.requested_role in ROLE_PERMISSIONS:
        if data.requested_role == user.role:
            raise HTTPException(status_code=400, detail="不能申请与当前相同的角色")
        existing = await db.execute(
            select(PermissionRequest).where(
                PermissionRequest.user_id == user.id,
                PermissionRequest.requested_role == data.requested_role,
                PermissionRequest.status == "pending",
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="已有相同的待审批申请")
        detail = f"角色升级: {user.role} → {data.requested_role}"
    # 或申请单个权限
    elif data.requested_role in ALL_PERMISSIONS:
        effective = await get_effective_permissions(user, db)
        if data.requested_role in effective:
            raise HTTPException(status_code=400, detail="你已经拥有此权限")
        existing = await db.execute(
            select(PermissionRequest).where(
                PermissionRequest.user_id == user.id,
                PermissionRequest.requested_role == data.requested_role,
                PermissionRequest.status == "pending",
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="已有相同权限的待审批申请")
        detail = f"申请权限: {PERMISSION_LABELS.get(data.requested_role, data.requested_role)}"
    else:
        raise HTTPException(status_code=400, detail=f"无效的申请目标: {data.requested_role}")

    req = PermissionRequest(
        user_id=user.id,
        requested_role=data.requested_role,
        reason=data.reason,
        status="pending",
    )
    db.add(req)
    await db.commit()
    await db.refresh(req)
    return {"success": True, "request_id": req.id, "message": f"已提交: {detail}"}


@router.get("/my-permission-requests")
async def my_permission_requests(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """查看我的权限申请记录"""
    result = await db.execute(
        select(PermissionRequest).where(PermissionRequest.user_id == user.id).order_by(PermissionRequest.created_at.desc())
    )
    requests = result.scalars().all()
    return [
        {
            "id": r.id,
            "requested_role": r.requested_role,
            "reason": r.reason,
            "status": r.status,
            "review_comment": r.review_comment,
            "created_at": r.created_at.isoformat() if r.created_at else "",
            "reviewed_at": r.reviewed_at.isoformat() if r.reviewed_at else None,
        }
        for r in requests
    ]


# ================================================================
#  管理员 — 用户管理
# ================================================================

@router.get("/users", response_model=list[UserListItem])
async def list_users(db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)):
    """（管理员）查看所有用户"""
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    users = result.scalars().all()
    return [
        UserListItem(
            id=u.id, username=u.username, display_name=u.display_name,
            role=u.role, is_active=u.is_active,
            created_at=u.created_at.isoformat() if u.created_at else "",
            last_login=u.last_login.isoformat() if u.last_login else None,
        )
        for u in users
    ]


@router.put("/users/{user_id}/role")
async def update_user_role(user_id: int, data: dict, db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)):
    """（管理员）修改用户角色"""
    new_role = data.get("role", "")
    valid_roles = list(ROLE_PERMISSIONS.keys())
    if new_role not in valid_roles:
        raise HTTPException(status_code=400, detail=f"无效的角色: {new_role}，可选: {valid_roles}")

    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="不能修改自己的角色")

    old_role = user.role
    user.role = new_role
    await db.commit()
    return {"success": True, "user_id": user_id, "old_role": old_role, "new_role": new_role}


@router.put("/users/{user_id}/status")
async def toggle_user_status(user_id: int, data: dict, db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)):
    """（管理员）启用/禁用用户"""
    is_active = data.get("is_active", True)
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="不能操作自己的账号")

    user.is_active = is_active
    await db.commit()
    return {"success": True, "user_id": user_id, "is_active": is_active}


# ================================================================
#  管理员 — 权限审批
# ================================================================

@router.get("/permission-requests")
async def all_permission_requests(db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)):
    """（管理员）查看所有权限申请"""
    result = await db.execute(
        select(PermissionRequest).order_by(
            PermissionRequest.status == "pending",
            PermissionRequest.created_at.desc()
        )
    )
    reqs = result.scalars().all()
    return [
        {
            "id": r.id,
            "user_id": r.user_id,
            "requested_role": r.requested_role,
            "reason": r.reason,
            "status": r.status,
            "review_comment": r.review_comment,
            "created_at": r.created_at.isoformat() if r.created_at else "",
            "reviewed_at": r.reviewed_at.isoformat() if r.reviewed_at else None,
        }
        for r in reqs
    ]


@router.post("/review-permission")
async def review_permission(data: PermissionReview, db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)):
    """（管理员）审批权限申请"""
    req = await db.get(PermissionRequest, data.request_id)
    if not req:
        raise HTTPException(status_code=404, detail="申请不存在")
    if req.status != "pending":
        raise HTTPException(status_code=400, detail="该申请已处理")

    if data.action == "approve":
        req.status = "approved"
        # 判断是角色升级还是单项权限
        if req.requested_role in ROLE_PERMISSIONS:
            # 角色升级
            user = await db.get(User, req.user_id)
            if user:
                user.role = req.requested_role
        elif req.requested_role in ALL_PERMISSIONS:
            # 单项权限: 添加 grant 覆写
            existing = await db.execute(
                select(UserPermissionOverride).where(
                    UserPermissionOverride.user_id == req.user_id,
                    UserPermissionOverride.permission_key == req.requested_role,
                )
            )
            if not existing.scalar_one_or_none():
                override = UserPermissionOverride(
                    user_id=req.user_id,
                    permission_key=req.requested_role,
                    action="grant",
                    granted_by=admin.id,
                )
                db.add(override)
    elif data.action == "reject":
        req.status = "rejected"
    else:
        raise HTTPException(status_code=400, detail="action 必须是 'approve' 或 'reject'")

    req.reviewed_by = admin.id
    req.review_comment = data.comment
    req.reviewed_at = datetime.utcnow()
    await db.commit()

    return {"success": True, "request_id": req.id, "status": req.status}


# ================================================================
#  管理员 — 灵活管理任意用户的权限
# ================================================================

@router.get("/users/{user_id}/permissions")
async def get_user_permissions(user_id: int, db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin)):
    """（管理员）查看指定用户的完整权限详情（角色+覆写+所有权限状态）"""
    target = await db.get(User, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="用户不存在")

    effective = await get_effective_permissions(target, db)
    role_base = ROLE_PERMISSIONS.get(target.role, set())

    # 获取该用户的覆写记录
    overrides_result = await db.execute(
        select(UserPermissionOverride).where(UserPermissionOverride.user_id == user_id)
    )
    overrides = {
        o.permission_key: o.action
        for o in overrides_result.scalars().all()
    }

    details = []
    for pk in sorted(ALL_PERMISSIONS):
        has = pk in effective
        from_role = pk in role_base
        overridden = pk in overrides
        detail = {
            "key": pk,
            "label": PERMISSION_LABELS.get(pk, pk),
            "has": has,
            "from_role": from_role,
            "overridden": overridden,
            "override_action": overrides.get(pk),
        }
        details.append(detail)

    return {
        "user_id": user_id,
        "username": target.username,
        "role": target.role,
        "role_label": ROLE_LABELS.get(target.role, target.role),
        "permissions": sorted(effective),
        "details": details,
        "all_permissions": ALL_PERMISSIONS,
    }


@router.post("/users/{user_id}/permissions/grant")
async def grant_permission(
    user_id: int, data: dict,
    db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin),
):
    """（管理员）授予用户一项权限"""
    target = await db.get(User, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="用户不存在")
    if target.id == admin.id:
        raise HTTPException(status_code=400, detail="不能操作自己")

    perm = data.get("permission", "")
    if perm not in ALL_PERMISSIONS:
        raise HTTPException(status_code=400, detail=f"无效的权限: {perm}")

    effective = await get_effective_permissions(target, db)
    if perm in effective:
        raise HTTPException(status_code=400, detail="用户已拥有此权限")

    # 检查是否已有覆写记录
    result = await db.execute(
        select(UserPermissionOverride).where(
            UserPermissionOverride.user_id == user_id,
            UserPermissionOverride.permission_key == perm,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        existing.action = "grant"
    else:
        override = UserPermissionOverride(
            user_id=user_id, permission_key=perm, action="grant", granted_by=admin.id
        )
        db.add(override)
    await db.commit()

    return {"success": True, "message": f"已授予权限: {PERMISSION_LABELS.get(perm, perm)}"}


@router.post("/users/{user_id}/permissions/revoke")
async def revoke_permission(
    user_id: int, data: dict,
    db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin),
):
    """（管理员）收回用户一项权限"""
    target = await db.get(User, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="用户不存在")
    if target.id == admin.id:
        raise HTTPException(status_code=400, detail="不能操作自己")

    perm = data.get("permission", "")
    if perm not in ALL_PERMISSIONS:
        raise HTTPException(status_code=400, detail=f"无效的权限: {perm}")

    effective = await get_effective_permissions(target, db)
    if perm not in effective:
        raise HTTPException(status_code=400, detail="用户本来就没有此权限")

    # 检查是否已有覆写记录
    result = await db.execute(
        select(UserPermissionOverride).where(
            UserPermissionOverride.user_id == user_id,
            UserPermissionOverride.permission_key == perm,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        existing.action = "revoke"
    else:
        override = UserPermissionOverride(
            user_id=user_id, permission_key=perm, action="revoke", granted_by=admin.id
        )
        db.add(override)
    await db.commit()

    return {"success": True, "message": f"已收回权限: {PERMISSION_LABELS.get(perm, perm)}"}


@router.post("/users/{user_id}/permissions/reset")
async def reset_permission(
    user_id: int, data: dict,
    db: AsyncSession = Depends(get_db), admin: User = Depends(require_admin),
):
    """（管理员）重置一项权限（删除覆写，恢复角色默认）"""
    target = await db.get(User, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="用户不存在")

    perm = data.get("permission", "")
    result = await db.execute(
        select(UserPermissionOverride).where(
            UserPermissionOverride.user_id == user_id,
            UserPermissionOverride.permission_key == perm,
        )
    )
    existing = result.scalar_one_or_none()
    if existing:
        await db.delete(existing)
        await db.commit()
        return {"success": True, "message": "覆写已删除，恢复角色默认"}
    return {"success": True, "message": "无覆写记录，无需操作"}
