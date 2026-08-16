# Paycheck Tracker

A personal finance app focused on **paycheck-to-paycheck** tracking.  
Shows you clearly how much is left after bills each pay period.

## Features

- **Login screen** (simple username + password)
- Current paycheck dashboard with **leftover** as the main number
- Quick transaction entry with your real categories & subcategories
- One-click **Create next paycheck period**
- Pre-load suggested recurring bills based on due dates / typical amounts
- Browse past paycheck periods
- Search & filter transaction history
- Change password in Settings

## Default login (change this immediately)

- Username: `doug`
- Password: `change-me`

## Running locally (for testing)

```bash
cd paycheck-tracker
pip install -r requirements.txt
cd app
python seed.py          # only needed the first time
streamlit run main.py
```

## Deploying online (so you can open it from any device)

### Recommended free path

1. Go to [https://share.streamlit.io](https://share.streamlit.io) (Streamlit Community Cloud)
2. Deploy this repo (point the main file at `app/main.py`)
3. For persistent data across restarts, set a free Postgres database:
   - Create a free account at [Neon.tech](https://neon.tech) or [Supabase](https://supabase.com)
   - Copy the connection string
   - In Streamlit Cloud → App settings → Secrets, add:

```toml
DATABASE_URL = "postgresql://user:pass@host/dbname"
```

4. (Optional) Add your Gmail for notifications later

### Changing the default password

After first login go to **Settings → Change password**.

## Data model notes

- Paycheck periods are date ranges (you control start/end).
- Leftover = Income − Bills − Debt − Expenses − Savings
- Recurring suggestions come from the seeded list taken from your existing spreadsheet.
- Most payments are assumed to be on credit card; you can change the payment method per transaction.

## Next improvements (easy to add later)

- Email notifications when a transaction is saved (using Gmail or SMTP)
- Import CSV of bank transactions
- Edit existing transactions
- Better mobile styling
- Automatic period creation on a schedule

---

Built for personal use. Your data stays in the database you control.
