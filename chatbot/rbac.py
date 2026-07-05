"""
RBAC Redirection Stub for backwards compatibility.
"""
from backend.core.rbac import (
    UserRole,
    Permission,
    ROLE_PERMISSIONS,
    AuthorizationService,
    require_role,
    require_permission,
    AuthErrorResponse,
    role_validation_middleware
)
