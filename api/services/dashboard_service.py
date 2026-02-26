"""Dashboard service layer for aggregated budget data."""

import uuid
from datetime import date, datetime
from calendar import monthrange

from sqlalchemy import func, and_, or_, case
from sqlalchemy.orm import Session, joinedload

from api.models.container import Container, ContainerType
from api.models.transaction import Transaction, TransactionStatus
from api.models.budget_post import BudgetPost
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

    return {
        "available_balance": available_balance,
        "containers": containers_data,
        "month_summary": month_summary,
        "pending_count": pending_count
    }
