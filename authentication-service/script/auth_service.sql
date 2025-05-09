-- auth_service.sql

-- 1. Ensure the `users` table exists
CREATE TABLE IF NOT EXISTS users (
  id SERIAL PRIMARY KEY,
  email VARCHAR(255) UNIQUE NOT NULL,
  password VARCHAR(255) NOT NULL
);

-- 2. (Optional) If you need to store more fields later,
--    add them here, e.g., totp_secret, created_at, etc.
-- ALTER TABLE users ADD COLUMN IF NOT EXISTS totp_secret VARCHAR(32);
