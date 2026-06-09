-- Notification storage for owners, clinics, and admins
-- Run this in Supabase/PostgreSQL before enabling real notifications.

CREATE TABLE
IF NOT EXISTS notifications
(
  id UUID PRIMARY KEY DEFAULT gen_random_uuid
(),
  user_id UUID NOT NULL REFERENCES auth_users
(id) ON
DELETE CASCADE,
  user_role VARCHAR(20),
  type VARCHAR
(50) NOT NULL,
  title VARCHAR
(255) NOT NULL,
  message TEXT NOT NULL,
  entity_type VARCHAR
(50),
  entity_id UUID,
  link_url VARCHAR
(500),
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
  is_read BOOLEAN NOT NULL DEFAULT FALSE,
  read_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW
(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW
(),
  CONSTRAINT notifications_user_role_check CHECK
(user_role IS NULL OR user_role IN
('owner', 'clinic', 'admin'))
);

CREATE INDEX
IF NOT EXISTS idx_notifications_user_id ON notifications
(user_id);
CREATE INDEX
IF NOT EXISTS idx_notifications_user_id_is_read ON notifications
(user_id, is_read);
CREATE INDEX
IF NOT EXISTS idx_notifications_created_at ON notifications
(created_at DESC);

-- Optional trigger to keep updated_at fresh
CREATE OR REPLACE FUNCTION set_notifications_updated_at
()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW
();
RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_notifications_updated_at
ON notifications;
CREATE TRIGGER trg_notifications_updated_at
BEFORE
UPDATE ON notifications
FOR EACH ROW
EXECUTE FUNCTION set_notifications_updated_at
();
