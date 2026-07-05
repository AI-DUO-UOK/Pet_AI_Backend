from fastapi import APIRouter, Depends, HTTPException, Request
from typing import Optional
import logging
from core.dependencies import require_role, get_clinic_service
from services.clinic_service import ClinicService

logger = logging.getLogger(__name__)

# Protect the entire router with require_role("admin")
router = APIRouter(prefix="/admin", tags=["Admin Operations"], dependencies=[require_role("admin")])

@router.get("/clinics/pending")
async def get_pending_clinics(clinic_service: ClinicService = Depends(get_clinic_service)):
    """List all pending clinics (unverified and not rejected)"""
    logger.info("Admin: Fetching pending clinics")
    result = clinic_service.get_pending_clinics()
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result

@router.get("/clinics")
async def get_all_clinics(clinic_service: ClinicService = Depends(get_clinic_service)):
    """List all clinics with their derived verification status"""
    logger.info("Admin: Fetching all clinics")
    
    from core.supabase_config import supabase
    try:
        resp = supabase.table("clinics").select("*").order("created_at", desc=True).execute()
        # We can call the helper parser on the injected service
        clinics = [clinic_service._parse_clinic_status(c) for c in (resp.data or [])]
        return {"success": True, "clinics": clinics, "count": len(clinics)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/stats")
async def get_admin_stats(clinic_service: ClinicService = Depends(get_clinic_service)):
    """Return admin dashboard counts and recent clinic activity"""
    logger.info("Admin: Fetching dashboard stats")
    
    from core.supabase_config import supabase
    try:
        all_resp = supabase.table("clinics").select("id", "is_verified", "clinic_name", "created_at", "description").execute()
        clinics = [clinic_service._parse_clinic_status(c) for c in (all_resp.data or [])]
        
        total_clinics = len(clinics)
        approved_clinics = sum(1 for c in clinics if c.get("verification_status") == "approved")
        pending_clinics = sum(1 for c in clinics if c.get("verification_status") == "pending")
        rejected_clinics = sum(1 for c in clinics if c.get("verification_status") == "rejected")

        recent = sorted(clinics, key=lambda c: c.get("created_at") or "", reverse=True)[:3]
        recent_verifications = []
        for clinic in recent:
            recent_verifications.append({
                "clinic": clinic.get("clinic_name", "Unknown Clinic"),
                "action": clinic.get("verification_status", "pending").title(),
                "time": clinic.get("created_at"),
                "badge": (
                    "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400"
                    if clinic.get("verification_status") == "approved"
                    else "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400"
                    if clinic.get("verification_status") == "rejected"
                    else "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400"
                ),
            })

        return {
            "success": True,
            "stats": {
                "total_clinics": total_clinics,
                "pending_verifications": pending_clinics,
                "approved_clinics": approved_clinics,
                "rejected": rejected_clinics,
            },
            "recent_verifications": recent_verifications,
        }
    except Exception as e:
        logger.error(f"Error fetching admin stats: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/clinics/{clinic_id}/approve")
async def approve_clinic(
    clinic_id: str,
    clinic_service: ClinicService = Depends(get_clinic_service)
):
    """Approve a clinic (verify it and activate its login profile)"""
    logger.info(f"Admin: Approving clinic {clinic_id}")
    result = clinic_service.approve_clinic(clinic_id=clinic_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result

@router.post("/clinics/{clinic_id}/reject")
async def reject_clinic(
    clinic_id: str,
    request: Request,
    clinic_service: ClinicService = Depends(get_clinic_service)
):
    """Reject a clinic registration with an optional reason"""
    logger.info(f"Admin: Rejecting clinic {clinic_id}")
    
    # Read optional reason from request body
    try:
        body = await request.json()
    except Exception:
        body = {}
    reason = (body or {}).get("reason")

    result = clinic_service.reject_clinic(clinic_id=clinic_id, reason=reason)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result
