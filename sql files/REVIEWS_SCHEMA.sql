-- Real clinic reviews submitted after completed channel appointments.
-- Run this in Supabase/PostgreSQL before enabling the review UI.

CREATE TABLE
IF NOT EXISTS clinic_reviews
(
  id UUID PRIMARY KEY DEFAULT gen_random_uuid
(),
  appointment_id UUID NOT NULL UNIQUE REFERENCES appointments
(id) ON
DELETE CASCADE,
  clinic_id UUID
NOT NULL REFERENCES clinics
(id) ON
DELETE CASCADE,
  pet_id UUID
NOT NULL REFERENCES pets
(id) ON
DELETE CASCADE,
  owner_id UUID
NOT NULL REFERENCES pet_owners
(user_id) ON
DELETE CASCADE,
  rating INTEGER
NOT NULL CHECK
(rating BETWEEN 1 AND 5),
  treatment VARCHAR
(100) NOT NULL,
  comment TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW
(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW
()
);

CREATE INDEX
IF NOT EXISTS idx_clinic_reviews_clinic_id ON clinic_reviews
(clinic_id);
CREATE INDEX
IF NOT EXISTS idx_clinic_reviews_owner_id ON clinic_reviews
(owner_id);
CREATE INDEX
IF NOT EXISTS idx_clinic_reviews_pet_id ON clinic_reviews
(pet_id);
CREATE INDEX
IF NOT EXISTS idx_clinic_reviews_created_at ON clinic_reviews
(created_at DESC);

CREATE OR REPLACE FUNCTION set_clinic_reviews_updated_at
()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW
();
RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_clinic_reviews_updated_at
ON clinic_reviews;
CREATE TRIGGER trg_clinic_reviews_updated_at
BEFORE
UPDATE ON clinic_reviews
FOR EACH ROW
EXECUTE FUNCTION set_clinic_reviews_updated_at
();