import { neon } from "@neondatabase/serverless";

function json(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json", "Access-Control-Allow-Origin": "*" }
  });
}

function getSql(env) {
  const url = env.DATABASE_URL;
  if (!url) throw new Error("DATABASE_URL not set");
  return neon(url);
}

function extractDueDay(name) {
  const m = name.match(/\((\d{1,2})(?:st|nd|rd|th)?\)/);
  return m ? parseInt(m[1], 10) : null;
}

function getPaymentType(name) {
  if (name.includes("Extra Credit Card")) return "Every period";
  if (name.includes("(AP)")) return "Auto-pay";
  if (name.includes("(BP)") || name.includes("(MT)")) return "Manual";
  return "Manual";
}

function isDueInPeriod(name, start, end) {
  const day = extractDueDay(name);
  if (day == null) return false;
  let d = new Date(start);
  const endD = new Date(end);
  while (d <= endD) {
    if (d.getUTCDate() === day) return true;
    d.setUTCDate(d.getUTCDate() + 1);
  }
  return false;
}

const BASE_BILLS_DEBT = {
  Bills: [
    "Child Support (MT)", "iCloud (1st) (AP)", "Paramount+ (4th) (AP)", "Spotify (5th) (AP)",
    "Netflix (5th) (AP)", "Cell Phone (9th) (AP)", "OnStar (11th) (AP)", "REMC Fiber (12th) (AP)",
    "Microsoft (12th) (AP)", "Nest (16th) (AP)", "Sallie Mae (16th) (BP)", "REMC (17th) (AP)",
    "Beach Body (17th) (AP)", "Life 360 (17th) (AP)", "Hulu (19th) (AP)", "Sewage (22nd) (AP)",
    "Insurance (23rd) (AP)", "Amazon CC (23rd) (BP)", "Youtube TV (23rd) (AP)", "Water (26th) (AP)",
    "NIPSCO (26th) (BP)", "Peacock (28th) (AP)", "Spotify (29th) (AP)"
  ],
  Debt: [
    "Mortgage (1st) (BP)", "Windows (5th) (BP)", "Ravi (7th) (MT)",
    "Truck (15th) (MT)", "Extra Truck (MT)", "Extra Credit Card (BP) (MT)"
  ]
};

const TYPICAL = {
  "Child Support (MT)": 680, "iCloud (1st) (AP)": 9.99, "Spotify (5th) (AP)": 16.99,
  "Netflix (5th) (AP)": 19.99, "Cell Phone (9th) (AP)": 425, "OnStar (11th) (AP)": 14.99,
  "REMC Fiber (12th) (AP)": 80.44, "Microsoft (12th) (AP)": 21.39, "Nest (16th) (AP)": 15,
  "Sallie Mae (16th) (BP)": 40, "REMC (17th) (AP)": 150, "Beach Body (17th) (AP)": 15.95,
  "Life 360 (17th) (AP)": 16.04, "Hulu (19th) (AP)": 19.95, "Sewage (22nd) (AP)": 71,
  "Insurance (23rd) (AP)": 246.19, "Amazon CC (23rd) (BP)": 200, "Youtube TV (23rd) (AP)": 120,
  "Water (26th) (AP)": 85, "NIPSCO (26th) (BP)": 47, "Peacock (28th) (AP)": 11.99,
  "Spotify (29th) (AP)": 19.99, "Mortgage (1st) (BP)": 2206.90, "Windows (5th) (BP)": 301.46,
  "Ravi (7th) (MT)": 709.27, "Truck (15th) (MT)": 659.29, "Extra Credit Card (BP) (MT)": 0
};

async function ensureTables(sql) {
  await sql`CREATE TABLE IF NOT EXISTS paycheck_periods (
    id SERIAL PRIMARY KEY,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    label VARCHAR(50),
    is_current BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW()
  )`;
  await sql`CREATE TABLE IF NOT EXISTS transactions (
    id SERIAL PRIMARY KEY,
    period_id INTEGER REFERENCES paycheck_periods(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    amount REAL NOT NULL,
    category VARCHAR(50) NOT NULL,
    subcategory VARCHAR(100) NOT NULL,
    description VARCHAR(255),
    method VARCHAR(50),
    status VARCHAR(20) DEFAULT 'Pending',
    created_at TIMESTAMPTZ DEFAULT NOW()
  )`;
  await sql`CREATE TABLE IF NOT EXISTS custom_subcategories (
    id SERIAL PRIMARY KEY,
    category VARCHAR(50) NOT NULL,
    name VARCHAR(100) NOT NULL
  )`;
}

async function getSummary(sql, periodId) {
  const rows = await sql`SELECT category, amount FROM transactions WHERE period_id = ${periodId}`;
  const totals = { Income: 0, Savings: 0, Bills: 0, Expenses: 0, Debt: 0 };
  for (const r of rows) {
    if (totals[r.category] !== undefined) totals[r.category] += Number(r.amount);
  }
  const total_out = totals.Bills + totals.Debt + totals.Expenses + totals.Savings;
  return { ...totals, leftover: totals.Income - total_out, total_out };
}

export async function onRequest(context) {
  const { request, env } = context;
  const url = new URL(request.url);
  const path = url.pathname.replace(/^\/api/, "") || "/";
  const method = request.method;

  if (method === "OPTIONS") {
    return new Response(null, {
      headers: {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET,POST,PATCH,DELETE,OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type"
      }
    });
  }

  try {
    const sql = getSql(env);
    await ensureTables(sql);

    // POST /api/import  — bulk import historical data
    if (path === "/import" && method === "POST") {
      const body = await request.json();
      const periods = body.periods || [];
      const transactions = body.transactions || [];

      // Clear existing data
      await sql`DELETE FROM transactions`;
      await sql`DELETE FROM paycheck_periods`;

      // Insert periods and keep id map
      const idMap = [];
      for (const p of periods) {
        const [row] = await sql`INSERT INTO paycheck_periods (start_date, end_date, label, is_current)
          VALUES (${p.start}, ${p.end}, ${p.label}, ${!!p.is_current}) RETURNING id`;
        idMap.push(row.id);
      }

      // Insert transactions
      let count = 0;
      for (const t of transactions) {
        const periodId = idMap[t.period_idx];
        if (!periodId) continue;
        await sql`INSERT INTO transactions
          (period_id, date, amount, category, subcategory, description, method, status)
          VALUES (${periodId}, ${t.date}, ${t.amount}, ${t.category}, ${t.subcategory},
                  ${t.description || null}, ${t.method || "Manual"}, ${t.status || "Paid"})`;
        count++;
      }

      return json({ ok: true, periods: periods.length, transactions: count });
    }

    // GET /api/period/current
    if (path === "/period/current" && method === "GET") {
      let [period] = await sql`SELECT * FROM paycheck_periods WHERE is_current = true LIMIT 1`;
      if (!period) {
        const start = new Date().toISOString().slice(0, 10);
        const end = new Date(Date.now() + 13 * 86400000).toISOString().slice(0, 10);
        [period] = await sql`INSERT INTO paycheck_periods (start_date, end_date, label, is_current)
          VALUES (${start}, ${end}, ${start.slice(5) + " – " + end.slice(5)}, true) RETURNING *`;
      }
      const summary = await getSummary(sql, period.id);
      const transactions = await sql`SELECT * FROM transactions WHERE period_id = ${period.id} ORDER BY date DESC`;

      const existing = new Set(
        (await sql`SELECT category, subcategory FROM transactions WHERE period_id = ${period.id}`)
          .map(t => t.category + "|" + t.subcategory)
      );
      const auto_items = [];
      for (const [cat, subs] of Object.entries(BASE_BILLS_DEBT)) {
        for (const sub of subs) {
          if (existing.has(cat + "|" + sub)) continue;
          if (sub.includes("Extra Credit Card") || isDueInPeriod(sub, period.start_date, period.end_date)) {
            auto_items.push({
              category: cat,
              subcategory: sub,
              amount: TYPICAL[sub] || 0,
              ptype: getPaymentType(sub)
            });
          }
        }
      }

      return json({ period, summary, transactions, auto_items });
    }

    // POST /api/period/next
    if (path === "/period/next" && method === "POST") {
      const [current] = await sql`SELECT * FROM paycheck_periods WHERE is_current = true LIMIT 1`;
      if (current) {
        await sql`UPDATE paycheck_periods SET is_current = false WHERE id = ${current.id}`;
        const start = new Date(current.end_date);
        start.setUTCDate(start.getUTCDate() + 1);
        const length = Math.round((new Date(current.end_date) - new Date(current.start_date)) / 86400000);
        const end = new Date(start);
        end.setUTCDate(end.getUTCDate() + length);
        const s = start.toISOString().slice(0, 10);
        const e = end.toISOString().slice(0, 10);
        const label = s.slice(5) + " – " + e.slice(5);
        await sql`INSERT INTO paycheck_periods (start_date, end_date, label, is_current)
          VALUES (${s}, ${e}, ${label}, true)`;
      }
      return json({ ok: true });
    }

    // GET /api/periods
    if (path === "/periods" && method === "GET") {
      const periods = await sql`SELECT * FROM paycheck_periods ORDER BY start_date DESC`;
      return json(periods);
    }

    // GET /api/period/:id
    if (path.match(/^\/period\/\d+$/) && method === "GET") {
      const id = parseInt(path.split("/")[2]);
      const [period] = await sql`SELECT * FROM paycheck_periods WHERE id = ${id}`;
      const summary = await getSummary(sql, id);
      const transactions = await sql`SELECT * FROM transactions WHERE period_id = ${id} ORDER BY date DESC`;
      return json({ period, summary, transactions });
    }

    // POST /api/transactions
    if (path === "/transactions" && method === "POST") {
      const body = await request.json();
      const [row] = await sql`INSERT INTO transactions
        (period_id, date, amount, category, subcategory, description, method, status)
        VALUES (${body.period_id}, ${body.date}, ${body.amount}, ${body.category},
                ${body.subcategory}, ${body.description || null}, ${body.method || null}, ${body.status || "Pending"})
        RETURNING *`;
      return json(row, 201);
    }

    // GET/PATCH/DELETE /api/transactions/:id
    if (path.match(/^\/transactions\/\d+$/)) {
      const id = parseInt(path.split("/")[2]);
      if (method === "GET") {
        const [row] = await sql`SELECT * FROM transactions WHERE id = ${id}`;
        return json(row || {}, row ? 200 : 404);
      }
      if (method === "PATCH") {
        const body = await request.json();
        const [row] = await sql`UPDATE transactions SET
          date = COALESCE(${body.date || null}, date),
          amount = COALESCE(${body.amount ?? null}, amount),
          category = COALESCE(${body.category || null}, category),
          subcategory = COALESCE(${body.subcategory || null}, subcategory),
          description = COALESCE(${body.description || null}, description),
          status = COALESCE(${body.status || null}, status)
          WHERE id = ${id} RETURNING *`;
        return json(row);
      }
      if (method === "DELETE") {
        await sql`DELETE FROM transactions WHERE id = ${id}`;
        return json({ ok: true });
      }
    }

    // GET/POST /api/custom
    if (path === "/custom") {
      if (method === "GET") {
        return json(await sql`SELECT * FROM custom_subcategories ORDER BY category, name`);
      }
      if (method === "POST") {
        const body = await request.json();
        const [row] = await sql`INSERT INTO custom_subcategories (category, name)
          VALUES (${body.category}, ${body.name}) RETURNING *`;
        return json(row, 201);
      }
    }

    // GET /api/search
    if (path === "/search" && method === "GET") {
      const q = url.searchParams.get("q") || "";
      const cat = url.searchParams.get("category") || "";
      let rows;
      if (q && cat) {
        rows = await sql`SELECT * FROM transactions
          WHERE category = ${cat} AND (subcategory ILIKE ${"%"+q+"%"} OR description ILIKE ${"%"+q+"%"})
          ORDER BY date DESC LIMIT 200`;
      } else if (q) {
        rows = await sql`SELECT * FROM transactions
          WHERE subcategory ILIKE ${"%"+q+"%"} OR description ILIKE ${"%"+q+"%"} OR category ILIKE ${"%"+q+"%"}
          ORDER BY date DESC LIMIT 200`;
      } else if (cat) {
        rows = await sql`SELECT * FROM transactions WHERE category = ${cat} ORDER BY date DESC LIMIT 200`;
      } else {
        rows = await sql`SELECT * FROM transactions ORDER BY date DESC LIMIT 100`;
      }
      return json(rows);
    }

    return json({ error: "Not found" }, 404);
  } catch (err) {
    return json({ error: err.message }, 500);
  }
}
