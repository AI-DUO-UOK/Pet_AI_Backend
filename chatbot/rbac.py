"""
RBAC Redirection Stub for backwards compatibility.
"""
from core.rbac import (
    UserRole,
    Permission,
    ROLE_PERMISSIONS,
    AuthorizationService,
    AuthErrorResponse,
    role_validation_middleware
)
