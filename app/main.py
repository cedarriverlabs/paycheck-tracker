"""
Paycheck Tracker – personal finance app focused on paycheck-to-paycheck leftover.
"""

import sys
from pathlib import Path

# Ensure the app/ directory is on the path (needed on Streamlit Cloud)
APP_DIR = Path(__file__).resolve().parent
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import streamlit as st
from datetime import date, datetime
from typing import Optional

from database import init_db
from auth import authenticate, change_password
from seed import run_seed
from services import (
    get_current_period, get_all_periods, get_period_by_id,
    create_next_period, update_period_dates,
    get_subcategories, get_category_list,
    add_transaction, get_transactions, delete_transaction,
    calculate_period_summary, get_recurring_suggestions, preload_recurring,
)


# ---------- Page config ----------
st.set_page_config(
    page_title="Paycheck Tracker",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ---------- Auth ----------
def login_screen():
    st.title("💰 Paycheck Tracker")
    st.markdown("### Sign in")

    with st.form("login_form"):
        username = st.text_input("Username", value="doug")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Log in", use_container_width=True)

        if submitted:
            if authenticate(username, password):
                st.session_state["authenticated"] = True
                st.session_state["username"] = username
                st.rerun()
            else:
                st.error("Invalid username or password.")


def require_auth():
    if not st.session_state.get("authenticated"):
        login_screen()
        st.stop()


# ---------- Helpers ----------
def money(amount: float) -> str:
    return f"${amount:,.2f}"


def show_leftover_card(summary: dict):
    leftover = summary["leftover"]
    color = "#0f9d58" if leftover >= 0 else "#d93025"
    st.markdown(
        f"""
        <div style="
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            border-radius: 16px;
            padding: 24px 28px;
            margin-bottom: 20px;
            border: 1px solid #2a2a4a;
        ">
            <div style="color:#aaa;font-size:0.9rem;margin-bottom:4px;">Leftover this paycheck</div>
            <div style="color:{color};font-size:2.6rem;font-weight:700;letter-spacing:-1px;">
                {money(leftover)}
            </div>
            <div style="color:#888;font-size:0.85rem;margin-top:8px;">
                Income {money(summary['Income'])} − Outgoing {money(summary['total_out'])}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------- Pages ----------
def page_current_paycheck():
    st.header("Current Paycheck")

    period = get_current_period()
    if not period:
        st.warning("No current paycheck period found.")
        if st.button("Create first period"):
            create_next_period()
            st.rerun()
        return

    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.subheader(period.label)
        st.caption(f"{period.start_date.strftime('%b %d, %Y')} → {period.end_date.strftime('%b %d, %Y')}")
    with col2:
        if st.button("➕ Create next period", use_container_width=True):
            new_p = create_next_period(period)
            st.success(f"Created {new_p.label}")
            st.rerun()
    with col3:
        with st.expander("Edit dates"):
            new_start = st.date_input("Start", value=period.start_date, key="edit_start")
            new_end = st.date_input("End", value=period.end_date, key="edit_end")
            if st.button("Save dates"):
                update_period_dates(period.id, new_start, new_end)
                st.rerun()

    summary = calculate_period_summary(period.id)
    show_leftover_card(summary)

    # Summary breakdown
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Income", money(summary["Income"]))
    c2.metric("Bills", money(summary["Bills"]))
    c3.metric("Debt", money(summary["Debt"]))
    c4.metric("Expenses", money(summary["Expenses"]))
    c5.metric("Savings", money(summary["Savings"]))

    st.divider()

    # Recurring suggestions
    suggestions = get_recurring_suggestions(period)
    if suggestions:
        with st.expander(f"💡 Suggested recurring items ({len(suggestions)}) — click to pre-load", expanded=False):
            st.caption("These are items you usually pay that haven’t been recorded yet this period.")
            selected = []
            for i, s in enumerate(suggestions):
                cols = st.columns([3, 2, 1])
                with cols[0]:
                    st.write(f"**{s['subcategory']}**  \n{s['category']} · {s.get('due_info') or ''}")
                with cols[1]:
                    default_amt = s["typical_amount"] or 0.0
                    amt = st.number_input(
                        "Amount",
                        min_value=0.0,
                        value=float(default_amt),
                        step=1.0,
                        key=f"sug_amt_{i}",
                        label_visibility="collapsed",
                    )
                with cols[2]:
                    if st.checkbox("Add", key=f"sug_chk_{i}"):
                        selected.append({
                            "category": s["category"],
                            "subcategory": s["subcategory"],
                            "amount": amt,
                            "typical_amount": s["typical_amount"],
                        })
            if selected and st.button("Pre-load selected", type="primary"):
                n = preload_recurring(period.id, selected)
                st.success(f"Added {n} recurring items.")
                st.rerun()

    # Recent transactions for this period
    st.subheader("Transactions this period")
    txns = get_transactions(period_id=period.id)
    if not txns:
        st.info("No transactions yet. Add one below or pre-load recurrings above.")
    else:
        for t in txns:
            cols = st.columns([1.5, 2, 2, 1.2, 0.5])
            cols[0].write(t.date.strftime("%b %d"))
            cols[1].write(f"**{t.subcategory}**")
            cols[2].write(t.category)
            color = "#0f9d58" if t.category == "Income" else "#e8eaed"
            cols[3].markdown(f"<span style='color:{color}'>{money(t.amount)}</span>", unsafe_allow_html=True)
            if cols[4].button("🗑", key=f"del_{t.id}"):
                delete_transaction(t.id)
                st.rerun()


def page_add_transaction():
    st.header("Add Transaction")

    period = get_current_period()
    if not period:
        st.warning("Create a current paycheck period first.")
        return

    st.caption(f"Adding to: **{period.label}**")

    categories = get_category_list()
    all_subs = get_subcategories()

    with st.form("add_txn", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            txn_date = st.date_input("Date", value=date.today())
            category = st.selectbox("Category", categories)
        with col2:
            amount = st.number_input("Amount", min_value=0.0, step=0.01, format="%.2f")
            # Filter subcategories by chosen category
            subs_for_cat = [s.name for s in all_subs if s.category == category]
            if not subs_for_cat:
                subs_for_cat = ["(none)"]
            subcategory = st.selectbox("Subcategory", subs_for_cat)

        description = st.text_input("Description (optional)")
        payment_method = st.selectbox(
            "Payment method",
            ["Credit Card", "Auto-pay", "Manual / Bank", "Cash", "Other"],
        )

        submitted = st.form_submit_button("Save Transaction", type="primary", use_container_width=True)

        if submitted:
            if amount <= 0:
                st.error("Amount must be greater than zero.")
            else:
                add_transaction(
                    period_id=period.id,
                    txn_date=txn_date,
                    amount=amount,
                    category=category,
                    subcategory=subcategory,
                    description=description,
                    payment_method=payment_method,
                )
                st.success(f"Saved {money(amount)} — {subcategory}")
                st.balloons()


def page_history():
    st.header("Past Paycheck Periods")

    periods = get_all_periods()
    if not periods:
        st.info("No periods yet.")
        return

    # Selector
    options = {f"{p.label} {'(current)' if p.is_current else ''}": p.id for p in periods}
    choice = st.selectbox("Select period", list(options.keys()))
    period_id = options[choice]
    period = get_period_by_id(period_id)

    summary = calculate_period_summary(period_id)
    show_leftover_card(summary)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Income", money(summary["Income"]))
    c2.metric("Bills + Debt", money(summary["Bills"] + summary["Debt"]))
    c3.metric("Expenses", money(summary["Expenses"]))
    c4.metric("Savings", money(summary["Savings"]))

    st.subheader("Transactions")
    txns = get_transactions(period_id=period_id)
    if txns:
        import pandas as pd
        df = pd.DataFrame([
            {
                "Date": t.date,
                "Category": t.category,
                "Subcategory": t.subcategory,
                "Amount": t.amount,
                "Description": t.description or "",
                "Method": t.payment_method or "",
            }
            for t in txns
        ])
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.caption("No transactions in this period.")


def page_search():
    st.header("Search & Filter Transactions")

    col1, col2 = st.columns(2)
    with col1:
        search = st.text_input("Search (subcategory, description, category)")
    with col2:
        cat_filter = st.selectbox("Category filter", ["All"] + get_category_list())

    category = None if cat_filter == "All" else cat_filter
    txns = get_transactions(search=search or None, category=category, limit=300)

    if not txns:
        st.info("No matching transactions.")
        return

    import pandas as pd
    df = pd.DataFrame([
        {
            "Date": t.date,
            "Period ID": t.period_id,
            "Category": t.category,
            "Subcategory": t.subcategory,
            "Amount": t.amount,
            "Description": t.description or "",
            "Method": t.payment_method or "",
        }
        for t in txns
    ])
    st.dataframe(df, use_container_width=True, hide_index=True)
    st.caption(f"{len(txns)} results")


def page_settings():
    st.header("Settings")

    st.subheader("Change password")
    with st.form("pw_form"):
        new_pw = st.text_input("New password", type="password")
        confirm = st.text_input("Confirm new password", type="password")
        if st.form_submit_button("Update password"):
            if new_pw != confirm:
                st.error("Passwords do not match.")
            elif len(new_pw) < 6:
                st.error("Password should be at least 6 characters.")
            else:
                if change_password(st.session_state["username"], new_pw):
                    st.success("Password updated.")
                else:
                    st.error("Could not update password.")

    st.divider()
    st.subheader("About")
    st.markdown(
        """
        **Paycheck Tracker**  
        Built for paycheck-to-paycheck tracking.  
        Focus: clear leftover after bills each pay period.
        """
    )


# ---------- Main ----------
def main():
    init_db()  # ensure tables exist

    # Seed on first run if no user exists yet
    from database import get_session, User
    session = get_session()
    try:
        if session.query(User).count() == 0:
            run_seed()
    finally:
        session.close()

    # Session state defaults
    if "authenticated" not in st.session_state:
        st.session_state["authenticated"] = False

    require_auth()

    # Sidebar navigation
    with st.sidebar:
        st.title("💰 Paycheck Tracker")
        st.caption(f"Signed in as **{st.session_state.get('username')}**")
        st.divider()

        page = st.radio(
            "Navigate",
            [
                "Current Paycheck",
                "Add Transaction",
                "Past Periods",
                "Search",
                "Settings",
            ],
            label_visibility="collapsed",
        )

        st.divider()
        if st.button("Log out", use_container_width=True):
            st.session_state["authenticated"] = False
            st.session_state.pop("username", None)
            st.rerun()

    # Route
    if page == "Current Paycheck":
        page_current_paycheck()
    elif page == "Add Transaction":
        page_add_transaction()
    elif page == "Past Periods":
        page_history()
    elif page == "Search":
        page_search()
    elif page == "Settings":
        page_settings()


if __name__ == "__main__":
    main()
