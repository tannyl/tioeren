"""Forecast service for projecting balance N periods forward."""

import uuid
from dataclasses import dataclass
from datetime import date, timedelta
from calendar import monthrange
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from api.models.account import Account, AccountPurpose
from api.models.transaction import Transaction
from api.models.budget_post import BudgetPost, BudgetPostType
from api.models.amount_pattern import AmountPattern


@dataclass
class MonthProjection:
    """Projection data for a single month."""

    month: str  # "2026-02", "2026-03", etc.
    start_balance: int  # øre
    expected_income: int  # øre
    expected_expenses: int  # øre
    end_balance: int  # øre


@dataclass
class ForecastResult:
    """Complete forecast result with projections and insights."""

    projections: list[MonthProjection]
    lowest_point: dict  # {"month": "2026-04", "balance": 620000}
    next_large_expense: Optional[dict]  # {"name": "Insurance", "amount": -480000, "date": "2026-03-15"}


def get_current_balance(db: Session, budget_id: uuid.UUID) -> int:
    """
    Calculate current balance for normal accounts in the budget.

    Args:
        db: Database session
        budget_id: Budget ID

    Returns:
        Current balance in øre (sum of starting_balance + transactions for normal accounts)
    """
    # Get all normal accounts with their transaction sums
    transaction_sum_subquery = (
        db.query(
            Transaction.account_id,
            func.coalesce(func.sum(Transaction.amount), 0).label("transaction_sum")
        )
        .filter(Transaction.account_id.in_(
            db.query(Account.id).filter(
                Account.budget_id == budget_id,
                Account.purpose == AccountPurpose.NORMAL,
                Account.deleted_at.is_(None)
            )
        ))
        .group_by(Transaction.account_id)
        .subquery()
    )

    accounts = (
        db.query(
            Account.starting_balance,
            func.coalesce(transaction_sum_subquery.c.transaction_sum, 0).label("transaction_sum")
        )
        .outerjoin(transaction_sum_subquery, Account.id == transaction_sum_subquery.c.account_id)
        .filter(
            Account.budget_id == budget_id,
            Account.purpose == AccountPurpose.NORMAL,
            Account.deleted_at.is_(None)
        )
        .all()
    )

    total_balance = sum(acc.starting_balance + acc.transaction_sum for acc in accounts)
    return total_balance


def generate_occurrences(budget_post: BudgetPost, month_date: date) -> list[dict]:
    """
    Generate expected occurrences for a budget post in a given month.

    Args:
        budget_post: Budget post with amount patterns loaded
        month_date: Date representing the month (typically first day of month)

    Returns:
        List of occurrence dictionaries with 'date' and 'amount' keys
    """
    occurrences = []

    # Get active amount patterns for this month
    # For now, get the first active pattern (future enhancement: handle multiple patterns)
    if not budget_post.amount_patterns:
        return occurrences

    # Get the first active amount pattern
    # TODO: In future, handle multiple overlapping patterns and select based on start_date/end_date
    amount_pattern = budget_post.amount_patterns[0]
    expected_amount = amount_pattern.amount
    pattern = amount_pattern.recurrence_pattern

    # If no pattern, default to monthly on day 1
    if not pattern or not isinstance(pattern, dict):
        pattern = {"type": "monthly", "day": 1}

    pattern_type = pattern.get("type", "monthly")

    if pattern_type == "monthly":
        # Monthly recurrence on specific day
        day = pattern.get("day", 1)
        year = month_date.year
        month = month_date.month

        # Ensure day is valid for this month
        _, last_day = monthrange(year, month)
        if day > last_day:
            day = last_day

        occurrence_date = date(year, month, day)
        occurrences.append({
            "date": occurrence_date,
            "amount": expected_amount
        })

    elif pattern_type == "quarterly":
        # Quarterly on specific months and day
        months = pattern.get("months", [3, 6, 9, 12])
        day = pattern.get("day", 1)

        if month_date.month in months:
            year = month_date.year
            month = month_date.month

            _, last_day = monthrange(year, month)
            if day > last_day:
                day = last_day

            occurrence_date = date(year, month, day)
            occurrences.append({
                "date": occurrence_date,
                "amount": expected_amount
            })

    elif pattern_type == "yearly":
        # Yearly on specific month and day
        target_month = pattern.get("month")
        target_day = pattern.get("day", 1)

        if month_date.month == target_month:
            year = month_date.year

            _, last_day = monthrange(year, target_month)
            if target_day > last_day:
                target_day = last_day

            occurrence_date = date(year, target_month, target_day)
            occurrences.append({
                "date": occurrence_date,
                "amount": expected_amount
            })

    elif pattern_type == "once":
        # One-time occurrence on specific date
        occurrence_date_str = pattern.get("date")
        if occurrence_date_str:
            try:
                occurrence_date = date.fromisoformat(occurrence_date_str)
                # Check if this date is in the target month
                if occurrence_date.year == month_date.year and occurrence_date.month == month_date.month:
                    occurrences.append({
                        "date": occurrence_date,
                        "amount": expected_amount
                    })
            except (ValueError, TypeError):
                # Invalid date format, skip
                pass

    return occurrences


def calculate_forecast(db: Session, budget_id: uuid.UUID, months: int = 12) -> ForecastResult:
    """
    Calculate forecast projection for N months forward.

    Args:
        db: Database session
        budget_id: Budget ID to forecast
        months: Number of months to project forward (default 12)

    Returns:
        ForecastResult with monthly projections and insights
    """
    # Get current balance as starting point
    current_balance = get_current_balance(db, budget_id)

    # Get all active budget posts with their amount patterns
    budget_posts = (
        db.query(BudgetPost)
        .options(joinedload(BudgetPost.amount_patterns))
        .filter(
            BudgetPost.budget_id == budget_id,
            BudgetPost.deleted_at.is_(None)
        )
        .all()
    )

    # Generate projections for each month
    projections = []
    today = date.today()
    running_balance = current_balance

    # Track for insights
    lowest_balance = current_balance
    lowest_month = None
    next_large_expense = None
    large_expenses = []  # Track expenses in next 3 months for insights

    for month_offset in range(months):
        # Calculate target month
        year = today.year
        month = today.month + month_offset

        # Handle year overflow
        while month > 12:
            month -= 12
            year += 1

        month_date = date(year, month, 1)
        month_str = month_date.strftime("%Y-%m")

        # Start balance is the running balance from previous month
        start_balance = running_balance

        # Generate expected transactions for this month
        expected_income = 0
        expected_expenses = 0

        for budget_post in budget_posts:
            occurrences = generate_occurrences(budget_post, month_date)

            for occurrence in occurrences:
                amount = occurrence["amount"]

                # Categorize as income or expense
                if amount > 0:
                    expected_income += amount
                else:
                    expected_expenses += amount

                    # Track large expenses in next 3 months
                    if month_offset < 3:
                        large_expenses.append({
                            "name": budget_post.name,
                            "amount": amount,
                            "date": occurrence["date"].isoformat()
                        })

        # Calculate end balance
        end_balance = start_balance + expected_income + expected_expenses

        projections.append(MonthProjection(
            month=month_str,
            start_balance=start_balance,
            expected_income=expected_income,
            expected_expenses=expected_expenses,
            end_balance=end_balance
        ))

        # Track lowest point
        if end_balance < lowest_balance:
            lowest_balance = end_balance
            lowest_month = month_str

        # Update running balance for next iteration
        running_balance = end_balance

    # Identify next large expense (largest single expense in next 3 months)
    if large_expenses:
        next_large_expense = min(large_expenses, key=lambda x: x["amount"])

    # Build lowest point dict
    lowest_point = {
        "month": lowest_month if lowest_month else month_str,
        "balance": lowest_balance
    }

    return ForecastResult(
        projections=projections,
        lowest_point=lowest_point,
        next_large_expense=next_large_expense
    )
