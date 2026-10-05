CREATE TABLE IF NOT EXISTS bookings (
 id TEXT PRIMARY KEY,
 request_key TEXT NOT NULL UNIQUE,
 owner_key TEXT NOT NULL,
 customer_name TEXT NOT NULL,
 customer_phone TEXT NOT NULL,
 service_id TEXT NOT NULL,
 service_name TEXT NOT NULL,
 price_cents INTEGER NOT NULL CHECK(price_cents >= 0),
 professional_id TEXT NOT NULL,
 professional_name TEXT NOT NULL,
 day TEXT NOT NULL,
 start_minute INTEGER NOT NULL CHECK(start_minute >= 0 AND start_minute < 1440),
 end_minute INTEGER NOT NULL CHECK(end_minute > start_minute AND end_minute <= 1440),
 status TEXT NOT NULL CHECK(status IN ('pending','confirmed','completed','cancelled','blocked')),
 note TEXT NOT NULL DEFAULT '',
 created_at TEXT NOT NULL,
 updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS bravo_day_prof ON bookings(day,professional_id,status);
CREATE TABLE IF NOT EXISTS audit (
 id TEXT PRIMARY KEY,
 booking_id TEXT NOT NULL REFERENCES bookings(id),
 action TEXT NOT NULL,
 actor TEXT NOT NULL,
 note TEXT NOT NULL DEFAULT '',
 created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS bravo_audit_booking ON audit(booking_id,created_at);
CREATE TABLE IF NOT EXISTS rate_limits (
 key TEXT PRIMARY KEY,
 hits INTEGER NOT NULL,
 expires_at INTEGER NOT NULL
);
