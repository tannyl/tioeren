"""Forecast service for projecting balance N periods forward."""

import uuid
from dataclasses import dataclass
from datetime import date
from calendar import monthrange
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from api.models.container import Container, ContainerType
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
    Calculate current balance for cashbox containers in the budget.

    Args:
        db: Database session
        budget_id: Budget ID

    Returns:
        Current balance in øre (sum of starting_balance + transactions for cashbox containers)
    """
    # Get all cashbox containers with their transaction sums
    transaction_sum_subquery = (
        db.query(
            Transaction.container_id,
            func.coalesce(func.sum(Transaction.amount), 0).label("transaction_sum")
        )
        .filter(Transaction.container_id.in_(
            db.query(Container.id).filter(
                Container.budget_id == budget_id,
                Container.type == ContainerType.CASHBOX,
                Container.deleted_at.is_(None)
            )
        ))
        .group_by(Transaction.container_id)
        .subquery()
    )

    containers = (
        db.query(
            Container.starting_balance,
            func.coalesce(transaction_sum_subquery.c.transaction_sum, 0).label("transaction_sum")
        )
        .outerjoin(transaction_sum_subquery, Container.id == transaction_sum_subquery.c.container_id)
        .filter(
            Container.budget_id == budget_id,
            Container.type == ContainerType.CASHBOX,
            Container.deleted_at.is_(None)
        )
        .all()
    )

    total_balance = sum(cont.starting_balance + cont.transaction_sum for cont in containers)
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

    # Get all active budget posts with their amount patterns and container relationships
    budget_posts = (
        db.query(BudgetPost)
        .options(
            joinedload(BudgetPost.amount_patterns),
            joinedload(BudgetPost.transfer_from_container),
            joinedload(BudgetPost.transfer_to_container),
        )
        .filter(
            BudgetPost.budget_id == budget_id,
            BudgetPost.deleted_at.is_(None)
        )
        .all()
    )

    # Load all containers for this budget (for type checking)
    containers = (
        db.query(Container)
        .filter(
            Container.budget_id == budget_id,
            Container.deleted_at.is_(None)
        )
        .all()
    )
    container_types = {cont.id: cont.type for cont in containers}

    # Filter to root-level income/expense posts with cashbox containers
    income_expense_posts = [
        post for post in budget_posts
        if post.direction in (BudgetPostDirection.INCOME, BudgetPostDirection.EXPENSE)
    ]

    # Filter to posts with at least one cashbox container
    cashbox_posts = []
    for post in income_expense_posts:
        if post.container_ids:
            has_cashbox = False
            for cont_id_str in post.container_ids:
                try:
                    cont_id = uuid.UUID(cont_id_str)
                    if container_types.get(cont_id) == ContainerType.CASHBOX:
                        has_cashbox = True
                        break
                except (ValueError, TypeError):
                    continue
            if has_cashbox:
                cashbox_posts.append(post)

    # Filter to root-level posts (posts with no ancestors in the hierarchy)
    root_posts = []
    for post in cashbox_posts:
        if not post.category_path:
            continue

        # Check if any other post is an ancestor (proper prefix of same direction)
        is_root = True
        for other_post in cashbox_posts:
            if other_post.id == post.id or not other_post.category_path:
                continue
            if other_post.direction != post.direction:
                continue

            # Check if other_post is an ancestor (proper prefix)
            if len(other_post.category_path) < len(post.category_path):
                if post.category_path[:len(other_post.category_path)] == other_post.category_path:
                    is_root = False
                    break

        if is_root:
            root_posts.append(post)

    # Get transfer posts
    transfer_posts = [
        post for post in budget_posts
        if post.direction == BudgetPostDirection.TRANSFER
    ]

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

        # Process root-level income/expense posts
        for budget_post in root_posts:
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
                    if month_offset < 3 and budget_post.category_path:
                        large_expenses.append({
                            "name": budget_post.category_path[-1],
                            "amount": -amount,  # Store as negative for display consistency
                            "date": occurrence_date.isoformat()
                        })

        # Process transfers (pengekasse ↔ non-pengekasse only)
        for transfer_post in transfer_posts:
            # Check if both containers exist and get their types
            from_container = transfer_post.transfer_from_container
            to_container = transfer_post.transfer_to_container

            if not from_container or not to_container:
                continue

            from_is_cashbox = from_container.type == ContainerType.CASHBOX
            to_is_cashbox = to_container.type == ContainerType.CASHBOX

            # Skip if both are cashbox or neither are cashbox (net-zero for pengekasse balance)
            if from_is_cashbox == to_is_cashbox:
                continue

            # Expand amount patterns to occurrences for this month
            occurrences = expand_amount_patterns_to_occurrences(
                transfer_post,
                month_start,
                month_end
            )

            for occurrence_date, amount in occurrences:
                if from_is_cashbox and not to_is_cashbox:
                    # pengekasse → non-pengekasse: reduces balance (treat as expense)
                    expected_expenses += amount
                elif not from_is_cashbox and to_is_cashbox:
                    # non-pengekasse → pengekasse: increases balance (treat as income)
                    expected_income += amount

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
