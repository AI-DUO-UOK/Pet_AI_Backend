-- Digital Vaccine Management System Schema
-- Run this in Supabase/PostgreSQL

-- 1. Vaccination Records - stores all vaccine entries
CREATE TABLE IF NOT EXISTS vaccination_records (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  pet_id UUID NOT NULL REFERENCES pets(id) ON DELETE CASCADE,
  vaccine_name VARCHAR(100) NOT NULL,
  vaccine_type VARCHAR(50),
  vaccination_date DATE NOT NULL,
  next_due_date DATE,
  batch_number VARCHAR(100),
  veterinarian_name VARCHAR(100),
  clinic_name VARCHAR(200),
  clinic_id UUID REFERENCES clinics(id) ON DELETE SET NULL,
  notes TEXT,
  source VARCHAR(20) NOT NULL DEFAULT 'manual' CHECK (source IN ('vlm_extracted', 'manual', 'vet_entry')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_vaccination_records_pet_id ON vaccination_records(pet_id);
CREATE INDEX IF NOT EXISTS idx_vaccination_records_next_due_date ON vaccination_records(next_due_date);

-- 2. Vaccine Documents - stores uploaded vaccine booklet images and extracted JSON
CREATE TABLE IF NOT EXISTS vaccine_documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  pet_id UUID NOT NULL REFERENCES pets(id) ON DELETE CASCADE,
  image_url TEXT NOT NULL,
  extracted_json JSONB,
  uploaded_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_vaccine_documents_pet_id ON vaccine_documents(pet_id);

-- 3. Notification Logs - prevents duplicate reminders
CREATE TABLE IF NOT EXISTS notification_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  vaccination_id UUID NOT NULL REFERENCES vaccination_records(id) ON DELETE CASCADE,
  notification_type VARCHAR(20) NOT NULL CHECK (notification_type IN ('UPCOMING_VACCINE', 'DUE_SOON', 'DUE_TODAY', 'OVERDUE')),
  sent_date DATE NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_notification_logs_vaccination_id ON notification_logs(vaccination_id);
CREATE INDEX IF NOT EXISTS idx_notification_logs_sent_date ON notification_logs(sent_date);

-- Prevent duplicate notification for same vaccine + type + date
CREATE UNIQUE INDEX IF NOT EXISTS idx_notification_logs_unique 
  ON notification_logs(vaccination_id, notification_type, sent_date);

-- Trigger to update updated_at
CREATE OR REPLACE FUNCTION set_vaccination_records_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_vaccination_records_updated_at ON vaccination_records;
CREATE TRIGGER trg_vaccination_records_updated_at
  BEFORE UPDATE ON vaccination_records
  FOR EACH ROW
  EXECUTE FUNCTION set_vaccination_records_updated_at();