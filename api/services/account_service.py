"""Account service layer for business logic."""

import uuid
from datetime import datetime, UTC

from sqlalchemy.orm import Session

from api.models.account import Account, AccountPurpose, AccountDatasource


def get_default_can_go_negative(datasource: AccountDatasource) -> bool:
    """
    Get default can_go_negative value based on datasource.

    Args:
        datasource: Account datasource type

    Returns:
        Default value for can_go_negative
    """
    return datasource == AccountDatasource.CREDIT


def get_default_needs_coverage(datasource: AccountDatasource) -> bool:
    """
    Get default needs_coverage value based on datasource.

    Args:
        datasource: Account datasource type

    Returns:
        Default value for needs_coverage
    """
    return datasource == AccountDatasource.CREDIT


def create_account(
    db: Session,
    budget_id: uuid.UUID,
    user_id: uuid.UUID,
    name: str,
    purpose: AccountPurpose,
    datasource: AccountDatasource,
    starting_balance: int,
    currency: str = "DKK",
    can_go_negative: bool | None = None,
    needs_coverage: bool | None = None,
) -> Account | None:
    """
    Create a new account for a budget.

    Args:
        db: Database session
        budget_id: Budget ID to create account for
        user_id: User ID creating the account
        name: Account name
        purpose: Account purpose (normal/savings/loan)
        datasource: Account datasource (bank/credit/cash/virtual)
        starting_balance: Starting balance in øre
        currency: Currency code (default DKK)
        can_go_negative: Whether account can go negative (None = use default)
        needs_coverage: Whether negative balance needs coverage (None = use default)

    Returns:
        Created Account instance, or None if duplicate name in budget
    """
    # Check for duplicate name within budget
    existing = db.query(Account).filter(
        Account.budget_id == budget_id,
        Account.name == name,
        Account.deleted_at.is_(None),
    ).first()

    if existing:
        return None

    # Set defaults based on datasource if not provided
    if can_go_negative is None:
        can_go_negative = get_default_can_go_negative(datasource)
    if needs_coverage is None:
        needs_coverage = get_default_needs_coverage(datasource)

    account = Account(
        budget_id=budget_id,
        name=name,
        purpose=purpose,
        datasource=datasource,
        currency=currency,
        starting_balance=starting_balance,
        can_go_negative=can_go_negative,
        needs_coverage=needs_coverage,
        created_by=user_id,
        updated_by=user_id,
    )

    db.add(account)
    db.commit()
    db.refresh(account)

    return account


def get_budget_accounts(
    db: Session,
    budget_id: uuid.UUID,
) -> list[Account]:
    """
    Get all non-deleted accounts for a budget.

    Args:
        db: Database session
        budget_id: Budget ID to get accounts for

    Returns:
        List of Account instances
    """
    return db.query(Account).filter(
        Account.budget_id == budget_id,
        Account.deleted_at.is_(None),
    ).order_by(Account.created_at.desc()).all()


def get_account_by_id(
    db: Session,
    account_id: uuid.UUID,
    budget_id: uuid.UUID,
) -> Account | None:
    """
    Get a single account by ID.

    Args:
        db: Database session
        account_id: Account ID to retrieve
        budget_id: Budget ID (for authorization check)

    Returns:
        Account if found and belongs to budget, None otherwise
    """
    return db.query(Account).filter(
        Account.id == account_id,
        Account.budget_id == budget_id,
        Account.deleted_at.is_(None),
    ).first()


def update_account(
    db: Session,
    account_id: uuid.UUID,
    budget_id: uuid.UUID,
    user_id: uuid.UUID,
    name: str | None = None,
    purpose: AccountPurpose | None = None,
    datasource: AccountDatasource | None = None,
    currency: str | None = None,
    starting_balance: int | None = None,
    can_go_negative: bool | None = None,
    needs_coverage: bool | None = None,
) -> Account | None:
    """
    Update an account.

    Args:
        db: Database session
        account_id: Account ID to update
        budget_id: Budget ID (for authorization check)
        user_id: User ID updating the account
        name: Optional new name
        purpose: Optional new purpose
        datasource: Optional new datasource
        currency: Optional new currency
        starting_balance: Optional new starting balance
        can_go_negative: Optional new can_go_negative
        needs_coverage: Optional new needs_coverage

    Returns:
        Updated Account if found and belongs to budget, None otherwise
    """
    account = get_account_by_id(db, account_id, budget_id)
    if not account:
        return None

    # Check for duplicate name if name is being changed
    if name is not None and name != account.name:
        existing = db.query(Account).filter(
            Account.budget_id == budget_id,
            Account.name == name,
            Account.deleted_at.is_(None),
            Account.id != account_id,
        ).first()
        if existing:
            return None

    # Update fields if provided
    if name is not None:
        account.name = name
    if purpose is not None:
        account.purpose = purpose
    if datasource is not None:
        account.datasource = datasource
    if currency is not None:
        account.currency = currency
    if starting_balance is not None:
        account.starting_balance = starting_balance
    if can_go_negative is not None:
        account.can_go_negative = can_go_negative
    if needs_coverage is not None:
        account.needs_coverage = needs_coverage

    account.updated_by = user_id

    db.commit()
    db.refresh(account)

    return account


def soft_delete_account(
    db: Session,
    account_id: uuid.UUID,
    budget_id: uuid.UUID,
) -> bool:
    """
    Soft delete an account.

    Args:
        db: Database session
        account_id: Account ID to delete
        budget_id: Budget ID (for authorization check)

    Returns:
        True if account was deleted, False if not found or not in budget
    """
    account = get_account_by_id(db, account_id, budget_id)
    if not account:
        return False

    account.deleted_at = datetime.now(UTC)
    db.commit()

    return True
