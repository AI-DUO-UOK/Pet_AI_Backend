"""
Role-Based Access Control (RBAC) for Pet AI Backend
Handles authorization, permissions, and role-based endpoint protection
"""

from functools import wraps
from typing import Dict, List, Optional, Callable
from fastapi import HTTPException, Request, status
from enum import Enum


class UserRole(str, Enum):
    """User roles in the system"""
    OWNER = "owner"  # Pet owner
    CLINIC = "clinic"  # Veterinary clinic
    ADMIN = "admin"  # System admin (future)


class Permission(str, Enum):
    """Permissions in the system"""
    # Pet Owner Permissions
    VIEW_OWN_PETS = "view_own_pets"
    CREATE_PET = "create_pet"
    EDIT_OWN_PET = "edit_own_pet"
    DELETE_OWN_PET = "delete_own_pet"
    VIEW_OWN_MEDICAL_RECORDS = "view_own_medical_records"
    CREATE_APPOINTMENT = "create_appointment"
    VIEW_OWN_APPOINTMENTS = "view_own_appointments"
    UPLOAD_VACCINE_RECORDS = "upload_vaccine_records"
    
    # Clinic Permissions
    VIEW_CLINIC_PATIENTS = "view_clinic_patients"
    CREATE_MEDICAL_RECORD = "create_medical_record"
    VIEW_CLINIC_APPOINTMENTS = "view_clinic_appointments"
    MANAGE_CLINIC_PROFILE = "manage_clinic_profile"
    
    # Admin Permissions
    VIEW_ALL_USERS = "view_all_users"
    MANAGE_USERS = "manage_users"
    VIEW_SYSTEM_STATS = "view_system_stats"
    MANAGE_CLINICS = "manage_clinics"


# Role to Permissions Mapping
ROLE_PERMISSIONS: Dict[UserRole, List[Permission]] = {
    UserRole.OWNER: [
        Permission.VIEW_OWN_PETS,
        Permission.CREATE_PET,
        Permission.EDIT_OWN_PET,
        Permission.DELETE_OWN_PET,
        Permission.VIEW_OWN_MEDICAL_RECORDS,
        Permission.CREATE_APPOINTMENT,
        Permission.VIEW_OWN_APPOINTMENTS,
        Permission.UPLOAD_VACCINE_RECORDS,
    ],
    UserRole.CLINIC: [
        Permission.VIEW_CLINIC_PATIENTS,
        Permission.CREATE_MEDICAL_RECORD,
        Permission.VIEW_CLINIC_APPOINTMENTS,
        Permission.MANAGE_CLINIC_PROFILE,
    ],
    UserRole.ADMIN: [
        Permission.VIEW_ALL_USERS,
        Permission.MANAGE_USERS,
        Permission.VIEW_SYSTEM_STATS,
        Permission.MANAGE_CLINICS,
        Permission.VIEW_OWN_PETS,
        Permission.VIEW_CLINIC_APPOINTMENTS,
    ],
}


class AuthorizationService:
    """Service for authorization and permission checks"""

    @staticmethod
    def get_user_permissions(role: str) -> List[Permission]:
        """
        Get all permissions for a user role
        
        Args:
            role: User role (owner, clinic, admin)
        
        Returns:
            List of permissions
        """
        try:
            user_role = UserRole(role.lower())
            return ROLE_PERMISSIONS.get(user_role, [])
        except ValueError:
            return []

    @staticmethod
    def has_permission(role: str, permission: Permission) -> bool:
        """
        Check if user role has specific permission
        
        Args:
            role: User role
            permission: Permission to check
        
        Returns:
            True if user has permission, False otherwise
        """
        permissions = AuthorizationService.get_user_permissions(role)
        return permission in permissions

    @staticmethod
    def check_role(user_role: str, required_role: UserRole) -> bool:
        """
        Check if user has required role
        
        Args:
            user_role: User's actual role
            required_role: Required role
        
        Returns:
            True if user has required role, False otherwise
        """
        return user_role.lower() == required_role.value

    @staticmethod
    def check_roles(user_role: str, required_roles: List[UserRole]) -> bool:
        """
        Check if user has one of multiple required roles
        
        Args:
            user_role: User's actual role
            required_roles: List of acceptable roles
        
        Returns:
            True if user has one of required roles, False otherwise
        """
        user_role_lower = user_role.lower()
        return any(user_role_lower == role.value for role in required_roles)





# ============================================
# Response Templates for Authorization Errors
# ============================================

class AuthErrorResponse:
    """Standard error responses for authentication/authorization"""

    @staticmethod
    def unauthorized() -> Dict:
        return {
            "success": False,
            "error": "Unauthorized",
            "message": "User is not authenticated. Please login.",
            "status_code": 401
        }

    @staticmethod
    def forbidden(required_role: str = None, permission: str = None) -> Dict:
        message = "Access denied."
        
        if required_role:
            message += f" Required role: {required_role}"
        elif permission:
            message += f" Required permission: {permission}"
        else:
            message += " You don't have permission to access this resource."
        
        return {
            "success": False,
            "error": "Forbidden",
            "message": message,
            "status_code": 403
        }

    @staticmethod
    def inactive_account() -> Dict:
        return {
            "success": False,
            "error": "Account Inactive",
            "message": "Your account is inactive. Please contact support.",
            "status_code": 403
        }


# ============================================
# Middleware for Role Validation
# ============================================

async def role_validation_middleware(request: Request, call_next):
    """
    Middleware to validate user role and attach to request state
    
    Usage in FastAPI main.py:
        app.middleware("http")(role_validation_middleware)
    """
    # Extract user info from request (usually from JWT token in Authorization header)
    auth_header = request.headers.get("Authorization")
    
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
        # In production, decode JWT token here
        pass
    
    # Set default values
    request.state.user_id = None
    request.state.user_role = None
    request.state.is_authenticated = False
    
    response = await call_next(request)
    return response
