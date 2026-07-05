"""
Supabase Configuration for Pet AI Backend
"""
import os
import logging
from typing import Optional
from typing import Iterable

logger = logging.getLogger(__name__)

from dotenv import load_dotenv
load_dotenv()

# Get credentials from environment variables
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")  # Use anon key for client-side, service key for server-side
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")

# Initialize Supabase client lazily to allow startup without credentials
supabase: Optional[object] = None

try:
    if SUPABASE_URL and SUPABASE_SERVICE_KEY:
        from supabase import create_client, Client
        # Use SERVICE_KEY for server-side operations to bypass RLS policies
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        logger.info("Supabase client initialized successfully with service key")
    else:
        logger.warning("SUPABASE_URL or SUPABASE_SERVICE_KEY not set - Supabase features disabled")
except ImportError:
    logger.warning("supabase package not installed - install with: pip install supabase")
except Exception as e:
    logger.error(f"Error initializing Supabase client: {str(e)}")

def get_supabase_client() -> Optional[object]:
    """Get Supabase client instance"""
    if not supabase:
        raise ValueError(
            "Supabase not initialized. Set SUPABASE_URL and SUPABASE_SERVICE_KEY environment variables"
        )
    return supabase

# Database helper functions
class SupabaseDB:
    """Helper class for Supabase database operations"""
    
    @staticmethod
    def _check_client():
        """Check if Supabase client is initialized"""
        if not supabase:
            raise RuntimeError(
                "Supabase client not initialized. "
                "Please set SUPABASE_URL and SUPABASE_KEY environment variables."
            )
    
    @staticmethod
    def insert_user(user_data: dict):
        """Insert user into auth_users table"""
        SupabaseDB._check_client()
        response = supabase.table("auth_users").insert(user_data).execute()
        return response.data
    
    @staticmethod
    def get_user(user_id: str):
        """Get user by ID"""
        SupabaseDB._check_client()
        response = supabase.table("auth_users").select("*").eq("id", user_id).execute()
        return response.data[0] if response.data else None
    
    @staticmethod
    def insert_pet(pet_data: dict):
        """Insert pet into pets table"""
        SupabaseDB._check_client()
        response = supabase.table("pets").insert(pet_data).execute()
        return response.data
    
    @staticmethod
    def get_user_pets(user_id: str):
        """Get all pets for a user"""
        SupabaseDB._check_client()
        response = supabase.table("pets").select("*").eq("user_id", user_id).execute()
        return response.data
    
    @staticmethod
    def insert_medical_record(record_data: dict):
        """Insert medical record into medical_records table"""
        SupabaseDB._check_client()
        response = supabase.table("medical_records").insert(record_data).execute()
        return response.data
    
    @staticmethod
    def get_pet_medical_records(pet_id: str):
        """Get all medical records for a pet"""
        SupabaseDB._check_client()
        response = supabase.table("medical_records").select("*").eq("pet_id", pet_id).execute()
        return response.data
    
    @staticmethod
    def upload_file(bucket_name: str, file_path: str, file_data):
        """Upload file to Supabase storage"""
        SupabaseDB._check_client()
        response = supabase.storage.from_(bucket_name).upload(file_path, file_data)
        return response

class SupabaseStorage:
    """Helper class for Supabase storage operations"""

    @staticmethod
    def ensure_bucket(bucket_name: str, *, public: bool = True, allowed_mime_types: Optional[Iterable[str]] = None):
        """Create the bucket if it does not already exist."""
        SupabaseDB._check_client()

        existing_buckets = supabase.storage.list_buckets()
        if any(getattr(bucket, "name", None) == bucket_name for bucket in (existing_buckets or [])):
            return
 
        options = {"public": public}
        if allowed_mime_types:
            options["allowed_mime_types"] = list(allowed_mime_types)

        supabase.storage.create_bucket(bucket_name, options=options)
    
    @staticmethod
    def upload_pet_image(user_id: str, pet_id: str, file_data, filename: str):
        """Upload pet image to storage"""
        SupabaseStorage.ensure_bucket("pet-images", public=True, allowed_mime_types=["image/*"])
        file_path = f"{user_id}/{pet_id}/{filename}"
        supabase.storage.from_("pet-images").upload(
            file=file_data,
            path=file_path,
            file_options={"content-type": "image/jpeg", "upsert": "false"},
        )
        return file_path

    @staticmethod
    def upload_clinic_image(user_id: str, file_data, filename: str, content_type: str = "image/jpeg"):
        """Upload clinic image to storage"""
        SupabaseStorage.ensure_bucket("clinic-images", public=True, allowed_mime_types=["image/*"])
        file_path = f"{user_id}/{filename}"
        supabase.storage.from_("clinic-images").upload(
            file=file_data,
            path=file_path,
            file_options={"content-type": content_type or "image/jpeg", "upsert": "false"},
        )
        return file_path

    @staticmethod
    def upload_clinic_document(user_id: str, file_data, filename: str, content_type: str = "application/pdf"):
        """Upload clinic verification document to storage"""
        SupabaseStorage.ensure_bucket("clinic-documents", public=True, allowed_mime_types=["image/*", "application/pdf"])
        file_path = f"{user_id}/{filename}"
        supabase.storage.from_("clinic-documents").upload(
            file=file_data,
            path=file_path,
            file_options={"content-type": content_type or "application/pdf", "upsert": "false"},
        )
        return file_path

    @staticmethod
    def upload_user_avatar(user_id: str, file_data, filename: str, content_type: str = "image/jpeg"):
        """Upload user avatar to storage"""
        SupabaseStorage.ensure_bucket("user-avatars", public=True, allowed_mime_types=["image/*"])
        file_path = f"{user_id}/{filename}"
        supabase.storage.from_("user-avatars").upload(
            file=file_data,
            path=file_path,
            file_options={"content-type": content_type or "image/jpeg", "upsert": "false"},
        )
        return file_path

    @staticmethod
    def list_clinic_images(user_id: str):
        """List public URLs for clinic images stored for a user."""
        SupabaseDB._check_client()
        SupabaseStorage.ensure_bucket("clinic-images", public=True, allowed_mime_types=["image/*"])

        try:
            files = supabase.storage.from_("clinic-images").list(user_id)
        except Exception:
            files = []

        image_urls = []
        for file_entry in files or []:
            file_name = getattr(file_entry, "name", None)
            if not file_name and isinstance(file_entry, dict):
                file_name = file_entry.get("name")
            if not file_name:
                continue
            # normalize public url value to string
            url = supabase.storage.from_("clinic-images").get_public_url(f"{user_id}/{file_name}")
            # supabase client may return a dict/object with a public URL field
            if isinstance(url, dict):
                image_urls.append(url.get('publicURL') or url.get('publicUrl') or url.get('public_url') or '')
            else:
                # handle objects with attributes or plain strings
                try:
                    u = getattr(url, 'publicURL', None) or getattr(url, 'publicUrl', None) or getattr(url, 'public_url', None)
                except Exception:
                    u = None
                image_urls.append(u or (url if isinstance(url, str) else ''))

        return image_urls
    
    @staticmethod
    def get_public_url(bucket_name: str, file_path: str):
        """Get public URL for a file"""
        result = supabase.storage.from_(bucket_name).get_public_url(file_path)
        if isinstance(result, dict):
            return result.get('publicURL') or result.get('publicUrl') or result.get('public_url') or ''
        # object with attribute
        try:
            attr = getattr(result, 'publicURL', None) or getattr(result, 'publicUrl', None) or getattr(result, 'public_url', None)
            if attr:
                return attr
        except Exception:
            pass
        return result if isinstance(result, str) else ''
