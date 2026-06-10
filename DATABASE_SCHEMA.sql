-- ============================================
-- PET AI DATABASE SCHEMA
-- Supabase PostgreSQL Setup
-- ============================================

-- Step 1: Create auth_users table (Pet Owners & Clinic Staff)
-- ============================================

CREATE TABLE
IF NOT EXISTS auth_users
(
  id UUID PRIMARY KEY DEFAULT gen_random_uuid
(),
  email VARCHAR
(255) UNIQUE NOT NULL,
  password_hash VARCHAR
(255) NOT NULL,
  first_name VARCHAR
(100),
  last_name VARCHAR
(100),
  phone VARCHAR
(20),
  role VARCHAR
(50) NOT NULL DEFAULT 'owner', -- 'owner' or 'clinic'
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT email_not_empty CHECK
(email != ''),
  CONSTRAINT valid_role CHECK
(role IN
('owner', 'clinic'))
);

-- Create index on email for faster lookups
CREATE INDEX
IF NOT EXISTS idx_auth_users_email ON auth_users
(email);
CREATE INDEX
IF NOT EXISTS idx_auth_users_role ON auth_users
(role);

-- ============================================
-- Step 2: Create pet_owners table
-- ============================================

CREATE TABLE
IF NOT EXISTS pet_owners
(
  id UUID PRIMARY KEY DEFAULT gen_random_uuid
(),
  user_id UUID UNIQUE NOT NULL REFERENCES auth_users
(id) ON
DELETE CASCADE,
  full_name VARCHAR(255)
NOT NULL,
  email VARCHAR
(255) NOT NULL,
  phone VARCHAR
(20),
  address TEXT,
  city VARCHAR
(100),
  state VARCHAR
(100),
  zip_code VARCHAR
(20),
  country VARCHAR
(100),
  profile_image_url VARCHAR
(500),
  bio TEXT,
  emergency_contact_name VARCHAR
(255),
  emergency_contact_phone VARCHAR
(20),
  latitude DOUBLE PRECISION,
  longitude DOUBLE PRECISION,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX
IF NOT EXISTS idx_pet_owners_user_id ON pet_owners
(user_id);
CREATE INDEX
IF NOT EXISTS idx_pet_owners_email ON pet_owners
(email);

-- ============================================
-- Step 3: Create clinics table
-- ============================================

CREATE TABLE
IF NOT EXISTS clinics
(
  id UUID PRIMARY KEY DEFAULT gen_random_uuid
(),
  user_id UUID UNIQUE NOT NULL REFERENCES auth_users
(id) ON
DELETE CASCADE,
  clinic_name VARCHAR(255)
NOT NULL,
  email VARCHAR
(255) NOT NULL,
  phone VARCHAR
(20),
  address TEXT NOT NULL,
  city VARCHAR
(100),
  state VARCHAR
(100),
  zip_code VARCHAR
(20),
  country VARCHAR
(100),
  clinic_logo_url VARCHAR(500),
  license_document_url VARCHAR(500),
  registration_number VARCHAR(100),
  license_number VARCHAR(100),
  website VARCHAR(500),
  opening_hours VARCHAR(500), -- JSON format: {"Monday": "9AM-5PM", ...}
  description TEXT,
  is_verified BOOLEAN DEFAULT false,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX
IF NOT EXISTS idx_clinics_user_id ON clinics
(user_id);
CREATE INDEX
IF NOT EXISTS idx_clinics_email ON clinics
(email);
CREATE INDEX
IF NOT EXISTS idx_clinics_city ON clinics
(city);

-- ============================================
-- Step 4: Create pets table
-- ============================================

CREATE TABLE
IF NOT EXISTS pets
(
  id UUID PRIMARY KEY DEFAULT gen_random_uuid
(),
  user_id UUID NOT NULL REFERENCES pet_owners
(user_id) ON
DELETE CASCADE,
  name VARCHAR(100)
NOT NULL,
  type VARCHAR
(50) NOT NULL, -- 'dog' or 'cat'
  breed VARCHAR
(100) NOT NULL,
  gender VARCHAR
(20), -- 'Male' or 'Female'
  date_of_birth DATE NOT NULL,
  weight DECIMAL
(5, 2), -- in kg or lbs
  weight_unit VARCHAR
(10) DEFAULT 'kg', -- 'kg' or 'lbs'
  blood_type VARCHAR
(50), -- e.g., "Type A", "Type B"
  color_markings TEXT, -- Physical appearance details
  allergies TEXT, -- Comma-separated or newline-separated
  medical_conditions TEXT, -- Health issues
  microchip_id VARCHAR
(100),
  profile_image_url VARCHAR
(500),
  notes TEXT,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX
IF NOT EXISTS idx_pets_user_id ON pets
(user_id);
CREATE INDEX
IF NOT EXISTS idx_pets_name ON pets
(name);
CREATE INDEX
IF NOT EXISTS idx_pets_type ON pets
(type);

-- ============================================
-- Step 5: Create vaccine_records table
-- ============================================

CREATE TABLE
IF NOT EXISTS vaccine_records
(
  id UUID PRIMARY KEY DEFAULT gen_random_uuid
(),
  pet_id UUID NOT NULL REFERENCES pets
(id) ON
DELETE CASCADE,
  file_name VARCHAR(255)
NOT NULL,
  file_url VARCHAR
(500) NOT NULL, -- Supabase storage URL
  file_type VARCHAR
(50), -- 'image' or 'pdf'
  file_size BIGINT, -- in bytes
  upload_date DATE NOT NULL,
  description TEXT,
  uploaded_by UUID REFERENCES auth_users
(id),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX
IF NOT EXISTS idx_vaccine_records_pet_id ON vaccine_records
(pet_id);
CREATE INDEX
IF NOT EXISTS idx_vaccine_records_upload_date ON vaccine_records
(upload_date);

-- ============================================
-- Step 6: Create medical_records table
-- ============================================

CREATE TABLE
IF NOT EXISTS medical_records
(
  id UUID PRIMARY KEY DEFAULT gen_random_uuid
(),
  pet_id UUID NOT NULL REFERENCES pets
(id) ON
DELETE CASCADE,
  clinic_id UUID
REFERENCES clinics
(id),
  record_type VARCHAR
(100), -- 'checkup', 'vaccination', 'surgery', 'test', etc.
  visit_date DATE,
  diagnosis TEXT,
  treatment TEXT,
  notes TEXT,
  next_visit_date DATE,
  veterinarian_name VARCHAR
(255),
  file_url VARCHAR
(500), -- If document uploaded
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX
IF NOT EXISTS idx_medical_records_pet_id ON medical_records
(pet_id);
CREATE INDEX
IF NOT EXISTS idx_medical_records_clinic_id ON medical_records
(clinic_id);
CREATE INDEX
IF NOT EXISTS idx_medical_records_visit_date ON medical_records
(visit_date);

-- ============================================
-- Step 7: Create appointments table
-- ============================================

CREATE TABLE
IF NOT EXISTS appointments
(
  id UUID PRIMARY KEY DEFAULT gen_random_uuid
(),
  pet_id UUID NOT NULL REFERENCES pets
(id) ON
DELETE CASCADE,
  clinic_id UUID
NOT NULL REFERENCES clinics
(id) ON
DELETE CASCADE,
  owner_id UUID
NOT NULL REFERENCES pet_owners
(user_id) ON
DELETE CASCADE,
  appointment_date DATE
NOT NULL,
  appointment_time TIME NOT NULL,
  reason VARCHAR
(255),
  status VARCHAR
(50) DEFAULT 'scheduled', -- 'scheduled', 'completed', 'cancelled'
  notes TEXT,
  reminder_sent BOOLEAN DEFAULT false,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX
IF NOT EXISTS idx_appointments_pet_id ON appointments
(pet_id);
CREATE INDEX
IF NOT EXISTS idx_appointments_clinic_id ON appointments
(clinic_id);
CREATE INDEX
IF NOT EXISTS idx_appointments_owner_id ON appointments
(owner_id);
CREATE INDEX
IF NOT EXISTS idx_appointments_date ON appointments
(appointment_date);

-- ============================================
-- Step 8: Enable Row Level Security (RLS)
-- ============================================

-- Enable RLS on all tables
ALTER TABLE auth_users ENABLE ROW LEVEL SECURITY;
ALTER TABLE pet_owners ENABLE ROW LEVEL SECURITY;
ALTER TABLE clinics ENABLE ROW LEVEL SECURITY;
ALTER TABLE pets ENABLE ROW LEVEL SECURITY;
ALTER TABLE vaccine_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE medical_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE appointments ENABLE ROW LEVEL SECURITY;

-- ============================================
-- RLS Policies for Pet Owners
-- ============================================

-- Pet Owners can view/edit their own profile
CREATE POLICY pet_owner_own_profile ON pet_owners
  FOR ALL
  USING
(user_id = auth.uid
());

-- Pet Owners can view/create/edit/delete their own pets
CREATE POLICY pet_owner_own_pets ON pets
  FOR ALL
  USING
(user_id = auth.uid
());

-- Pet Owners can view/create vaccine records for their pets
CREATE POLICY pet_owner_vaccine_records ON vaccine_records
  FOR ALL
  USING
(
    pet_id IN
(
      SELECT id
FROM pets
WHERE user_id = auth.uid()
    )
);

-- Pet Owners can view medical records for their pets
CREATE POLICY pet_owner_medical_records ON medical_records
  FOR
SELECT
  USING (
    pet_id IN (
      SELECT id
  FROM pets
  WHERE user_id = auth.uid()
    )
  );

-- ============================================
-- RLS Policies for Clinics
-- ============================================

-- Clinics can view/edit their own profile
CREATE POLICY clinic_own_profile ON clinics
  FOR ALL
  USING
(user_id = auth.uid
());

-- Clinics can create medical records
CREATE POLICY clinic_medical_records ON medical_records
  FOR ALL
  USING
(clinic_id IN
(SELECT id
FROM clinics
WHERE user_id = auth.uid())
);

-- Clinics can view appointments for their clinic
CREATE POLICY clinic_appointments ON appointments
  FOR ALL
  USING
(clinic_id IN
(SELECT id
FROM clinics
WHERE user_id = auth.uid())
);

-- ============================================
-- Public Policies (For Login/Signup)
-- ============================================

-- Anyone can insert new users (signup)
CREATE POLICY auth_users_signup ON auth_users
  FOR
INSERT
  WITH CHECK
  (true)
;

-- Users can view their own auth record
CREATE POLICY auth_users_view_own ON auth_users
  FOR
SELECT
  USING (id = auth.uid());

-- ============================================
-- Summary of Tables Created:
-- ============================================
-- 1. auth_users - User authentication (pet owners & clinics)
-- 2. pet_owners - Pet owner profiles
-- 3. clinics - Clinic/veterinary profiles
-- 4. pets - Pet information with health details
-- 5. vaccine_records - Uploaded vaccine documents
-- 6. medical_records - Medical visit records
-- 7. appointments - Appointment scheduling
