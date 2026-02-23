"""Account service layer for business logic."""

import uuid
from datetime import datetime, UTC

from sqlalchemy.orm import Session

from api.models.account import Account, AccountPurpose, AccountDatasource


# Sentinel value for "not provided" in updates (distinct from None which means "set to NULL")
_UNSET = object()


def create_account(
    db: Session,
    budget_id: uuid.UUID,
    user_id: uuid.UUID,
    name: str,
    purpose: AccountPurpose,
    datasource: AccountDatasource,
    starting_balance: int,
    currency: str = "DKK",
    credit_limit: int | None = None,
    locked: bool = False,
) -> Account | None:
    """
    Create a new account for a budget.

    Args:
        db: Database session
        budget_id: Budget ID to create account for
        user_id: User ID creating the account
        name: Account name
        purpose: Account purpose (normal/savings/loan/kassekredit)
        datasource: Account datasource (bank/cash/virtual)
        starting_balance: Starting balance in øre
        currency: Currency code (default DKK)
        credit_limit: Credit limit in øre (0 = cannot go negative, None = no limit)
        locked: Whether account is locked (only for savings accounts)

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

    # Validation: locked should only be True for savings accounts
    if locked and purpose != AccountPurpose.SAVINGS:
        raise ValueError("Only savings accounts can be locked")

    # Validation: credit_limit must be <= 0 (negative floor or 0)
    if credit_limit is not None and credit_limit > 0:
        raise ValueError("credit_limit must be <= 0 (negative floor or 0)")

    account = Account(
        budget_id=budget_id,
        name=name,
        purpose=purpose,
        datasource=datasource,
        currency=currency,
        starting_balance=starting_balance,
        credit_limit=credit_limit,
        locked=locked,
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
    name=_UNSET,
    purpose=_UNSET,
    datasource=_UNSET,
    currency=_UNSET,
    starting_balance=_UNSET,
    credit_limit=_UNSET,
    locked=_UNSET,
) -> Account | None:
    """
    Update an account.

    Args:
        db: Database session
        account_id: Account ID to update
        budget_id: Budget ID (for authorization check)
        user_id: User ID updating the account
        name: Optional new name (use _UNSET to skip)
        purpose: Optional new purpose (use _UNSET to skip)
        datasource: Optional new datasource (use _UNSET to skip)
        currency: Optional new currency (use _UNSET to skip)
        starting_balance: Optional new starting balance (use _UNSET to skip)
        credit_limit: Optional new credit limit (use _UNSET to skip, None to clear)
        locked: Optional new locked status (use _UNSET to skip)

    Returns:
        Updated Account if found and belongs to budget, None otherwise
    """
    account = get_account_by_id(db, account_id, budget_id)
    if not account:
        return None

    # Check for duplicate name if name is being changed
    if name is not _UNSET and name != account.name:
        existing = db.query(Account).filter(
            Account.budget_id == budget_id,
            Account.name == name,
            Account.deleted_at.is_(None),
            Account.id != account_id,
        ).first()
        if existing:
            return None

    # Validation: if locked is being set to True, and purpose is being changed or is already not savings
    new_purpose = purpose if purpose is not _UNSET else account.purpose
    new_locked = locked if locked is not _UNSET else account.locked
    if new_locked and new_purpose != AccountPurpose.SAVINGS:
        raise ValueError("Only savings accounts can be locked")

    # Validation: credit_limit must be <= 0 (negative floor or 0)
    if credit_limit is not _UNSET:
        if credit_limit is not None and credit_limit > 0:
            raise ValueError("credit_limit must be <= 0 (negative floor or 0)")

    # Update fields if provided
    if name is not _UNSET:
        account.name = name
    if purpose is not _UNSET:
        account.purpose = purpose
    if datasource is not _UNSET:
        account.datasource = datasource
    if currency is not _UNSET:
        account.currency = currency
    if starting_balance is not _UNSET:
        account.starting_balance = starting_balance
    if credit_limit is not _UNSET:
        account.credit_limit = credit_limit
    if locked is not _UNSET:
        account.locked = locked

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
