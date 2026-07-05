-- =========================================================================
-- PetPULSE Database Migration v4 - Clinic Rejection Columns
-- =========================================================================

ALTER TABLE public.clinics 
ADD COLUMN IF NOT EXISTS rejection_reason text,
ADD COLUMN IF NOT EXISTS rejected_at timestamp without time zone;
