"""Dashboard service layer for aggregated budget data."""

import uuid
from datetime import date, datetime
from calendar import monthrange

from sqlalchemy import func, and_, or_, case
from sqlalchemy.orm import Session, joinedload

from api.models.container import Container, ContainerType
from api.models.transaction import Transaction, TransactionStatus
from api.models.budget_post import BudgetPost, BudgetPostType
from api.models.amount_pattern import AmountPattern
from api.models.transaction_allocation import TransactionAllocation


def get_dashboard_data(db: Session, budget_id: uuid.UUID) -> dict:
    """
    Get aggregated dashboard data for a budget.

    Args:
        db: Database session
        budget_id: Budget ID to get dashboard for

    Returns:
        Dictionary with dashboard data:
        - available_balance: Sum of balances for cashbox containers
        - containers: List of all containers with current balances
        - month_summary: Income/expenses for current month
        - pending_count: Count of uncategorized transactions
        - fixed_expenses: Fixed budget posts with status for current month
    """
    today = date.today()
    month_start = date(today.year, today.month, 1)
    _, last_day = monthrange(today.year, today.month)
    month_end = date(today.year, today.month, last_day)

    # Get all containers with their current balances (starting_balance + sum of transactions)
    # Using subquery to calculate transaction sums per container
    transaction_sum_subquery = (
        db.query(
            Transaction.container_id,
            func.coalesce(func.sum(Transaction.amount), 0).label("transaction_sum")
        )
        .filter(Transaction.container_id.in_(
            db.query(Container.id).filter(
                Container.budget_id == budget_id,
                Container.deleted_at.is_(None)
            )
        ))
        .group_by(Transaction.container_id)
        .subquery()
    )

    containers = (
        db.query(
            Container.id,
            Container.name,
            Container.type,
            Container.starting_balance,
            func.coalesce(transaction_sum_subquery.c.transaction_sum, 0).label("transaction_sum")
        )
        .outerjoin(transaction_sum_subquery, Container.id == transaction_sum_subquery.c.container_id)
        .filter(
            Container.budget_id == budget_id,
            Container.deleted_at.is_(None)
        )
        .all()
    )

    # Calculate balances and prepare container list
    containers_data = []
    available_balance = 0

    for cont in containers:
        current_balance = cont.starting_balance + cont.transaction_sum
        containers_data.append({
            "id": str(cont.id),
            "name": cont.name,
            "type": cont.type,
            "balance": current_balance
        })

        # Sum up available balance (only cashbox containers)
        if cont.type == ContainerType.CASHBOX:
            available_balance += current_balance

    # Get month summary (income and expenses for current month)
    # Query all transactions for this budget's containers in current month
    month_transactions = (
        db.query(
            func.sum(case((Transaction.amount > 0, Transaction.amount), else_=0)).label("income"),
            func.sum(case((Transaction.amount < 0, Transaction.amount), else_=0)).label("expenses")
        )
        .join(Container, Transaction.container_id == Container.id)
        .filter(
            Container.budget_id == budget_id,
            Container.deleted_at.is_(None),
            Transaction.date >= month_start,
            Transaction.date <= month_end
        )
        .first()
    )

    income = month_transactions.income or 0
    expenses = month_transactions.expenses or 0
    net = income + expenses

    month_summary = {
        "income": income,
        "expenses": expenses,
        "net": net
    }

    # Get pending (uncategorized) transaction count
    pending_count = (
        db.query(func.count(Transaction.id))
        .join(Container, Transaction.container_id == Container.id)
        .filter(
            Container.budget_id == budget_id,
            Container.deleted_at.is_(None),
            Transaction.status == TransactionStatus.UNCATEGORIZED
        )
        .scalar()
    ) or 0

    # Get fixed budget posts for the current month with their status and amount patterns
    # For MVP: simplified matching - check if any transaction is allocated to this budget post in current month
    fixed_budget_posts = (
        db.query(BudgetPost)
        .options(joinedload(BudgetPost.amount_patterns))
        .filter(
            BudgetPost.budget_id == budget_id,
            BudgetPost.type == BudgetPostType.FIXED,
            BudgetPost.deleted_at.is_(None)
        )
        .all()
    )

    fixed_expenses = []
    for bp in fixed_budget_posts:
        # Skip if no amount patterns
        if not bp.amount_patterns:
            continue

        # Get the first active amount pattern
        # TODO: In future, handle multiple patterns and select based on start_date/end_date
        amount_pattern = bp.amount_patterns[0]
        expected_amount = amount_pattern.amount

        # Check if there's an allocation to this amount pattern in current month
        allocation = (
            db.query(TransactionAllocation)
            .join(Transaction, TransactionAllocation.transaction_id == Transaction.id)
            .filter(
                TransactionAllocation.amount_pattern_id == amount_pattern.id,
                Transaction.date >= month_start,
                Transaction.date <= month_end
            )
            .first()
        )

        # For MVP: simplified status determination
        # In a real implementation, we'd parse recurrence_pattern to get expected date
        # For now, we'll use a placeholder date (15th of the month) and determine status
        expected_date = date(today.year, today.month, 15)

        if allocation:
            # Transaction exists - mark as paid
            # Get the actual transaction amount
            transaction = (
                db.query(Transaction)
                .filter(Transaction.id == allocation.transaction_id)
                .first()
            )

            fixed_expenses.append({
                "name": bp.category_path[-1] if bp.category_path else "Unknown",
                "expected_amount": expected_amount,
                "status": "paid",
                "date": expected_date.isoformat(),
                "actual_amount": transaction.amount if transaction else None
            })
        elif expected_date > today:
            # Expected date hasn't passed - mark as pending
            fixed_expenses.append({
                "name": bp.category_path[-1] if bp.category_path else "Unknown",
                "expected_amount": expected_amount,
                "status": "pending",
                "date": expected_date.isoformat(),
                "actual_amount": None
            })
        else:
            # Expected date passed, no match - mark as overdue
            fixed_expenses.append({
                "name": bp.category_path[-1] if bp.category_path else "Unknown",
                "expected_amount": expected_amount,
                "status": "overdue",
                "date": expected_date.isoformat(),
                "actual_amount": None
            })

    return {
        "available_balance": available_balance,
        "containers": containers_data,
        "month_summary": month_summary,
        "pending_count": pending_count,
        "fixed_expenses": fixed_expenses
    }
