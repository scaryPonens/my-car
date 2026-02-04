-- =============================================================================
-- Smart Car VA Database Schema
-- PostgreSQL with Supabase Row Level Security (RLS)
-- =============================================================================

-- =============================================================================
-- Users Table
-- =============================================================================

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    telegram_id BIGINT UNIQUE NOT NULL,
    username VARCHAR(255),
    first_name VARCHAR(255),
    last_name VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for fast telegram_id lookups
CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id);

-- =============================================================================
-- Vehicles Table
-- =============================================================================

CREATE TABLE IF NOT EXISTS vehicles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    smartcar_vehicle_id VARCHAR(255) NOT NULL,
    make VARCHAR(100),
    model VARCHAR(100),
    year INTEGER,
    access_token TEXT,
    refresh_token TEXT,
    token_expiration TIMESTAMP WITH TIME ZONE,
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Unique constraint on smartcar_vehicle_id per user
    UNIQUE(smartcar_vehicle_id)
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_vehicles_user_id ON vehicles(user_id);
CREATE INDEX IF NOT EXISTS idx_vehicles_smartcar_id ON vehicles(smartcar_vehicle_id);
CREATE INDEX IF NOT EXISTS idx_vehicles_status ON vehicles(status);

-- =============================================================================
-- Vehicle Telemetry Table (Optional - for historical data)
-- =============================================================================

CREATE TABLE IF NOT EXISTS vehicle_telemetry (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vehicle_id UUID NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,
    odometer_km DECIMAL(12, 2),
    fuel_percent DECIMAL(5, 2),
    battery_percent DECIMAL(5, 2),
    latitude DECIMAL(10, 7),
    longitude DECIMAL(10, 7),
    tire_pressure_fl DECIMAL(6, 2),
    tire_pressure_fr DECIMAL(6, 2),
    tire_pressure_rl DECIMAL(6, 2),
    tire_pressure_rr DECIMAL(6, 2),
    recorded_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for time-series queries
CREATE INDEX IF NOT EXISTS idx_telemetry_vehicle_time
    ON vehicle_telemetry(vehicle_id, recorded_at DESC);

-- =============================================================================
-- Conversations Table (Optional - for LLM context persistence)
-- =============================================================================

CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    messages JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for user conversations
CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);

-- =============================================================================
-- Updated At Trigger Function
-- =============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Apply trigger to all tables with updated_at
DROP TRIGGER IF EXISTS update_users_updated_at ON users;
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_vehicles_updated_at ON vehicles;
CREATE TRIGGER update_vehicles_updated_at
    BEFORE UPDATE ON vehicles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

DROP TRIGGER IF EXISTS update_conversations_updated_at ON conversations;
CREATE TRIGGER update_conversations_updated_at
    BEFORE UPDATE ON conversations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- Row Level Security (RLS) Policies
-- =============================================================================

-- Enable RLS on all tables
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE vehicles ENABLE ROW LEVEL SECURITY;
ALTER TABLE vehicle_telemetry ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;

-- Service role bypass (for backend operations)
-- The service role key allows full access regardless of RLS

-- Users policies
-- Users can only read their own data (via authenticated role)
CREATE POLICY "Users can view own data" ON users
    FOR SELECT
    USING (auth.uid()::text = id::text);

-- Vehicles policies
-- Users can only access their own vehicles
CREATE POLICY "Users can view own vehicles" ON vehicles
    FOR SELECT
    USING (user_id IN (
        SELECT id FROM users WHERE auth.uid()::text = users.id::text
    ));

CREATE POLICY "Users can update own vehicles" ON vehicles
    FOR UPDATE
    USING (user_id IN (
        SELECT id FROM users WHERE auth.uid()::text = users.id::text
    ));

-- Telemetry policies
CREATE POLICY "Users can view own telemetry" ON vehicle_telemetry
    FOR SELECT
    USING (vehicle_id IN (
        SELECT id FROM vehicles WHERE user_id IN (
            SELECT id FROM users WHERE auth.uid()::text = users.id::text
        )
    ));

-- Conversations policies
CREATE POLICY "Users can view own conversations" ON conversations
    FOR SELECT
    USING (user_id IN (
        SELECT id FROM users WHERE auth.uid()::text = users.id::text
    ));

CREATE POLICY "Users can update own conversations" ON conversations
    FOR UPDATE
    USING (user_id IN (
        SELECT id FROM users WHERE auth.uid()::text = users.id::text
    ));

-- =============================================================================
-- Service Role Policies (for backend API access)
-- These allow the service role to bypass RLS for server-side operations
-- =============================================================================

-- Allow service role full access to all tables
CREATE POLICY "Service role full access to users" ON users
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Service role full access to vehicles" ON vehicles
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Service role full access to telemetry" ON vehicle_telemetry
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

CREATE POLICY "Service role full access to conversations" ON conversations
    FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

-- =============================================================================
-- Sample Queries for Reference
-- =============================================================================

-- Get user with their vehicles:
-- SELECT u.*, json_agg(v.*) as vehicles
-- FROM users u
-- LEFT JOIN vehicles v ON v.user_id = u.id
-- WHERE u.telegram_id = 123456789
-- GROUP BY u.id;

-- Get latest telemetry for a vehicle:
-- SELECT * FROM vehicle_telemetry
-- WHERE vehicle_id = 'uuid-here'
-- ORDER BY recorded_at DESC
-- LIMIT 1;

-- Get all vehicles with status:
-- SELECT v.*, u.telegram_id, u.username
-- FROM vehicles v
-- JOIN users u ON u.id = v.user_id
-- WHERE v.status = 'active';
