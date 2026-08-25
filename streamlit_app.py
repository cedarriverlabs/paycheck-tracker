import streamlit as st
from datetime import date, timedelta, datetime
import pandas as pd
import re
import os
from sqlalchemy import create_engine, Column, Integer, String, Float, Date, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from sqlalchemy.pool import NullPool

st.set_page_config(
    page_title="Paycheck Tracker",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------- Database ----------
Base = declarative_base()

class PaycheckPeriod(Base):
    __tablename__ = "paycheck_periods"
    id = Column(Integer, primary_key=True)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    label = Column(String(50))
    is_current = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    transactions = relationship("Transaction", back_populates="period", cascade="all, delete-orphan")

class Transaction(Base):
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True)
    period_id = Column(Integer, ForeignKey("paycheck_periods.id"), nullable=False)
    date = Column(Date, nullable=False)
    amount = Column(Float, nullable=False)
    category = Column(String(50), nullable=False)
    subcategory = Column(String(100), nullable=False)
    description = Column(String(255), nullable=True)
    method = Column(String(50), nullable=True)
    status = Column(String(20), default="Pending")
    created_at = Column(DateTime, default=datetime.utcnow)
    period = relationship("PaycheckPeriod", back_populates="transactions")

class CustomSubcategory(Base):
    __tablename__ = "custom_subcategories"
    id = Column(Integer, primary_key=True)
    category = Column(String(50), nullable=False)
    name = Column(String(100), nullable=False)

def get_engine():
    url = os.getenv("DATABASE_URL")
    if url and url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    if not url:
        url = "sqlite:///paycheck.db"
    return create_engine(url, poolclass=NullPool)

engine = get_engine()
SessionLocal = sessionmaker(bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        if session.query(PaycheckPeriod).count() == 0:
            start = date(2026, 8, 14)
            end = date(2026, 8, 27)
            session.add(PaycheckPeriod(
                start_date=start, end_date=end,
                label=f"{start.strftime('%b %d')} – {end.strftime('%b %d')}",
                is_current=True
            ))
            session.commit()
    finally:
        session.close()

init_db()

# ---------- Categories ----------
BASE_CATEGORIES = {
    "Income": ["Doug Paycheck", "Amanda Paycheck", "Doug Bonus", "Amanda Bonus", "Doug VA"],
    "Savings": ["Emergency Fund (MT)"],
    "Bills": [
        "Child Support (MT)", "iCloud (1st) (AP)", "Paramount+ (4th) (AP)", "Spotify (5th) (AP)",
        "Netflix (5th) (AP)", "Cell Phone (9th) (AP)", "OnStar (11th) (AP)", "REMC Fiber (12th) (AP)",
        "Microsoft (12th) (AP)", "Nest (16th) (AP)", "Sallie Mae (16th) (BP)", "REMC (17th) (AP)",
        "Beach Body (17th) (AP)", "Life 360 (17th) (AP)", "Hulu (19th) (AP)", "Sewage (22nd) (AP)",
        "Insurance (23rd) (AP)", "Amazon CC (23rd) (BP)", "Youtube TV (23rd) (AP)", "Water (26th) (AP)",
        "NIPSCO (26th) (BP)", "Peacock (28th) (AP)", "Spotify (29th) (AP)"
    ],
    "Expenses": ["Groceries", "Gas", "Other"],
    "Debt": [
        "Mortgage (1st) (BP)", "Windows (5th) (BP)", "Ravi (7th) (MT)",
        "Truck (15th) (MT)", "Extra Truck (MT)", "Extra Credit Card (BP) (MT)"
    ]
}

TYPICAL_AMOUNTS = {
    "Doug Paycheck": 3639.45, "Amanda Paycheck": 1295.65, "Child Support (MT)": 680.00,
    "iCloud (1st) (AP)": 9.99, "Spotify (5th) (AP)": 16.99, "Netflix (5th) (AP)": 19.99,
    "Cell Phone (9th) (AP)": 425.00, "OnStar (11th) (AP)": 14.99, "REMC Fiber (12th) (AP)": 80.44,
    "Microsoft (12th) (AP)": 21.39, "Nest (16th) (AP)": 15.00, "Sallie Mae (16th) (BP)": 40.00,
    "REMC (17th) (AP)": 150.00, "Beach Body (17th) (AP)": 15.95, "Life 360 (17th) (AP)": 16.04,
    "Hulu (19th) (AP)": 19.95, "Sewage (22nd) (AP)": 71.00, "Insurance (23rd) (AP)": 246.19,
    "Amazon CC (23rd) (BP)": 200.00, "Youtube TV (23rd) (AP)": 120.00, "Water (26th) (AP)": 85.00,
    "NIPSCO (26th) (BP)": 47.00, "Peacock (28th) (AP)": 11.99, "Spotify (29th) (AP)": 19.99,
    "Mortgage (1st) (BP)": 2206.90, "Windows (5th) (BP)": 301.46, "Ravi (7th) (MT)": 709.27,
    "Truck (15th) (MT)": 659.29, "Extra Credit Card (BP) (MT)": 0.0,
}

def get_categories():
    session = SessionLocal()
    try:
        cats = {k: list(v) for k, v in BASE_CATEGORIES.items()}
        for c in session.query(CustomSubcategory).all():
            if c.category in cats and c.name not in cats[c.category]:
                cats[c.category].append(c.name)
        return cats
    finally:
        session.close()

def money(a):
    return f"${a:,.2f}"

def get_current_period(session):
    return session.query(PaycheckPeriod).filter_by(is_current=True).first()

def extract_due_day(name):
    m = re.search(r"\((\d{1,2})(?:st|nd|rd|th)?\)", name)
    return int(m.group(1)) if m else None

def get_payment_type(name):
    if "Extra Credit Card" in name: return "Every period"
    if "(AP)" in name: return "Auto-pay"
    if "(BP)" in name or "(MT)" in name: return "Manual"
    return "Manual"

def is_due_in_period(name, start, end):
    day = extract_due_day(name)
    if day is None: return False
    d = start
    while d <= end:
        if d.day == day: return True
        d += timedelta(days=1)
    return False

def calc_summary(session, period_id):
    rows = session.query(Transaction.category, Transaction.amount).filter_by(period_id=period_id).all()
    totals = {"Income":0.0,"Savings":0.0,"Bills":0.0,"Expenses":0.0,"Debt":0.0}
    for cat, amt in rows:
        if cat in totals: totals[cat] += float(amt or 0)
    leftover = totals["Income"] - totals["Bills"] - totals["Debt"] - totals["Expenses"] - totals["Savings"]
    return {**totals, "leftover": leftover, "total_out": totals["Bills"]+totals["Debt"]+totals["Expenses"]+totals["Savings"]}

def get_auto_items(session, period):
    cats = get_categories()
    existing = {(t.category, t.subcategory) for t in session.query(Transaction).filter_by(period_id=period.id)}
    items = []
    for cat, subs in cats.items():
        if cat not in ("Bills", "Debt"): continue
        for sub in subs:
            if (cat, sub) in existing: continue
            if "Extra Credit Card" in sub:
                items.append((cat, sub, TYPICAL_AMOUNTS.get(sub, 0.0), "Every period"))
                continue
            if is_due_in_period(sub, period.start_date, period.end_date):
                items.append((cat, sub, TYPICAL_AMOUNTS.get(sub, 0.0), get_payment_type(sub)))
    return items

# ---------- Auth ----------
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "editing_id" not in st.session_state:
    st.session_state.editing_id = None

def login_screen():
    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.4, 1])
    with col2:
        st.title("💰 Paycheck Tracker")
        st.caption("Sign in to continue")
        with st.form("login"):
            u = st.text_input("Username", value="doug")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Log in", use_container_width=True, type="primary"):
                if u == "doug" and p == "change-me":
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error("Wrong username or password")

if not st.session_state.authenticated:
    login_screen()
    st.stop()

# ---------- Sidebar ----------
with st.sidebar:
    st.title("💰 Tracker")
    st.caption("doug")
    st.divider()
    page = st.radio(
        "Menu",
        ["Current Paycheck", "Add Transaction", "Past Periods", "Search", "Settings"],
        label_visibility="collapsed"
    )
    st.divider()
    if st.button("Log out", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()

CATEGORIES = get_categories()
session = SessionLocal()

try:
    # ==================== CURRENT PAYCHECK ====================
    if page == "Current Paycheck":
        period = get_current_period(session)
        if not period:
            start = date.today()
            end = start + timedelta(days=13)
            period = PaycheckPeriod(start_date=start, end_date=end,
                label=f"{start.strftime('%b %d')} – {end.strftime('%b %d')}", is_current=True)
            session.add(period)
            session.commit()
            st.rerun()

        st.header(period.label)
        st.caption(f"{period.start_date.strftime('%b %d, %Y')}  →  {period.end_date.strftime('%b %d, %Y')}")

        if st.button("➕ Create next period"):
            period.is_current = False
            ns = period.end_date + timedelta(days=1)
            length = (period.end_date - period.start_date).days
            ne = ns + timedelta(days=length)
            session.add(PaycheckPeriod(start_date=ns, end_date=ne,
                label=f"{ns.strftime('%b %d')} – {ne.strftime('%b %d')}", is_current=True))
            session.commit()
            st.rerun()

        summary = calc_summary(session, period.id)
        color = "#16a34a" if summary["leftover"] >= 0 else "#dc2626"

        st.markdown(f"""
        <div style="background:#0f172a;border-radius:12px;padding:20px 24px;margin:16px 0;border:1px solid #1e293b;">
            <div style="color:#94a3b8;font-size:0.85rem;margin-bottom:4px;">Leftover this paycheck</div>
            <div style="color:{color};font-size:2.4rem;font-weight:700;">{money(summary['leftover'])}</div>
            <div style="color:#64748b;font-size:0.8rem;margin-top:6px;">Income {money(summary['Income'])} − Outgoing {money(summary['total_out'])}</div>
        </div>
        """, unsafe_allow_html=True)

        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Income", money(summary["Income"]))
        m2.metric("Bills", money(summary["Bills"]))
        m3.metric("Debt", money(summary["Debt"]))
        m4.metric("Expenses", money(summary["Expenses"]))
        m5.metric("Savings", money(summary["Savings"]))

        st.divider()

        # Auto items
        auto = get_auto_items(session, period)
        if auto:
            with st.expander(f"📅 {len(auto)} items due this period — click to add", expanded=True):
                for i, (cat, sub, amt, ptype) in enumerate(auto):
                    c1, c2, c3, c4 = st.columns([3, 1.2, 1.4, 1])
                    c1.write(f"**{sub}**  \n{cat} · {ptype}")
                    new_amt = c2.number_input("$", value=float(amt), key=f"a{i}", label_visibility="collapsed", min_value=0.0)
                    if c3.button("Add", key=f"add{i}"):
                        status = "Paid" if ptype == "Auto-pay" else "Pending"
                        session.add(Transaction(
                            period_id=period.id, date=period.start_date, amount=new_amt,
                            category=cat, subcategory=sub, description=ptype,
                            method="Credit Card" if ptype=="Auto-pay" else "Manual", status=status
                        ))
                        session.commit()
                        st.rerun()
                if st.button("Add all", type="primary"):
                    for cat, sub, amt, ptype in auto:
                        status = "Paid" if ptype == "Auto-pay" else "Pending"
                        session.add(Transaction(
                            period_id=period.id, date=period.start_date, amount=amt,
                            category=cat, subcategory=sub, description=ptype,
                            method="Credit Card" if ptype=="Auto-pay" else "Manual", status=status
                        ))
                    session.commit()
                    st.rerun()

        # Transactions list
        st.subheader("Transactions")
        txns = session.query(Transaction).filter_by(period_id=period.id).order_by(Transaction.date.desc()).all()
        pending = [t for t in txns if t.status == "Pending"]
        paid = [t for t in txns if t.status == "Paid"]

        if pending:
            st.markdown("**🔴 Pending (need to pay)**")
            for t in pending:
                c1, c2, c3, c4, c5 = st.columns([1.2, 3, 1.5, 1, 1])
                c1.write(t.date.strftime("%b %d"))
                c2.write(f"**{t.subcategory}**")
                c3.write(money(t.amount))
                if c4.button("Paid", key=f"p{t.id}"):
                    t.status = "Paid"
                    session.commit()
                    st.rerun()
                if c5.button("Edit", key=f"e{t.id}"):
                    st.session_state.editing_id = t.id
                    st.rerun()

        if paid:
            st.markdown("**✅ Paid**")
            for t in paid:
                c1, c2, c3, c4 = st.columns([1.2, 3, 1.5, 1])
                c1.write(t.date.strftime("%b %d"))
                c2.write(f"**{t.subcategory}**")
                c3.write(money(t.amount))
                if c4.button("Edit", key=f"ep{t.id}"):
                    st.session_state.editing_id = t.id
                    st.rerun()

        if not txns:
            st.info("No transactions yet. Use the sidebar → **Add Transaction** or add the due items above.")

        # Edit form
        if st.session_state.editing_id:
            t = session.query(Transaction).get(st.session_state.editing_id)
            if t:
                st.divider()
                st.subheader("Edit Transaction")
                with st.form("edit"):
                    nd = st.date_input("Date", value=t.date)
                    nc = st.selectbox("Category", list(CATEGORIES.keys()), index=list(CATEGORIES.keys()).index(t.category) if t.category in CATEGORIES else 0)
                    ns = st.selectbox("Subcategory", CATEGORIES[nc], index=CATEGORIES[nc].index(t.subcategory) if t.subcategory in CATEGORIES[nc] else 0)
                    na = st.number_input("Amount", value=float(t.amount), min_value=0.0, step=0.01)
                    nst = st.selectbox("Status", ["Pending", "Paid"], index=0 if t.status=="Pending" else 1)
                    ndesc = st.text_input("Description", value=t.description or "")
                    b1, b2, b3 = st.columns(3)
                    if b1.form_submit_button("Save", type="primary"):
                        t.date, t.category, t.subcategory, t.amount, t.status, t.description = nd, nc, ns, na, nst, ndesc
                        session.commit()
                        st.session_state.editing_id = None
                        st.rerun()
                    if b2.form_submit_button("Cancel"):
                        st.session_state.editing_id = None
                        st.rerun()
                    if b3.form_submit_button("Delete"):
                        session.delete(t)
                        session.commit()
                        st.session_state.editing_id = None
                        st.rerun()

    # ==================== ADD TRANSACTION ====================
    elif page == "Add Transaction":
        period = get_current_period(session)
        st.header("Add Transaction")
        st.caption(f"Adding to period: **{period.label}**")

        with st.form("add_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                txn_date = st.date_input("Date", value=date.today())
                category = st.selectbox("Category", list(CATEGORIES.keys()))
            with c2:
                amount = st.number_input("Amount", min_value=0.0, step=0.01, format="%.2f")
                subcategory = st.selectbox("Subcategory", CATEGORIES[category])

            description = st.text_input("Description (optional)")
            method = st.selectbox("Payment method", ["Credit Card", "Auto-pay", "Manual / Bank", "Cash", "Other"])
            status = st.selectbox("Status", ["Pending", "Paid"])

            submitted = st.form_submit_button("Save Transaction", type="primary", use_container_width=True)
            if submitted:
                if amount <= 0:
                    st.error("Amount must be greater than zero")
                else:
                    session.add(Transaction(
                        period_id=period.id, date=txn_date, amount=amount,
                        category=category, subcategory=subcategory,
                        description=description, method=method, status=status
                    ))
                    session.commit()
                    st.success(f"Saved {money(amount)} — {subcategory}")
                    st.balloons()

        st.divider()
        st.subheader("Add a custom item to the lists")
        with st.form("custom"):
            custom_cat = st.selectbox("Category", list(CATEGORIES.keys()))
            custom_name = st.text_input("New item name", placeholder="e.g. Vet bill, New subscription")
            if st.form_submit_button("Add to dropdowns"):
                if custom_name.strip():
                    exists = session.query(CustomSubcategory).filter_by(category=custom_cat, name=custom_name.strip()).first()
                    if not exists:
                        session.add(CustomSubcategory(category=custom_cat, name=custom_name.strip()))
                        session.commit()
                        st.success(f"Added **{custom_name}** under {custom_cat}")
                        st.rerun()
                    else:
                        st.warning("Already exists")
                else:
                    st.error("Enter a name")

    # ==================== PAST PERIODS ====================
    elif page == "Past Periods":
        st.header("Past Periods")
        periods = session.query(PaycheckPeriod).order_by(PaycheckPeriod.start_date.desc()).all()
        if not periods:
            st.info("No periods yet")
        else:
            opts = {f"{p.label} {'(current)' if p.is_current else ''}": p.id for p in periods}
            choice = st.selectbox("Select period", list(opts.keys()))
            pid = opts[choice]
            summary = calc_summary(session, pid)

            color = "#16a34a" if summary["leftover"] >= 0 else "#dc2626"
            st.markdown(f"""
            <div style="background:#0f172a;border-radius:12px;padding:18px 22px;margin:12px 0;border:1px solid #1e293b;">
                <div style="color:#94a3b8;font-size:0.85rem;">Leftover</div>
                <div style="color:{color};font-size:2.2rem;font-weight:700;">{money(summary['leftover'])}</div>
            </div>
            """, unsafe_allow_html=True)

            c1,c2,c3,c4 = st.columns(4)
            c1.metric("Income", money(summary["Income"]))
            c2.metric("Bills+Debt", money(summary["Bills"]+summary["Debt"]))
            c3.metric("Expenses", money(summary["Expenses"]))
            c4.metric("Savings", money(summary["Savings"]))

            txns = session.query(Transaction).filter_by(period_id=pid).order_by(Transaction.date.desc()).all()
            if txns:
                df = pd.DataFrame([{"Date":t.date,"Category":t.category,"Subcategory":t.subcategory,"Amount":t.amount,"Status":t.status} for t in txns])
                st.dataframe(df, use_container_width=True, hide_index=True)
            else:
                st.caption("No transactions")

    # ==================== SEARCH ====================
    elif page == "Search":
        st.header("Search")
        search = st.text_input("Search subcategory / description / category")
        cat_filter = st.selectbox("Category filter", ["All"] + list(CATEGORIES.keys()))

        q = session.query(Transaction)
        if search:
            like = f"%{search}%"
            q = q.filter((Transaction.subcategory.ilike(like)) | (Transaction.description.ilike(like)) | (Transaction.category.ilike(like)))
        if cat_filter != "All":
            q = q.filter_by(category=cat_filter)

        results = q.order_by(Transaction.date.desc()).limit(300).all()
        if results:
            df = pd.DataFrame([{"Date":t.date,"Category":t.category,"Subcategory":t.subcategory,"Amount":t.amount,"Status":t.status} for t in results])
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.caption(f"{len(results)} results")
        else:
            st.info("No matches")

    # ==================== SETTINGS ====================
    elif page == "Settings":
        st.header("Settings")
        st.write("Login: `doug` / `change-me`")
        st.divider()
        customs = session.query(CustomSubcategory).all()
        if customs:
            st.subheader("Custom items")
            for c in customs:
                st.write(f"{c.category} → {c.name}")
        else:
            st.caption("No custom items yet")
        st.divider()
        st.caption("Data is stored in your Neon database and survives restarts.")

finally:
    session.close()
