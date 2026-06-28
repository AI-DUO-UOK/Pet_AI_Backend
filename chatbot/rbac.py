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
# FastAPI Decorators for Route Protection
# ============================================

def require_role(*required_roles: UserRole):
    """
    Decorator to protect FastAPI endpoints - requires specific role(s)
    
    Usage:
        @app.get("/api/clinic/patients")
        @require_role(UserRole.CLINIC, UserRole.ADMIN)
        async def get_clinic_patients(request: Request):
            ...
    
    Args:
        *required_roles: One or more acceptable roles
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get user role from request (set by middleware or dependency)
            request: Request = kwargs.get("request") or args[0] if args else None
            
            if not request:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Request object not found"
                )
            
            user_role = request.state.user_role if hasattr(request.state, "user_role") else None
            
            if not user_role:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not authenticated"
                )
            
            if not AuthorizationService.check_roles(user_role, list(required_roles)):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access denied. Required role(s): {', '.join([r.value for r in required_roles])}"
                )
            
            return await func(*args, **kwargs) if hasattr(func, "__await__") else func(*args, **kwargs)
        
        return wrapper
    return decorator


def require_permission(permission: Permission):
    """
    Decorator to protect FastAPI endpoints - requires specific permission
    
    Usage:
        @app.post("/api/pets")
        @require_permission(Permission.CREATE_PET)
        async def create_pet(request: Request, data: PetData):
            ...
    
    Args:
        permission: Required permission
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request: Request = kwargs.get("request") or args[0] if args else None
            
            if not request:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Request object not found"
                )
            
            user_role = request.state.user_role if hasattr(request.state, "user_role") else None
            
            if not user_role:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not authenticated"
                )
            
            if not AuthorizationService.has_permission(user_role, permission):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access denied. Permission required: {permission.value}"
                )
            
            return await func(*args, **kwargs) if hasattr(func, "__await__") else func(*args, **kwargs)
        
        return wrapper
    return decorator


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
        # TODO: Decode JWT token and extract user_id, role
        # For now, this is a placeholder
        # In production, decode JWT token here
        pass
    
    # Set default values
    request.state.user_id = None
    request.state.user_role = None
    request.state.is_authenticated = False
    
    response = await call_next(request)
    return response


# ============================================
# Usage Examples
# ============================================

"""
EXAMPLE 1: Check role in a service function
----------------------------------------------

from chatbot.rbac import AuthorizationService, UserRole, Permission

def create_medical_record(user_id: str, user_role: str, record_data: dict):
    # Check if user has permission
    if not AuthorizationService.has_permission(user_role, Permission.CREATE_MEDICAL_RECORD):
        return {
            "success": False,
            "error": "Access denied",
            "message": "Only clinics can create medical records"
        }
    
    # Proceed with creation
    return supabase.table("medical_records").insert(record_data).execute()


EXAMPLE 2: Protect FastAPI endpoints
----------------------------------------------

from fastapi import FastAPI, Request
from chatbot.rbac import require_role, require_permission, UserRole, Permission

app = FastAPI()

@app.get("/api/clinic/patients")
@require_role(UserRole.CLINIC, UserRole.ADMIN)
async def get_clinic_patients(request: Request):
    # Only clinic staff and admin can access
    clinic_id = request.state.clinic_id
    return get_patients_for_clinic(clinic_id)


@app.post("/api/medical-records")
@require_permission(Permission.CREATE_MEDICAL_RECORD)
async def create_medical_record(request: Request, data: dict):
    # Only users with CREATE_MEDICAL_RECORD permission
    user_id = request.state.user_id
    return create_record(user_id, data)


EXAMPLE 3: Login with role-based response
----------------------------------------------

def login_with_role_check(email: str, password: str):
    result = AuthService.login(email, password)
    
    if not result["success"]:
        return result
    
    # Get user permissions
    role = result["role"]
    permissions = AuthorizationService.get_user_permissions(role)
    
    return {
        **result,
        "permissions": [p.value for p in permissions],
        "role_description": {
            "owner": "Pet Owner",
            "clinic": "Veterinary Clinic",
            "admin": "System Administrator"
        }.get(role)
    }


EXAMPLE 4: Role-based routes
----------------------------------------------

# Routes accessible only by pet owners
def get_owner_routes():
    return [
        "GET /api/my-pets",
        "POST /api/pets",
        "GET /api/appointments",
        "POST /api/appointments",
        "POST /api/vaccine-records"
    ]

# Routes accessible only by clinics
def get_clinic_routes():
    return [
        "GET /api/clinic/patients",
        "POST /api/medical-records",
        "GET /api/clinic/appointments",
        "PUT /api/clinic/profile"
    ]

# Routes accessible by admins
def get_admin_routes():
    return [
        "GET /api/admin/users",
        "GET /api/admin/clinics",
        "GET /api/admin/stats",
        "DELETE /api/admin/users/{id}"
    ]
"""
