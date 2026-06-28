-- =========================================================================
-- PetPULSE Google OAuth & public.users Migration SQL
-- =========================================================================

BEGIN;

-- 1. Create public.users table
CREATE TABLE IF NOT EXISTS public.users (
  id uuid NOT NULL PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  email character varying NOT NULL,
  full_name character varying,
  role character varying CHECK (role IN ('owner', 'clinic', 'admin')),
  avatar_url character varying,
  phone_number character varying,
  created_at timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL,
  updated_at timestamp with time zone DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- Migrate existing data from public.profiles if any exist
-- INSERT INTO public.users (id, email, role, phone_number, created_at, updated_at)
-- SELECT p.id, u.email, p.role, p.phone, p.created_at, p.updated_at 
-- FROM public.profiles p
-- JOIN auth.users u ON p.id = u.id
-- ON CONFLICT (id) DO NOTHING;

-- 2. Re-link foreign keys to public.users
-- Update pet_owners
ALTER TABLE public.pet_owners DROP CONSTRAINT IF EXISTS pet_owners_user_id_fkey;
ALTER TABLE public.pet_owners ADD CONSTRAINT pet_owners_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;

-- Update clinics
ALTER TABLE public.clinics DROP CONSTRAINT IF EXISTS clinics_user_id_fkey;
ALTER TABLE public.clinics ADD CONSTRAINT clinics_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;

-- Update pets
ALTER TABLE public.pets DROP CONSTRAINT IF EXISTS pets_user_id_fkey;
ALTER TABLE public.pets ADD CONSTRAINT pets_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;

-- Update vaccine_records
ALTER TABLE public.vaccine_records DROP CONSTRAINT IF EXISTS vaccine_records_uploaded_by_fkey;
ALTER TABLE public.vaccine_records ADD CONSTRAINT vaccine_records_uploaded_by_fkey FOREIGN KEY (uploaded_by) REFERENCES public.users(id) ON DELETE SET NULL;

-- Update appointments
ALTER TABLE public.appointments DROP CONSTRAINT IF EXISTS appointments_owner_id_fkey;
ALTER TABLE public.appointments ADD CONSTRAINT appointments_owner_id_fkey FOREIGN KEY (owner_id) REFERENCES public.users(id) ON DELETE CASCADE;

-- Update notifications
ALTER TABLE public.notifications DROP CONSTRAINT IF EXISTS notifications_user_id_fkey;
ALTER TABLE public.notifications ADD CONSTRAINT notifications_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;

-- Update clinic_reviews
ALTER TABLE public.clinic_reviews DROP CONSTRAINT IF EXISTS clinic_reviews_owner_id_fkey;
ALTER TABLE public.clinic_reviews ADD CONSTRAINT clinic_reviews_owner_id_fkey FOREIGN KEY (owner_id) REFERENCES public.users(id) ON DELETE CASCADE;

-- 3. Drop old profiles table (if it exists)
DROP TABLE IF EXISTS public.profiles CASCADE;

-- 4. Update the trigger function for new users
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

-- Recreate trigger (ensuring it's properly bound)
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- 5. Row Level Security (RLS) & Policies for public.users
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Allow users to read their own user record" ON public.users;
CREATE POLICY "Allow users to read their own user record" ON public.users
  FOR SELECT TO authenticated USING (auth.uid() = id);

DROP POLICY IF EXISTS "Allow users to update their own user record" ON public.users;
CREATE POLICY "Allow users to update their own user record" ON public.users
  FOR UPDATE TO authenticated USING (auth.uid() = id);

DROP POLICY IF EXISTS "Allow admins full access to users" ON public.users;
CREATE POLICY "Allow admins full access to users" ON public.users
  FOR ALL TO authenticated USING (
    (auth.jwt() -> 'user_metadata' ->> 'role') = 'admin'
  );

-- 6. Update other tables' RLS policies to refer to public.users
-- Pet Owners
DROP POLICY IF EXISTS "Allow clinics to view pet owner details" ON public.pet_owners;
CREATE POLICY "Allow clinics to view pet owner details" ON public.pet_owners
  FOR SELECT TO authenticated USING (
    EXISTS (SELECT 1 FROM public.users WHERE id = auth.uid() AND role = 'clinic')
  );

DROP POLICY IF EXISTS "Allow admins full access to pet owners" ON public.pet_owners;
CREATE POLICY "Allow admins full access to pet owners" ON public.pet_owners
  FOR ALL TO authenticated USING (
    EXISTS (SELECT 1 FROM public.users WHERE id = auth.uid() AND role = 'admin')
  );

-- Clinics
DROP POLICY IF EXISTS "Allow admins full access to clinics" ON public.clinics;
CREATE POLICY "Allow admins full access to clinics" ON public.clinics
  FOR ALL TO authenticated USING (
    EXISTS (SELECT 1 FROM public.users WHERE id = auth.uid() AND role = 'admin')
  );

-- Pets
DROP POLICY IF EXISTS "Allow clinics to view pets" ON public.pets;
CREATE POLICY "Allow clinics to view pets" ON public.pets
  FOR SELECT TO authenticated USING (
    EXISTS (SELECT 1 FROM public.users WHERE id = auth.uid() AND role = 'clinic')
  );

DROP POLICY IF EXISTS "Allow admins full access to pets" ON public.pets;
CREATE POLICY "Allow admins full access to pets" ON public.pets
  FOR ALL TO authenticated USING (
    EXISTS (SELECT 1 FROM public.users WHERE id = auth.uid() AND role = 'admin')
  );

-- Appointments
DROP POLICY IF EXISTS "Allow admins full access to appointments" ON public.appointments;
CREATE POLICY "Allow admins full access to appointments" ON public.appointments
  FOR ALL TO authenticated USING (
    EXISTS (SELECT 1 FROM public.users WHERE id = auth.uid() AND role = 'admin')
  );

-- Vaccine Records
DROP POLICY IF EXISTS "Allow clinics to view vaccine records" ON public.vaccine_records;
CREATE POLICY "Allow clinics to view vaccine records" ON public.vaccine_records
  FOR SELECT TO authenticated USING (
    EXISTS (SELECT 1 FROM public.users WHERE id = auth.uid() AND role = 'clinic')
  );

-- Medical Records
DROP POLICY IF EXISTS "Allow clinics to manage medical records" ON public.medical_records;
CREATE POLICY "Allow clinics to manage medical records" ON public.medical_records
  FOR ALL TO authenticated USING (
    clinic_id IN (SELECT id FROM public.clinics WHERE user_id = auth.uid())
  );

-- 7. Update Storage Policies to refer to public.users
-- Medical Records
DROP POLICY IF EXISTS "Allow access to medical records" ON storage.objects;
CREATE POLICY "Allow access to medical records" ON storage.objects FOR ALL TO authenticated USING (
  bucket_id = 'medical-records' AND (
    EXISTS (SELECT 1 FROM public.pets WHERE id::text = (storage.foldername(name))[1] AND user_id = auth.uid()) OR
    EXISTS (SELECT 1 FROM public.users WHERE id = auth.uid() AND role = 'clinic')
  )
);

-- Vaccine Documents
DROP POLICY IF EXISTS "Allow access to vaccine documents" ON storage.objects;
CREATE POLICY "Allow access to vaccine documents" ON storage.objects FOR ALL TO authenticated USING (
  bucket_id = 'vaccine-documents' AND (
    EXISTS (SELECT 1 FROM public.pets WHERE id::text = (storage.foldername(name))[1] AND user_id = auth.uid()) OR
    EXISTS (SELECT 1 FROM public.users WHERE id = auth.uid() AND role = 'clinic')
  )
);

GRANT ALL ON ALL TABLES IN SCHEMA public TO postgres, anon, authenticated, service_role;
GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO postgres, anon, authenticated, service_role;
GRANT ALL ON ALL FUNCTIONS IN SCHEMA public TO postgres, anon, authenticated, service_role;

COMMIT;
