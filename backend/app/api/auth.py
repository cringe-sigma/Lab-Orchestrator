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
#  用户认证依赖
# ================================================================

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


# ================================================================
#  角色权限依赖
# ================================================================

def require_permission(permission: str):
    """依赖: 检查当前用户是否有指定权限"""
    async def checker(user: User = Depends(get_current_user)):
        allowed = ROLE_PERMISSIONS.get(user.role, set())
        if permission not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"权限不足: 需要 '{permission}'，当前角色 '{user.role}'",
            )
        return user
    return checker


async def require_admin(user: User = Depends(get_current_user)):
    """要求 admin 角色"""
    if user.role != UserRole.ADMIN.value:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要管理员权限")
    return user


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
async def my_permissions(user: User = Depends(get_current_user)):
    """查看当前用户的权限列表"""
    perms = ROLE_PERMISSIONS.get(user.role, set())
    role_labels = {"admin": "管理员", "user": "普通用户", "viewer": "观察者"}
    return {
        "role": user.role,
        "role_label": role_labels.get(user.role, user.role),
        "permissions": sorted(perms),
    }


# ================================================================
#  权限申请 (所有用户可申请更高级别角色)
# ================================================================

@router.post("/apply-permission")
async def apply_permission(data: PermissionApply, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """申请升级角色权限"""
    # 验证请求的角色是否合法
    valid_roles = list(ROLE_PERMISSIONS.keys())
    if data.requested_role not in valid_roles:
        raise HTTPException(status_code=400, detail=f"无效的角色: {data.requested_role}，可选: {valid_roles}")

    if data.requested_role == user.role:
        raise HTTPException(status_code=400, detail="不能申请与当前相同的角色")

    # 检查是否有待处理的相同申请
    existing = await db.execute(
        select(PermissionRequest).where(
            PermissionRequest.user_id == user.id,
            PermissionRequest.requested_role == data.requested_role,
            PermissionRequest.status == "pending",
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="已有相同角色的待审批申请")

    req = PermissionRequest(
        user_id=user.id,
        requested_role=data.requested_role,
        reason=data.reason,
        status="pending",
    )
    db.add(req)
    await db.commit()
    await db.refresh(req)
    return {"success": True, "request_id": req.id, "message": "权限申请已提交，等待管理员审批"}


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
        # 更新用户角色
        user = await db.get(User, req.user_id)
        if user:
            user.role = req.requested_role
        req.status = "approved"
    elif data.action == "reject":
        req.status = "rejected"
    else:
        raise HTTPException(status_code=400, detail="action 必须是 'approve' 或 'reject'")

    req.reviewed_by = admin.id
    req.review_comment = data.comment
    req.reviewed_at = datetime.utcnow()
    await db.commit()

    return {"success": True, "request_id": req.id, "status": req.status}
