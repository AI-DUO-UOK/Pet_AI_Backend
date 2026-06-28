-- =========================================================================
-- PetPULSE Complete Database Schema (Supabase Auth Architecture)
-- =========================================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. Users Table (1:1 with auth.users)
CREATE TABLE public.users (
  id uuid NOT NULL PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  email character varying NOT NULL,
  full_name character varying,
  role character varying CHECK (role IN ('owner', 'clinic', 'admin')),
  avatar_url character varying,
  phone_number character varying,
  updated_at timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Grant permissions
GRANT ALL ON ALL TABLES IN SCHEMA public TO postgres, anon, authenticated, service_role;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO postgres, anon, authenticated, service_role;
GRANT ALL ON ALL FUNCTIONS IN SCHEMA public TO postgres, anon, authenticated, service_role;

-- 2. Pet Owners Table
CREATE TABLE public.pet_owners (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL UNIQUE,
  full_name character varying NOT NULL,
  email character varying NOT NULL,
  phone character varying NOT NULL,
  address text,
  state character varying,
  zip_code character varying,
  country character varying,
  profile_image_url character varying,
  bio text,
  created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
  updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
  latitude double precision,
  longitude double precision,
  CONSTRAINT pet_owners_pkey PRIMARY KEY (id),
  CONSTRAINT pet_owners_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE
);

-- 3. Clinics Table
CREATE TABLE public.clinics (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL UNIQUE,
  clinic_name character varying NOT NULL,
  email character varying NOT NULL,
  phone character varying,
  address text NOT NULL,
  city character varying,
  state character varying,
  zip_code character varying,
  country character varying,
  clinic_logo_url character varying,
  registration_number character varying,
  license_number character varying,
  website character varying,
  opening_hours character varying,
  description text,
  is_verified boolean DEFAULT false,
  is_active boolean DEFAULT true,
  created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
  updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
  license_document_url character varying,
  latitude double precision,
  longitude double precision,
  CONSTRAINT clinics_pkey PRIMARY KEY (id),
  CONSTRAINT clinics_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE
);

-- 4. Pets Table
CREATE TABLE public.pets (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL,
  name character varying NOT NULL,
  type character varying NOT NULL,
  breed character varying NOT NULL,
  gender character varying,
  date_of_birth date NOT NULL,
  weight numeric,
  weight_unit character varying DEFAULT 'kg'::character varying,
  blood_type character varying,
  color_markings text,
  allergies text,
  medical_conditions text,
  microchip_id character varying,
  profile_image_url character varying,
  notes text,
  is_active boolean DEFAULT true,
  created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
  updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT pets_pkey PRIMARY KEY (id),
  CONSTRAINT pets_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE
);

-- 5. Vaccine Records Table (Files uploaded)
CREATE TABLE public.vaccine_records (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  pet_id uuid NOT NULL,
  file_name character varying NOT NULL,
  file_url character varying NOT NULL,
  file_type character varying,
  file_size bigint,
  upload_date date NOT NULL,
  description text,
  uploaded_by uuid,
  created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
  updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT vaccine_records_pkey PRIMARY KEY (id),
  CONSTRAINT vaccine_records_pet_id_fkey FOREIGN KEY (pet_id) REFERENCES public.pets(id) ON DELETE CASCADE,
  CONSTRAINT vaccine_records_uploaded_by_fkey FOREIGN KEY (uploaded_by) REFERENCES public.users(id) ON DELETE SET NULL
);

-- 6. Medical Records Table
CREATE TABLE public.medical_records (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  pet_id uuid NOT NULL,
  clinic_id uuid,
  record_type character varying,
  visit_date date,
  diagnosis text,
  treatment text,
  notes text,
  next_visit_date date,
  veterinarian_name character varying,
  file_url character varying,
  created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
  updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT medical_records_pkey PRIMARY KEY (id),
  CONSTRAINT medical_records_pet_id_fkey FOREIGN KEY (pet_id) REFERENCES public.pets(id) ON DELETE CASCADE,
  CONSTRAINT medical_records_clinic_id_fkey FOREIGN KEY (clinic_id) REFERENCES public.clinics(id) ON DELETE SET NULL
);

-- 7. Appointments Table
CREATE TABLE public.appointments (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  pet_id uuid NOT NULL,
  clinic_id uuid NOT NULL,
  owner_id uuid NOT NULL,
  appointment_date date NOT NULL,
  appointment_time time without time zone NOT NULL,
  reason character varying,
  status character varying DEFAULT 'scheduled'::character varying,
  notes text,
  reminder_sent boolean DEFAULT false,
  created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
  updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT appointments_pkey PRIMARY KEY (id),
  CONSTRAINT appointments_pet_id_fkey FOREIGN KEY (pet_id) REFERENCES public.pets(id) ON DELETE CASCADE,
  CONSTRAINT appointments_clinic_id_fkey FOREIGN KEY (clinic_id) REFERENCES public.clinics(id) ON DELETE CASCADE,
  CONSTRAINT appointments_owner_id_fkey FOREIGN KEY (owner_id) REFERENCES public.users(id) ON DELETE CASCADE
);

-- 8. Notifications Table
CREATE TABLE public.notifications (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  user_id uuid NOT NULL,
  user_role character varying CHECK (user_role IS NULL OR (user_role::text = ANY (ARRAY['owner'::character varying::text, 'clinic'::character varying::text, 'admin'::character varying::text]))),
  type character varying NOT NULL,
  title character varying NOT NULL,
  message text NOT NULL,
  entity_type character varying,
  entity_id uuid,
  link_url character varying,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  is_read boolean NOT NULL DEFAULT false,
  read_at timestamp with time zone,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT notifications_pkey PRIMARY KEY (id),
  CONSTRAINT notifications_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE
);

-- 9. Clinic Reviews Table
CREATE TABLE public.clinic_reviews (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  appointment_id uuid NOT NULL UNIQUE,
  clinic_id uuid NOT NULL,
  pet_id uuid NOT NULL,
  owner_id uuid NOT NULL,
  rating integer NOT NULL CHECK (rating >= 1 AND rating <= 5),
  treatment character varying NOT NULL,
  comment text,
  created_at timestamp with time zone NOT NULL DEFAULT now(),
  updated_at timestamp with time zone NOT NULL DEFAULT now(),
  CONSTRAINT clinic_reviews_pkey PRIMARY KEY (id),
  CONSTRAINT clinic_reviews_appointment_id_fkey FOREIGN KEY (appointment_id) REFERENCES public.appointments(id) ON DELETE CASCADE,
  CONSTRAINT clinic_reviews_clinic_id_fkey FOREIGN KEY (clinic_id) REFERENCES public.clinics(id) ON DELETE CASCADE,
  CONSTRAINT clinic_reviews_pet_id_fkey FOREIGN KEY (pet_id) REFERENCES public.pets(id) ON DELETE CASCADE,
  CONSTRAINT clinic_reviews_owner_id_fkey FOREIGN KEY (owner_id) REFERENCES public.users(id) ON DELETE CASCADE
);

-- =========================================================================
-- Triggers
-- =========================================================================

-- Trigger to automatically create a user row on signup
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger AS $$
BEGIN
  INSERT INTO public.users (id, email, full_name, role, avatar_url, phone_number)
  VALUES (
    new.id,
    new.email,
    COALESCE(new.raw_user_meta_data->>'full_name', new.raw_user_meta_data->>'name', ''),
    new.raw_user_meta_data->>'role',
    COALESCE(new.raw_user_meta_data->>'avatar_url', ''),
    COALESCE(new.raw_user_meta_data->>'phone', '')
  )
  ON CONFLICT (id) DO NOTHING;
  RETURN new;
EXCEPTION WHEN OTHERS THEN
  RETURN new;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- =========================================================================
-- Row Level Security (RLS) & Policies
-- =========================================================================

-- Enable RLS on all tables
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.pet_owners ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.clinics ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.pets ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.appointments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.clinic_reviews ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.vaccine_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.medical_records ENABLE ROW LEVEL SECURITY;

-- 1. Users Policies
CREATE POLICY "Allow users to read their own user record" ON public.users
  FOR SELECT TO authenticated USING (auth.uid() = id);

CREATE POLICY "Allow users to update their own user record" ON public.users
  FOR UPDATE TO authenticated USING (auth.uid() = id);

CREATE POLICY "Allow admins full access to users" ON public.users
  FOR ALL TO authenticated USING (
    (auth.jwt() -> 'user_metadata' ->> 'role') = 'admin'
  );

-- 2. Pet Owners Policies
CREATE POLICY "Allow owners to manage their own profile details" ON public.pet_owners
  FOR ALL TO authenticated USING (auth.uid() = user_id);

CREATE POLICY "Allow clinics to view pet owner details" ON public.pet_owners
  FOR SELECT TO authenticated USING (
    EXISTS (SELECT 1 FROM public.users WHERE id = auth.uid() AND role = 'clinic')
  );

CREATE POLICY "Allow admins full access to pet owners" ON public.pet_owners
  FOR ALL TO authenticated USING (
    EXISTS (SELECT 1 FROM public.users WHERE id = auth.uid() AND role = 'admin')
  );

-- 3. Clinics Policies
CREATE POLICY "Allow clinics to manage their own profile details" ON public.clinics
  FOR ALL TO authenticated USING (auth.uid() = user_id);

CREATE POLICY "Allow anyone to view verified clinics" ON public.clinics
  FOR SELECT USING (is_verified = true);

CREATE POLICY "Allow admins full access to clinics" ON public.clinics
  FOR ALL TO authenticated USING (
    EXISTS (SELECT 1 FROM public.users WHERE id = auth.uid() AND role = 'admin')
  );

-- 4. Pets Policies
CREATE POLICY "Allow owners to manage their own pets" ON public.pets
  FOR ALL TO authenticated USING (auth.uid() = user_id);

CREATE POLICY "Allow clinics to view pets" ON public.pets
  FOR SELECT TO authenticated USING (
    EXISTS (SELECT 1 FROM public.users WHERE id = auth.uid() AND role = 'clinic')
  );

CREATE POLICY "Allow admins full access to pets" ON public.pets
  FOR ALL TO authenticated USING (
    EXISTS (SELECT 1 FROM public.users WHERE id = auth.uid() AND role = 'admin')
  );

-- 5. Appointments Policies
CREATE POLICY "Allow owners to manage their own appointments" ON public.appointments
  FOR ALL TO authenticated USING (auth.uid() = owner_id);

CREATE POLICY "Allow clinics to view and update their own appointments" ON public.appointments
  FOR ALL TO authenticated USING (
    clinic_id IN (SELECT id FROM public.clinics WHERE user_id = auth.uid())
  );

CREATE POLICY "Allow admins full access to appointments" ON public.appointments
  FOR ALL TO authenticated USING (
    EXISTS (SELECT 1 FROM public.users WHERE id = auth.uid() AND role = 'admin')
  );

-- 6. Clinic Reviews Policies
CREATE POLICY "Allow owners to manage reviews for their appointments" ON public.clinic_reviews
  FOR ALL TO authenticated USING (auth.uid() = owner_id);

CREATE POLICY "Allow clinics to view reviews" ON public.clinic_reviews
  FOR SELECT TO authenticated USING (true);

-- 7. Notifications Policies
CREATE POLICY "Allow users to manage their own notifications" ON public.notifications
  FOR ALL TO authenticated USING (auth.uid() = user_id);

-- 8. Vaccine Records Policies
CREATE POLICY "Allow owners to view and upload vaccine records for their pets" ON public.vaccine_records
  FOR ALL TO authenticated USING (
    pet_id IN (SELECT id FROM public.pets WHERE user_id = auth.uid())
  );

CREATE POLICY "Allow clinics to view vaccine records" ON public.vaccine_records
  FOR SELECT TO authenticated USING (
    EXISTS (SELECT 1 FROM public.users WHERE id = auth.uid() AND role = 'clinic')
  );

-- 9. Medical Records Policies
CREATE POLICY "Allow owners to view medical records for their pets" ON public.medical_records
  FOR SELECT TO authenticated USING (
    pet_id IN (SELECT id FROM public.pets WHERE user_id = auth.uid())
  );

CREATE POLICY "Allow clinics to manage medical records" ON public.medical_records
  FOR ALL TO authenticated USING (
    clinic_id IN (SELECT id FROM public.clinics WHERE user_id = auth.uid())
  );

-- =========================================================================
-- Storage Buckets & Policies
-- =========================================================================

-- Create Buckets
INSERT INTO storage.buckets (id, name, public)
VALUES 
  ('pet-images', 'pet-images', true),
  ('clinic-logos', 'clinic-logos', true),
  ('medical-records', 'medical-records', false),
  ('vaccine-documents', 'vaccine-documents', false)
ON CONFLICT (id) DO NOTHING;

-- Pet Images (Public Read, Owner Write/Delete)
CREATE POLICY "Allow public read access to pet images" ON storage.objects FOR SELECT USING (bucket_id = 'pet-images');
CREATE POLICY "Allow owners to upload pet images" ON storage.objects FOR INSERT TO authenticated WITH CHECK (bucket_id = 'pet-images' AND (auth.uid()::text = (storage.foldername(name))[1]));
CREATE POLICY "Allow owners to manage their own pet images" ON storage.objects FOR ALL TO authenticated USING (bucket_id = 'pet-images' AND (auth.uid()::text = (storage.foldername(name))[1]));

-- Clinic Logos (Public Read, Clinic Write/Delete)
CREATE POLICY "Allow public read access to clinic logos" ON storage.objects FOR SELECT USING (bucket_id = 'clinic-logos');
CREATE POLICY "Allow clinics to upload logos" ON storage.objects FOR INSERT TO authenticated WITH CHECK (bucket_id = 'clinic-logos' AND (auth.uid()::text = (storage.foldername(name))[1]));
CREATE POLICY "Allow clinics to manage their own logos" ON storage.objects FOR ALL TO authenticated USING (bucket_id = 'clinic-logos' AND (auth.uid()::text = (storage.foldername(name))[1]));

-- Medical Records (Private Read/Write)
CREATE POLICY "Allow access to medical records" ON storage.objects FOR ALL TO authenticated USING (
  bucket_id = 'medical-records' AND (
    EXISTS (SELECT 1 FROM public.pets WHERE id::text = (storage.foldername(name))[1] AND user_id = auth.uid()) OR
    EXISTS (SELECT 1 FROM public.users WHERE id = auth.uid() AND role = 'clinic')
  )
);

-- Vaccine Documents (Private Read/Write)
CREATE POLICY "Allow access to vaccine documents" ON storage.objects FOR ALL TO authenticated USING (
  bucket_id = 'vaccine-documents' AND (
    EXISTS (SELECT 1 FROM public.pets WHERE id::text = (storage.foldername(name))[1] AND user_id = auth.uid()) OR
    EXISTS (SELECT 1 FROM public.users WHERE id = auth.uid() AND role = 'clinic')
  )
);