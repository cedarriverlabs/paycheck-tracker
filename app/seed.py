"""
Seed the database with the user's real categories, subcategories,
and typical recurring amounts extracted from their existing spreadsheet.
"""

from datetime import date, timedelta
from database import (
    init_db, get_session, Subcategory, PaycheckPeriod, User
)
import bcrypt


# ---------- Categories & Subcategories from Bills 2026 ----------
SEED_SUBCATEGORIES = [
    # INCOME
    {"category": "Income", "name": "Doug Paycheck", "is_recurring": True, "typical_amount": 3639.45, "due_info": None},
    {"category": "Income", "name": "Amanda Paycheck", "is_recurring": True, "typical_amount": 1295.65, "due_info": None},
    {"category": "Income", "name": "Doug Bonus", "is_recurring": False, "typical_amount": None, "due_info": None},
    {"category": "Income", "name": "Amanda Bonus", "is_recurring": False, "typical_amount": None, "due_info": None},
    {"category": "Income", "name": "Doug VA", "is_recurring": False, "typical_amount": None, "due_info": None},

    # SAVINGS
    {"category": "Savings", "name": "Emergency Fund (MT)", "is_recurring": True, "typical_amount": None, "due_info": "MT"},

    # BILLS (recurring with due info)
    {"category": "Bills", "name": "Child Support (MT)", "is_recurring": True, "typical_amount": 680.00, "due_info": "MT"},
    {"category": "Bills", "name": "iCloud (1st) (AP)", "is_recurring": True, "typical_amount": 9.99, "due_info": "1st (AP)"},
    {"category": "Bills", "name": "Paramount+ (4th) (AP)", "is_recurring": True, "typical_amount": None, "due_info": "4th (AP)"},
    {"category": "Bills", "name": "Spotify (5th) (AP)", "is_recurring": True, "typical_amount": 16.99, "due_info": "5th (AP)"},
    {"category": "Bills", "name": "Netflix (5th) (AP)", "is_recurring": True, "typical_amount": 19.99, "due_info": "5th (AP)"},
    {"category": "Bills", "name": "Cell Phone (9th) (AP)", "is_recurring": True, "typical_amount": 425.00, "due_info": "9th (AP)"},
    {"category": "Bills", "name": "OnStar (11th) (AP)", "is_recurring": True, "typical_amount": 14.99, "due_info": "11th (AP)"},
    {"category": "Bills", "name": "REMC Fiber (12th) (AP)", "is_recurring": True, "typical_amount": 80.44, "due_info": "12th (AP)"},
    {"category": "Bills", "name": "Microsoft (12th) (AP)", "is_recurring": True, "typical_amount": 21.39, "due_info": "12th (AP)"},
    {"category": "Bills", "name": "Nest (16th) (AP)", "is_recurring": True, "typical_amount": 15.00, "due_info": "16th (AP)"},
    {"category": "Bills", "name": "Sallie Mae (16th) (BP)", "is_recurring": True, "typical_amount": 40.00, "due_info": "16th (BP)"},
    {"category": "Bills", "name": "REMC (17th) (AP)", "is_recurring": True, "typical_amount": 150.00, "due_info": "17th (AP)"},
    {"category": "Bills", "name": "Beach Body (17th) (AP)", "is_recurring": True, "typical_amount": 15.95, "due_info": "17th (AP)"},
    {"category": "Bills", "name": "Life 360 (17th) (AP)", "is_recurring": True, "typical_amount": 16.04, "due_info": "17th (AP)"},
    {"category": "Bills", "name": "Hulu (19th) (AP)", "is_recurring": True, "typical_amount": 19.95, "due_info": "19th (AP)"},
    {"category": "Bills", "name": "Sewage (22nd) (AP)", "is_recurring": True, "typical_amount": 71.00, "due_info": "22nd (AP)"},
    {"category": "Bills", "name": "Insurance (23rd) (AP)", "is_recurring": True, "typical_amount": 246.19, "due_info": "23rd (AP)"},
    {"category": "Bills", "name": "Amazon CC (23rd) (BP)", "is_recurring": True, "typical_amount": 200.00, "due_info": "23rd (BP)"},
    {"category": "Bills", "name": "Youtube TV (23rd) (AP)", "is_recurring": True, "typical_amount": 120.00, "due_info": "23rd (AP)"},
    {"category": "Bills", "name": "Water (26th) (AP)", "is_recurring": True, "typical_amount": 85.00, "due_info": "26th (AP)"},
    {"category": "Bills", "name": "NIPSCO (26th) (BP)", "is_recurring": True, "typical_amount": 47.00, "due_info": "26th (BP)"},
    {"category": "Bills", "name": "Peacock (28th) (AP)", "is_recurring": True, "typical_amount": 11.99, "due_info": "28th (AP)"},
    {"category": "Bills", "name": "Spotify (29th) (AP)", "is_recurring": True, "typical_amount": 19.99, "due_info": "29th (AP)"},

    # EXPENSES
    {"category": "Expenses", "name": "Groceries", "is_recurring": False, "typical_amount": None, "due_info": None},
    {"category": "Expenses", "name": "Gas", "is_recurring": False, "typical_amount": None, "due_info": None},
    {"category": "Expenses", "name": "Other", "is_recurring": False, "typical_amount": None, "due_info": None},

    # DEBT
    {"category": "Debt", "name": "Mortgage (1st) (BP)", "is_recurring": True, "typical_amount": 2206.90, "due_info": "1st (BP)"},
    {"category": "Debt", "name": "Windows (5th) (BP)", "is_recurring": True, "typical_amount": 301.46, "due_info": "5th (BP)"},
    {"category": "Debt", "name": "Ravi (7th) (MT)", "is_recurring": True, "typical_amount": 709.27, "due_info": "7th (MT)"},
    {"category": "Debt", "name": "Truck (15th) (MT)", "is_recurring": True, "typical_amount": 659.29, "due_info": "15th (MT)"},
    {"category": "Debt", "name": "Extra Truck (MT)", "is_recurring": True, "typical_amount": None, "due_info": "MT"},
    {"category": "Debt", "name": "Extra Credit Card (BP) (MT)", "is_recurring": True, "typical_amount": 100.00, "due_info": "BP (MT)"},
]


def create_default_user(session, username: str = "doug", password: str = "change-me"):
    """Create the primary user. Change the password after first login."""
    existing = session.query(User).filter_by(username=username).first()
    if existing:
        return existing
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    user = User(username=username, password_hash=hashed, email=None)
    session.add(user)
    session.commit()
    return user


def seed_subcategories(session):
    for item in SEED_SUBCATEGORIES:
        exists = session.query(Subcategory).filter_by(
            category=item["category"], name=item["name"]
        ).first()
        if not exists:
            session.add(Subcategory(**item))
    session.commit()


def create_initial_period(session):
    """Create a starting current period based on typical bi-weekly cadence.
    User can adjust dates later.
    """
    existing = session.query(PaycheckPeriod).filter_by(is_current=True).first()
    if existing:
        return existing

    # Approximate current period around mid-August 2026 (from the spreadsheet)
    start = date(2026, 8, 14)
    end = date(2026, 8, 27)
    period = PaycheckPeriod(
        start_date=start,
        end_date=end,
        label=f"{start.strftime('%b %d')} – {end.strftime('%b %d')}",
        is_current=True,
    )
    session.add(period)
    session.commit()
    return period


def run_seed():
    init_db()
    session = get_session()
    try:
        create_default_user(session)
        seed_subcategories(session)
        create_initial_period(session)
        print("✅ Database seeded successfully.")
        print("   Default login → username: doug  |  password: change-me")
        print("   Please change the password after first login.")
    finally:
        session.close()


if __name__ == "__main__":
    run_seed()
