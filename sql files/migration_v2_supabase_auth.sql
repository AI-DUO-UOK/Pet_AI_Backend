-- =========================================================================
-- PetPULSE Authentication Refactor Migration SQL
-- =========================================================================

BEGIN;

-- 1. Create profiles table
CREATE TABLE IF NOT EXISTS public.profiles (
  id uuid NOT NULL PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  role character varying NOT NULL CHECK (role IN ('owner', 'clinic', 'admin')),
  phone character varying,
  is_active boolean DEFAULT true,
  created_at timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL,
  updated_at timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Migrate existing users from public.auth_users to public.profiles if any exist
-- Note: This assumes auth.users already contains the users. If migrating from custom auth,
-- those users should be created in auth.users first.
-- INSERT INTO public.profiles (id, role, phone, is_active, created_at, updated_at)
-- SELECT id, role, phone, is_active, created_at, updated_at FROM public.auth_users
-- ON CONFLICT (id) DO NOTHING;

-- 2. Update Foreign Keys to point to public.profiles
-- Update pet_owners
ALTER TABLE public.pet_owners DROP CONSTRAINT IF EXISTS pet_owners_user_id_fkey;
ALTER TABLE public.pet_owners ADD CONSTRAINT pet_owners_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.profiles(id) ON DELETE CASCADE;

-- Update clinics
ALTER TABLE public.clinics DROP CONSTRAINT IF EXISTS clinics_user_id_fkey;
ALTER TABLE public.clinics ADD CONSTRAINT clinics_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.profiles(id) ON DELETE CASCADE;

-- Update pets
ALTER TABLE public.pets DROP CONSTRAINT IF EXISTS pets_user_id_fkey;
ALTER TABLE public.pets ADD CONSTRAINT pets_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.profiles(id) ON DELETE CASCADE;

-- Update vaccine_records
ALTER TABLE public.vaccine_records DROP CONSTRAINT IF EXISTS vaccine_records_uploaded_by_fkey;
ALTER TABLE public.vaccine_records ADD CONSTRAINT vaccine_records_uploaded_by_fkey FOREIGN KEY (uploaded_by) REFERENCES public.profiles(id) ON DELETE SET NULL;

-- Update appointments
ALTER TABLE public.appointments DROP CONSTRAINT IF EXISTS appointments_owner_id_fkey;
ALTER TABLE public.appointments ADD CONSTRAINT appointments_owner_id_fkey FOREIGN KEY (owner_id) REFERENCES public.profiles(id) ON DELETE CASCADE;

-- Update notifications
ALTER TABLE public.notifications DROP CONSTRAINT IF EXISTS notifications_user_id_fkey;
ALTER TABLE public.notifications ADD CONSTRAINT notifications_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.profiles(id) ON DELETE CASCADE;

-- Update clinic_reviews
ALTER TABLE public.clinic_reviews DROP CONSTRAINT IF EXISTS clinic_reviews_owner_id_fkey;
ALTER TABLE public.clinic_reviews ADD CONSTRAINT clinic_reviews_owner_id_fkey FOREIGN KEY (owner_id) REFERENCES public.profiles(id) ON DELETE CASCADE;

-- 3. Drop the old auth_users table
DROP TABLE IF EXISTS public.auth_users CASCADE;

-- 4. Create trigger to automatically create profile on signup
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger AS $$
BEGIN
  INSERT INTO public.profiles (id, role, phone, is_active)
  VALUES (
    new.id,
    COALESCE(new.raw_user_meta_data->>'role', 'owner'),
    COALESCE(new.raw_user_meta_data->>'phone', ''),
    true
  );
  RETURN new;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- 5. Enable Row Level Security (RLS)
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.pet_owners ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.clinics ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.pets ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.appointments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.clinic_reviews ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.notifications ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.vaccine_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.medical_records ENABLE ROW LEVEL SECURITY;

-- 6. RLS Policies

-- PROFILES POLICIES
CREATE POLICY "Allow users to read their own profile" ON public.profiles
  FOR SELECT TO authenticated USING (auth.uid() = id);

CREATE POLICY "Allow users to update their own profile" ON public.profiles
  FOR UPDATE TO authenticated USING (auth.uid() = id);

CREATE POLICY "Allow admins full access to profiles" ON public.profiles
  FOR ALL TO authenticated USING (
    EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role = 'admin')
  );

-- PET OWNERS POLICIES
CREATE POLICY "Allow owners to manage their own profile details" ON public.pet_owners
  FOR ALL TO authenticated USING (auth.uid() = user_id);

CREATE POLICY "Allow clinics to view pet owner details" ON public.pet_owners
  FOR SELECT TO authenticated USING (
    EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role = 'clinic')
  );

CREATE POLICY "Allow admins full access to pet owners" ON public.pet_owners
  FOR ALL TO authenticated USING (
    EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role = 'admin')
  );

-- CLINICS POLICIES
CREATE POLICY "Allow clinics to manage their own profile details" ON public.clinics
  FOR ALL TO authenticated USING (auth.uid() = user_id);

CREATE POLICY "Allow anyone to view verified clinics" ON public.clinics
  FOR SELECT USING (is_verified = true);

CREATE POLICY "Allow admins full access to clinics" ON public.clinics
  FOR ALL TO authenticated USING (
    EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role = 'admin')
  );

-- PETS POLICIES
CREATE POLICY "Allow owners to manage their own pets" ON public.pets
  FOR ALL TO authenticated USING (auth.uid() = user_id);

CREATE POLICY "Allow clinics to view pets" ON public.pets
  FOR SELECT TO authenticated USING (
    EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role = 'clinic')
  );

CREATE POLICY "Allow admins full access to pets" ON public.pets
  FOR ALL TO authenticated USING (
    EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role = 'admin')
  );

-- APPOINTMENTS POLICIES
CREATE POLICY "Allow owners to manage their own appointments" ON public.appointments
  FOR ALL TO authenticated USING (auth.uid() = owner_id);

CREATE POLICY "Allow clinics to view and update their own appointments" ON public.appointments
  FOR ALL TO authenticated USING (
    clinic_id IN (SELECT id FROM public.clinics WHERE user_id = auth.uid())
  );

CREATE POLICY "Allow admins full access to appointments" ON public.appointments
  FOR ALL TO authenticated USING (
    EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role = 'admin')
  );

-- CLINIC REVIEWS POLICIES
CREATE POLICY "Allow owners to manage reviews for their appointments" ON public.clinic_reviews
  FOR ALL TO authenticated USING (auth.uid() = owner_id);

CREATE POLICY "Allow clinics to view reviews" ON public.clinic_reviews
  FOR SELECT TO authenticated USING (true);

-- NOTIFICATIONS POLICIES
CREATE POLICY "Allow users to manage their own notifications" ON public.notifications
  FOR ALL TO authenticated USING (auth.uid() = user_id);

-- VACCINE RECORDS POLICIES
CREATE POLICY "Allow owners to view and upload vaccine records for their pets" ON public.vaccine_records
  FOR ALL TO authenticated USING (
    pet_id IN (SELECT id FROM public.pets WHERE user_id = auth.uid())
  );

CREATE POLICY "Allow clinics to view vaccine records" ON public.vaccine_records
  FOR SELECT TO authenticated USING (
    EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role = 'clinic')
  );

-- MEDICAL RECORDS POLICIES
CREATE POLICY "Allow owners to view medical records for their pets" ON public.medical_records
  FOR SELECT TO authenticated USING (
    pet_id IN (SELECT id FROM public.pets WHERE user_id = auth.uid())
  );

CREATE POLICY "Allow clinics to manage medical records" ON public.medical_records
  FOR ALL TO authenticated USING (
    clinic_id IN (SELECT id FROM public.clinics WHERE user_id = auth.uid())
  );

-- 7. Storage Buckets & Policies
INSERT INTO storage.buckets (id, name, public)
VALUES 
  ('pet-images', 'pet-images', true),
  ('clinic-logos', 'clinic-logos', true),
  ('medical-records', 'medical-records', false),
  ('vaccine-documents', 'vaccine-documents', false)
ON CONFLICT (id) DO NOTHING;

-- Storage RLS Policies
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
    EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role = 'clinic')
  )
);

-- Vaccine Documents (Private Read/Write)
CREATE POLICY "Allow access to vaccine documents" ON storage.objects FOR ALL TO authenticated USING (
  bucket_id = 'vaccine-documents' AND (
    EXISTS (SELECT 1 FROM public.pets WHERE id::text = (storage.foldername(name))[1] AND user_id = auth.uid()) OR
    EXISTS (SELECT 1 FROM public.profiles WHERE id = auth.uid() AND role = 'clinic')
  )
);

COMMIT;
