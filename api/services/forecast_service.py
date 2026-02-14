"""Forecast service for projecting balance N periods forward."""

import uuid
from dataclasses import dataclass
from datetime import date
from calendar import monthrange
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from api.models.account import Account, AccountPurpose
from api.models.transaction import Transaction
from api.models.budget_post import BudgetPost, BudgetPostDirection
from api.services.budget_post_service import expand_amount_patterns_to_occurrences


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
        .options(joinedload(BudgetPost.amount_patterns), joinedload(BudgetPost.category))
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

        # Calculate month date range
        month_start = date(year, month, 1)
        _, last_day = monthrange(year, month)
        month_end = date(year, month, last_day)
        month_str = month_start.strftime("%Y-%m")

        # Start balance is the running balance from previous month
        start_balance = running_balance

        # Generate expected transactions for this month
        expected_income = 0
        expected_expenses = 0

        for budget_post in budget_posts:
            # Skip transfers - they are net zero for total balance
            if budget_post.direction == BudgetPostDirection.TRANSFER:
                continue

            # Expand amount patterns to occurrences for this month
            occurrences = expand_amount_patterns_to_occurrences(
                budget_post,
                month_start,
                month_end
            )

            for occurrence_date, amount in occurrences:
                # Use direction to determine income vs expense
                # Amount from pattern is always positive in new model
                if budget_post.direction == BudgetPostDirection.INCOME:
                    expected_income += amount
                elif budget_post.direction == BudgetPostDirection.EXPENSE:
                    expected_expenses += amount

                    # Track large expenses in next 3 months for insights
                    # Skip if budget_post has no category (shouldn't happen for expense, but check anyway)
                    if month_offset < 3 and budget_post.category:
                        large_expenses.append({
                            "name": budget_post.category.name,
                            "amount": -amount,  # Store as negative for display consistency
                            "date": occurrence_date.isoformat()
                        })

        # Calculate end balance (expenses are added as positive, so subtract them)
        end_balance = start_balance + expected_income - expected_expenses

        projections.append(MonthProjection(
            month=month_str,
            start_balance=start_balance,
            expected_income=expected_income,
            expected_expenses=-expected_expenses,  # Store as negative for display consistency
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
