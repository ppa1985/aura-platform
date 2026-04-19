import { Pool } from "pg";

declare global {
  // eslint-disable-next-line no-var
  var __aura_pool: Pool | undefined;
}

const pool =
  global.__aura_pool ??
  new Pool({
    connectionString: process.env.DATABASE_URL,
    max: 4,
  });

if (process.env.NODE_ENV !== "production") {
  global.__aura_pool = pool;
}

export async function query<T = unknown>(text: string, params: unknown[] = []): Promise<T[]> {
  const res = await pool.query(text, params);
  return res.rows as T[];
}

export const SCHEMA = "app_warehouse_management_system";
