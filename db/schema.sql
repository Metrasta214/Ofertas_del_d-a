CREATE TABLE IF NOT EXISTS offers (
  id TEXT PRIMARY KEY,
  external_id TEXT UNIQUE NOT NULL,
  title TEXT NOT NULL,
  image_url TEXT NOT NULL,
  product_url TEXT NOT NULL,
  affiliate_url TEXT,
  price NUMERIC(12, 2) NOT NULL,
  original_price NUMERIC(12, 2),
  discount INTEGER NOT NULL DEFAULT 0,
  seller TEXT NOT NULL DEFAULT 'Mercado Libre',
  shipping TEXT NOT NULL DEFAULT 'Consulta las condiciones de envío',
  category TEXT NOT NULL DEFAULT 'General',
  status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected', 'sent')),
  message TEXT NOT NULL,
  found_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  sent_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS offers_status_found_at_idx
  ON offers(status, found_at DESC);
