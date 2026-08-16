import streamlit as st
from datetime import date, timedelta
import pandas as pd
import re

st.set_page_config(
    page_title="Paycheck Tracker",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------- Simple in-memory storage ----------
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "periods" not in st.session_state:
    st.session_state.periods = []
if "transactions" not in st.session_state:
    st.session_state.transactions = []
if "current_period_id" not in st.session_state:
    st.session_state.current_period_id = None
if "editing_idx" not in st.session_state:
    st.session_state.editing_idx = None
if "custom_subs" not in st.session_state:
    st.session_state.custom_subs = {  # category -> list of extra subcategory names
        "Income": [],
        "Savings": [],
        "Bills": [],
        "Expenses": [],
        "Debt": []
    }

# Seed a starting period if none exists
if not st.session_state.periods:
    start = date(2026, 8, 14)
    end = date(2026, 8, 27)
    st.session_state.periods.append({
        "id": 1,
        "start": start,
        "end": end,
        "label": f"{start.strftime('%b %d')} – {end.strftime('%b %d')}",
        "is_current": True
    })
    st.session_state.current_period_id = 1

# ---------- Base categories from your spreadsheet ----------
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

def get_categories():
    """Return full category dict including any custom subcategories the user has added."""
    cats = {}
    for cat, subs in BASE_CATEGORIES.items():
        cats[cat] = subs + st.session_state.custom_subs.get(cat, [])
    return cats

TYPICAL_AMOUNTS = {
    "Doug Paycheck": 3639.45,
    "Amanda Paycheck": 1295.65,
    "Child Support (MT)": 680.00,
    "iCloud (1st) (AP)": 9.99,
    "Spotify (5th) (AP)": 16.99,
    "Netflix (5th) (AP)": 19.99,
    "Cell Phone (9th) (AP)": 425.00,
    "OnStar (11th) (AP)": 14.99,
    "REMC Fiber (12th) (AP)": 80.44,
    "Microsoft (12th) (AP)": 21.39,
    "Nest (16th) (AP)": 15.00,
    "Sallie Mae (16th) (BP)": 40.00,
    "REMC (17th) (AP)": 150.00,
    "Beach Body (17th) (AP)": 15.95,
    "Life 360 (17th) (AP)": 16.04,
    "Hulu (19th) (AP)": 19.95,
    "Sewage (22nd) (AP)": 71.00,
    "Insurance (23rd) (AP)": 246.19,
    "Amazon CC (23rd) (BP)": 200.00,
    "Youtube TV (23rd) (AP)": 120.00,
    "Water (26th) (AP)": 85.00,
    "NIPSCO (26th) (BP)": 47.00,
    "Peacock (28th) (AP)": 11.99,
    "Spotify (29th) (AP)": 19.99,
    "Mortgage (1st) (BP)": 2206.90,
    "Windows (5th) (BP)": 301.46,
    "Ravi (7th) (MT)": 709.27,
    "Truck (15th) (MT)": 659.29,
    "Extra Credit Card (BP) (MT)": 0.0,
}

def money(amount):
    return f"${amount:,.2f}"

def get_current_period():
    for p in st.session_state.periods:
        if p["is_current"]:
            return p
    return None

def extract_due_day(name: str):
    match = re.search(r"\((\d{1,2})(?:st|nd|rd|th)?\)", name)
    if match:
        return int(match.group(1))
    return None

def get_payment_type(name: str) -> str:
    if "Extra Credit Card" in name:
        return "Every period"
    if "(AP)" in name:
        return "Auto-pay"
    if "(BP)" in name or "(MT)" in name:
        return "Manual"
    return "Manual"

def is_due_in_period(name: str, period_start: date, period_end: date) -> bool:
    day = extract_due_day(name)
    if day is None:
        return False
    current = period_start
    while current <= period_end:
        if current.day == day:
            return True
        current += timedelta(days=1)
    return False

def calculate_summary(period_id):
    totals = {"Income": 0.0, "Savings": 0.0, "Bills": 0.0, "Expenses": 0.0, "Debt": 0.0}
    for t in st.session_state.transactions:
        if t["period_id"] == period_id:
            totals[t["category"]] += t["amount"]
    leftover = totals["Income"] - totals["Bills"] - totals["Debt"] - totals["Expenses"] - totals["Savings"]
    return {**totals, "leftover": leftover, "total_out": totals["Bills"] + totals["Debt"] + totals["Expenses"] + totals["Savings"]}

def get_auto_items_for_period(period):
    cats = get_categories()
    existing = {(t["category"], t["subcategory"]) for t in st.session_state.transactions if t["period_id"] == period["id"]}
    items = []

    for cat, subs in cats.items():
        if cat not in ("Bills", "Debt"):
            continue
        for sub in subs:
            if (cat, sub) in existing:
                continue

            if "Extra Credit Card" in sub:
                items.append((cat, sub, TYPICAL_AMOUNTS.get(sub, 0.0), "Every period"))
                continue

            if is_due_in_period(sub, period["start"], period["end"]):
                ptype = get_payment_type(sub)
                items.append((cat, sub, TYPICAL_AMOUNTS.get(sub, 0.0), ptype))

    return items

# ---------- Login ----------
def login_screen():
    st.title("💰 Paycheck Tracker")
    st.markdown("### Sign in")
    with st.form("login_form"):
        username = st.text_input("Username", value="doug")
        password = st.text_input("Password", type="password")
        if st.form_submit_button("Log in", use_container_width=True):
            if username == "doug" and password == "change-me":
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Invalid username or password")

if not st.session_state.authenticated:
    login_screen()
    st.stop()

# ---------- Sidebar ----------
with st.sidebar:
    st.title("💰 Paycheck Tracker")
    st.caption("Signed in as **doug**")
    st.divider()
    page = st.radio("Navigate", ["Current Paycheck", "Add Transaction", "Past Periods", "Search", "Settings"], label_visibility="collapsed")
    st.divider()
    if st.button("Log out", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()

CATEGORIES = get_categories()

# ---------- Current Paycheck ----------
if page == "Current Paycheck":
    period = get_current_period()
    st.header("Current Paycheck")
    st.subheader(period["label"])
    st.caption(f"{period['start'].strftime('%b %d, %Y')} → {period['end'].strftime('%b %d, %Y')}")

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("➕ Create next period", use_container_width=True):
            last = period
            new_start = last["end"] + timedelta(days=1)
            length = (last["end"] - last["start"]).days
            new_end = new_start + timedelta(days=length)
            new_id = max([p["id"] for p in st.session_state.periods]) + 1
            for p in st.session_state.periods:
                p["is_current"] = False
            st.session_state.periods.append({
                "id": new_id,
                "start": new_start,
                "end": new_end,
                "label": f"{new_start.strftime('%b %d')} – {new_end.strftime('%b %d')}",
                "is_current": True
            })
            st.session_state.current_period_id = new_id
            st.rerun()

    summary = calculate_summary(period["id"])

    color = "#0f9d58" if summary["leftover"] >= 0 else "#d93025"
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#1a1a2e,#16213e);border-radius:16px;padding:24px 28px;margin:20px 0;border:1px solid #2a2a4a;">
        <div style="color:#aaa;font-size:0.9rem;">Leftover this paycheck</div>
        <div style="color:{color};font-size:2.6rem;font-weight:700;">{money(summary['leftover'])}</div>
        <div style="color:#888;font-size:0.85rem;margin-top:8px;">Income {money(summary['Income'])} − Outgoing {money(summary['total_out'])}</div>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Income", money(summary["Income"]))
    c2.metric("Bills", money(summary["Bills"]))
    c3.metric("Debt", money(summary["Debt"]))
    c4.metric("Expenses", money(summary["Expenses"]))
    c5.metric("Savings", money(summary["Savings"]))

    st.divider()

    # Auto-populate section
    auto_items = get_auto_items_for_period(period)
    if auto_items:
        st.subheader("📅 Items for this period")
        st.caption("AP = Auto-pay · BP/MT = Manual · Extra Credit Card always appears")

        for i, (cat, sub, amt, ptype) in enumerate(auto_items):
            cols = st.columns([3.2, 1.3, 1.5, 1])
            cols[0].write(f"**{sub}**  \n{cat}")
            cols[1].write(ptype)
            new_amt = cols[2].number_input("Amount", value=float(amt), key=f"auto_{i}", label_visibility="collapsed", min_value=0.0)
            if cols[3].button("Add", key=f"add_auto_{i}"):
                status = "Paid" if ptype == "Auto-pay" else "Pending"
                st.session_state.transactions.append({
                    "period_id": period["id"],
                    "date": period["start"],
                    "amount": new_amt,
                    "category": cat,
                    "subcategory": sub,
                    "description": ptype,
                    "method": "Credit Card" if ptype == "Auto-pay" else "Manual",
                    "status": status
                })
                st.rerun()

        if st.button("➕ Add all listed items", type="primary"):
            for cat, sub, amt, ptype in auto_items:
                status = "Paid" if ptype == "Auto-pay" else "Pending"
                st.session_state.transactions.append({
                    "period_id": period["id"],
                    "date": period["start"],
                    "amount": amt,
                    "category": cat,
                    "subcategory": sub,
                    "description": ptype,
                    "method": "Credit Card" if ptype == "Auto-pay" else "Manual",
                    "status": status
                })
            st.rerun()

    st.divider()

    # Transactions with status + edit
    st.subheader("Transactions this period")
    period_txns = [(i, t) for i, t in enumerate(st.session_state.transactions) if t["period_id"] == period["id"]]

    pending = [(i, t) for i, t in period_txns if t.get("status") == "Pending"]
    paid = [(i, t) for i, t in period_txns if t.get("status") == "Paid"]

    if pending:
        st.markdown("#### 🔴 Still need to pay (Pending)")
        for idx, (orig_idx, t) in enumerate(pending):
            cols = st.columns([1.3, 2.8, 1.3, 1.2, 1, 1])
            cols[0].write(t["date"].strftime("%b %d"))
            cols[1].write(f"**{t['subcategory']}**")
            cols[2].write(t["category"])
            cols[3].write(money(t["amount"]))
            if cols[4].button("Paid", key=f"paid_{orig_idx}"):
                st.session_state.transactions[orig_idx]["status"] = "Paid"
                st.rerun()
            if cols[5].button("Edit", key=f"edit_p_{orig_idx}"):
                st.session_state.editing_idx = orig_idx
                st.rerun()

    if paid:
        st.markdown("#### ✅ Paid")
        for idx, (orig_idx, t) in enumerate(paid):
            cols = st.columns([1.3, 2.8, 1.3, 1.2, 1])
            cols[0].write(t["date"].strftime("%b %d"))
            cols[1].write(f"**{t['subcategory']}**")
            cols[2].write(t["category"])
            cols[3].write(money(t["amount"]))
            if cols[4].button("Edit", key=f"edit_paid_{orig_idx}"):
                st.session_state.editing_idx = orig_idx
                st.rerun()

    if not period_txns:
        st.info("No transactions yet.")

    # Edit form
    if st.session_state.editing_idx is not None:
        t = st.session_state.transactions[st.session_state.editing_idx]
        st.divider()
        st.subheader("✏️ Edit Transaction")
        with st.form("edit_form"):
            new_date = st.date_input("Date", value=t["date"])
            new_category = st.selectbox("Category", list(CATEGORIES.keys()), index=list(CATEGORIES.keys()).index(t["category"]))
            sub_options = CATEGORIES[new_category]
            sub_index = sub_options.index(t["subcategory"]) if t["subcategory"] in sub_options else 0
            new_sub = st.selectbox("Subcategory", sub_options, index=sub_index)
            new_amount = st.number_input("Amount", value=float(t["amount"]), min_value=0.0, step=0.01)
            new_status = st.selectbox("Status", ["Pending", "Paid"], index=0 if t.get("status") == "Pending" else 1)
            new_desc = st.text_input("Description", value=t.get("description", ""))

            c1, c2, c3 = st.columns(3)
            if c1.form_submit_button("Save changes", type="primary"):
                st.session_state.transactions[st.session_state.editing_idx].update({
                    "date": new_date,
                    "category": new_category,
                    "subcategory": new_sub,
                    "amount": new_amount,
                    "status": new_status,
                    "description": new_desc
                })
                st.session_state.editing_idx = None
                st.rerun()
            if c2.form_submit_button("Cancel"):
                st.session_state.editing_idx = None
                st.rerun()
            if c3.form_submit_button("Delete", type="secondary"):
                st.session_state.transactions.pop(st.session_state.editing_idx)
                st.session_state.editing_idx = None
                st.rerun()

# ---------- Add Transaction ----------
elif page == "Add Transaction":
    st.header("Add Transaction")
    period = get_current_period()
    st.caption(f"Adding to: **{period['label']}**")

    with st.form("add_txn", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            txn_date = st.date_input("Date", value=date.today())
            category = st.selectbox("Category", list(CATEGORIES.keys()))
        with col2:
            amount = st.number_input("Amount", min_value=0.0, step=0.01, format="%.2f")
            subcategory = st.selectbox("Subcategory", CATEGORIES[category])

        description = st.text_input("Description (optional)")
        method = st.selectbox("Payment method", ["Credit Card", "Auto-pay", "Manual / Bank", "Cash", "Other"])
        status = st.selectbox("Status", ["Pending", "Paid"], index=0)

        if st.form_submit_button("Save Transaction", type="primary", use_container_width=True):
            if amount <= 0:
                st.error("Amount must be greater than zero")
            else:
                st.session_state.transactions.append({
                    "period_id": period["id"],
                    "date": txn_date,
                    "amount": amount,
                    "category": category,
                    "subcategory": subcategory,
                    "description": description,
                    "method": method,
                    "status": status
                })
                st.success(f"Saved {money(amount)} — {subcategory}")
                st.balloons()

    st.divider()
    st.subheader("➕ Add a new custom item")
    st.caption("Use this when you have a new bill, expense, or anything not already in the lists.")

    with st.form("add_custom"):
        custom_cat = st.selectbox("Category for new item", list(CATEGORIES.keys()), key="custom_cat")
        custom_name = st.text_input("Name of the new item", placeholder="e.g. New subscription, Vet bill, etc.")
        if st.form_submit_button("Add to list"):
            if custom_name.strip():
                if custom_name.strip() not in st.session_state.custom_subs[custom_cat]:
                    st.session_state.custom_subs[custom_cat].append(custom_name.strip())
                    st.success(f"Added **{custom_name}** under {custom_cat}. It will now appear in the dropdowns.")
                    st.rerun()
                else:
                    st.warning("That item already exists.")
            else:
                st.error("Please enter a name.")

# ---------- Past Periods ----------
elif page == "Past Periods":
    st.header("Past Paycheck Periods")
    options = {f"{p['label']} {'(current)' if p['is_current'] else ''}": p["id"] for p in st.session_state.periods}
    choice = st.selectbox("Select period", list(options.keys()))
    pid = options[choice]
    summary = calculate_summary(pid)

    color = "#0f9d58" if summary["leftover"] >= 0 else "#d93025"
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#1a1a2e,#16213e);border-radius:16px;padding:24px 28px;margin:20px 0;border:1px solid #2a2a4a;">
        <div style="color:#aaa;font-size:0.9rem;">Leftover</div>
        <div style="color:{color};font-size:2.4rem;font-weight:700;">{money(summary['leftover'])}</div>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Income", money(summary["Income"]))
    c2.metric("Bills + Debt", money(summary["Bills"] + summary["Debt"]))
    c3.metric("Expenses", money(summary["Expenses"]))
    c4.metric("Savings", money(summary["Savings"]))

    st.subheader("Transactions")
    txns = [t for t in st.session_state.transactions if t["period_id"] == pid]
    if txns:
        df = pd.DataFrame([{
            "Date": t["date"],
            "Category": t["category"],
            "Subcategory": t["subcategory"],
            "Amount": t["amount"],
            "Status": t.get("status", ""),
            "Method": t.get("method", "")
        } for t in txns])
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.caption("No transactions in this period.")

# ---------- Search ----------
elif page == "Search":
    st.header("Search Transactions")
    search = st.text_input("Search (subcategory, description, category)")
    cat_filter = st.selectbox("Category", ["All"] + list(CATEGORIES.keys()))

    results = st.session_state.transactions
    if search:
        results = [t for t in results if search.lower() in t["subcategory"].lower() or search.lower() in (t.get("description") or "").lower() or search.lower() in t["category"].lower()]
    if cat_filter != "All":
        results = [t for t in results if t["category"] == cat_filter]

    if results:
        df = pd.DataFrame([{
            "Date": t["date"],
            "Category": t["category"],
            "Subcategory": t["subcategory"],
            "Amount": t["amount"],
            "Status": t.get("status", ""),
            "Method": t.get("method", "")
        } for t in results])
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.caption(f"{len(results)} results")
    else:
        st.info("No matching transactions.")

# ---------- Settings ----------
elif page == "Settings":
    st.header("Settings")
    st.write("**Default login**:")
    st.code("Username: doug\nPassword: change-me")
    st.divider()

    st.subheader("Custom items you have added")
    has_custom = False
    for cat, subs in st.session_state.custom_subs.items():
        if subs:
            has_custom = True
            st.write(f"**{cat}**: {', '.join(subs)}")
    if not has_custom:
        st.caption("None yet. Add them on the Add Transaction page.")

    st.divider()
    st.markdown("""
    **Paycheck Tracker**  
    - **(AP)** = Auto-pay → starts as Paid  
    - **(BP)** or **(MT)** = Manual → starts as Pending  
    - **Extra Credit Card** always appears every period  
    - Use **Add a new custom item** on the Add Transaction page for anything not in the lists  
    - Click **Edit** on any transaction to change or delete it  
    
    Next: Gmail monitoring to auto-mark payments as Paid.
    """)
