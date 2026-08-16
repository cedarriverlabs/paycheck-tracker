"""
Business logic: periods, transactions, leftover calculation, recurring suggestions.
"""

from datetime import date, timedelta
from typing import List, Optional, Dict, Tuple
from sqlalchemy import func

from database import (
    get_session, PaycheckPeriod, Transaction, Subcategory
)


def get_current_period() -> Optional[PaycheckPeriod]:
    session = get_session()
    try:
        return session.query(PaycheckPeriod).filter_by(is_current=True).first()
    finally:
        session.close()


def get_all_periods() -> List[PaycheckPeriod]:
    session = get_session()
    try:
        return (
            session.query(PaycheckPeriod)
            .order_by(PaycheckPeriod.start_date.desc())
            .all()
        )
    finally:
        session.close()


def get_period_by_id(period_id: int) -> Optional[PaycheckPeriod]:
    session = get_session()
    try:
        return session.query(PaycheckPeriod).get(period_id)
    finally:
        session.close()


def create_next_period(from_period: Optional[PaycheckPeriod] = None) -> PaycheckPeriod:
    """
    Create the next paycheck period.
    Assumes roughly bi-weekly (14 days). User can edit dates afterward.
    """
    session = get_session()
    try:
        # Mark previous current as not current
        current = session.query(PaycheckPeriod).filter_by(is_current=True).first()
        if current:
            current.is_current = False

        if from_period is None:
            from_period = current

        if from_period:
            # Next period starts the day after the previous ends
            new_start = from_period.end_date + timedelta(days=1)
            # Keep same length as previous period
            length = (from_period.end_date - from_period.start_date).days
            new_end = new_start + timedelta(days=length)
        else:
            # Fallback
            new_start = date.today()
            new_end = new_start + timedelta(days=13)

        period = PaycheckPeriod(
            start_date=new_start,
            end_date=new_end,
            label=f"{new_start.strftime('%b %d')} – {new_end.strftime('%b %d')}",
            is_current=True,
        )
        session.add(period)
        session.commit()
        session.refresh(period)
        return period
    finally:
        session.close()


def update_period_dates(period_id: int, start: date, end: date) -> bool:
    session = get_session()
    try:
        period = session.query(PaycheckPeriod).get(period_id)
        if not period:
            return False
        period.start_date = start
        period.end_date = end
        period.label = f"{start.strftime('%b %d')} – {end.strftime('%b %d')}"
        session.commit()
        return True
    finally:
        session.close()


def get_subcategories(category: Optional[str] = None) -> List[Subcategory]:
    session = get_session()
    try:
        q = session.query(Subcategory).filter_by(active=True)
        if category:
            q = q.filter_by(category=category)
        return q.order_by(Subcategory.category, Subcategory.name).all()
    finally:
        session.close()


def get_category_list() -> List[str]:
    return ["Income", "Savings", "Bills", "Expenses", "Debt"]


def add_transaction(
    period_id: int,
    txn_date: date,
    amount: float,
    category: str,
    subcategory: str,
    description: str = "",
    is_suggested: bool = False,
    payment_method: str = None,
) -> Transaction:
    session = get_session()
    try:
        txn = Transaction(
            period_id=period_id,
            date=txn_date,
            amount=amount,
            category=category,
            subcategory=subcategory,
            description=description or None,
            is_suggested=is_suggested,
            payment_method=payment_method,
        )
        session.add(txn)
        session.commit()
        session.refresh(txn)
        return txn
    finally:
        session.close()


def get_transactions(
    period_id: Optional[int] = None,
    search: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 500,
) -> List[Transaction]:
    session = get_session()
    try:
        q = session.query(Transaction)
        if period_id:
            q = q.filter_by(period_id=period_id)
        if category:
            q = q.filter_by(category=category)
        if search:
            like = f"%{search}%"
            q = q.filter(
                (Transaction.subcategory.ilike(like)) |
                (Transaction.description.ilike(like)) |
                (Transaction.category.ilike(like))
            )
        return q.order_by(Transaction.date.desc(), Transaction.id.desc()).limit(limit).all()
    finally:
        session.close()


def delete_transaction(txn_id: int) -> bool:
    session = get_session()
    try:
        txn = session.query(Transaction).get(txn_id)
        if not txn:
            return False
        session.delete(txn)
        session.commit()
        return True
    finally:
        session.close()


def calculate_period_summary(period_id: int) -> Dict:
    """
    Returns the key numbers the user cares about:
    - total_income
    - total_bills
    - total_debt
    - total_expenses
    - total_savings
    - leftover (income - bills - debt - expenses - savings)
    """
    session = get_session()
    try:
        rows = (
            session.query(Transaction.category, func.sum(Transaction.amount))
            .filter(Transaction.period_id == period_id)
            .group_by(Transaction.category)
            .all()
        )
        totals = {cat: 0.0 for cat in ["Income", "Savings", "Bills", "Expenses", "Debt"]}
        for cat, total in rows:
            if cat in totals:
                totals[cat] = float(total or 0)

        leftover = (
            totals["Income"]
            - totals["Bills"]
            - totals["Debt"]
            - totals["Expenses"]
            - totals["Savings"]
        )
        return {
            **totals,
            "leftover": leftover,
            "total_out": totals["Bills"] + totals["Debt"] + totals["Expenses"] + totals["Savings"],
        }
    finally:
        session.close()


def get_recurring_suggestions(period: PaycheckPeriod) -> List[Dict]:
    """
    Return suggested recurring bills/debt that are not yet recorded
    in this period (or that have typical amounts).
    """
    session = get_session()
    try:
        # Already recorded subcategories in this period
        existing = {
            (t.category, t.subcategory)
            for t in session.query(Transaction)
            .filter_by(period_id=period.id)
            .all()
        }

        suggestions = []
        recurrings = (
            session.query(Subcategory)
            .filter_by(is_recurring=True, active=True)
            .all()
        )
        for sub in recurrings:
            if (sub.category, sub.name) not in existing:
                suggestions.append({
                    "category": sub.category,
                    "subcategory": sub.name,
                    "typical_amount": sub.typical_amount,
                    "due_info": sub.due_info,
                })
        return suggestions
    finally:
        session.close()


def preload_recurring(period_id: int, selected: List[Dict]) -> int:
    """
    Add the selected suggested items as transactions (marked is_suggested=True).
    Returns how many were added.
    """
    count = 0
    period = get_period_by_id(period_id)
    if not period:
        return 0

    for item in selected:
        amount = item.get("amount") or item.get("typical_amount") or 0
        if amount <= 0:
            continue
        add_transaction(
            period_id=period_id,
            txn_date=period.start_date,  # default to start of period; user can edit later
            amount=float(amount),
            category=item["category"],
            subcategory=item["subcategory"],
            description="Pre-loaded recurring",
            is_suggested=True,
            payment_method="Credit Card",  # default assumption
        )
        count += 1
    return count
