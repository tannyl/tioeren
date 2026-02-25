"""Container service layer for business logic."""

import uuid
from datetime import datetime, UTC

from sqlalchemy.orm import Session

from api.models.container import Container, ContainerType
from api.schemas.container import ContainerCreate, ContainerUpdate


# Sentinel value for "not provided" in updates (distinct from None which means "set to NULL")
_UNSET = object()


def create_container(
    db: Session,
    budget_id: uuid.UUID,
    data: ContainerCreate,
    user_id: uuid.UUID,
) -> Container | None:
    """
    Create a new container for a budget.

    Args:
        db: Database session
        budget_id: Budget ID to create container for
        data: Container creation data
        user_id: User ID creating the container

    Returns:
        Created Container instance, or None if duplicate name in budget

    Raises:
        ValueError: If type-specific validation fails
    """
    # Check for duplicate name within budget
    existing = db.query(Container).filter(
        Container.budget_id == budget_id,
        Container.name == data.name,
        Container.deleted_at.is_(None),
    ).first()

    if existing:
        return None

    # Type-specific validation (defense-in-depth, schemas already validate)
    if data.type == ContainerType.CASHBOX:
        if data.overdraft_limit is not None and data.overdraft_limit > 0:
            raise ValueError("overdraft_limit must be <= 0 (negative floor or 0)")
    elif data.type == ContainerType.PIGGYBANK:
        # No additional validation needed for piggybank
        pass
    elif data.type == ContainerType.DEBT:
        if data.credit_limit is None:
            raise ValueError("debt containers require credit_limit")
        if data.credit_limit > 0:
            raise ValueError("credit_limit must be <= 0 (negative floor or 0)")
        if data.interest_rate is not None and data.interest_rate <= 0:
            raise ValueError("interest_rate must be > 0")
        if data.required_payment is not None and data.required_payment <= 0:
            raise ValueError("required_payment must be > 0")

    container = Container(
        budget_id=budget_id,
        name=data.name,
        type=data.type,
        starting_balance=data.starting_balance,
        bank_name=data.bank_name,
        bank_account_name=data.bank_account_name,
        bank_reg_number=data.bank_reg_number,
        bank_account_number=data.bank_account_number,
        overdraft_limit=data.overdraft_limit,
        locked=data.locked,
        credit_limit=data.credit_limit,
        allow_withdrawals=data.allow_withdrawals,
        interest_rate=data.interest_rate,
        interest_frequency=data.interest_frequency,
        required_payment=data.required_payment,
        created_by=user_id,
        updated_by=user_id,
    )

    db.add(container)
    db.commit()
    db.refresh(container)

    return container


def get_budget_containers(
    db: Session,
    budget_id: uuid.UUID,
) -> list[Container]:
    """
    Get all non-deleted containers for a budget.

    Args:
        db: Database session
        budget_id: Budget ID to get containers for

    Returns:
        List of Container instances
    """
    return db.query(Container).filter(
        Container.budget_id == budget_id,
        Container.deleted_at.is_(None),
    ).order_by(Container.created_at.desc()).all()


def get_container_by_id(
    db: Session,
    budget_id: uuid.UUID,
    container_id: uuid.UUID,
) -> Container | None:
    """
    Get a single container by ID.

    Args:
        db: Database session
        budget_id: Budget ID (for authorization check)
        container_id: Container ID to retrieve

    Returns:
        Container if found and belongs to budget, None otherwise
    """
    return db.query(Container).filter(
        Container.id == container_id,
        Container.budget_id == budget_id,
        Container.deleted_at.is_(None),
    ).first()


def update_container(
    db: Session,
    budget_id: uuid.UUID,
    container_id: uuid.UUID,
    data: ContainerUpdate,
    user_id: uuid.UUID,
) -> Container | None:
    """
    Update a container.

    Args:
        db: Database session
        budget_id: Budget ID (for authorization check)
        container_id: Container ID to update
        data: Container update data
        user_id: User ID updating the container

    Returns:
        Updated Container if found and belongs to budget, None otherwise

    Raises:
        ValueError: If validation fails (duplicate name, type change attempt, or type-specific constraint violation)
    """
    container = get_container_by_id(db, budget_id, container_id)
    if not container:
        return None

    # Type changes are NOT allowed (would require data migration)
    if "type" in data.model_fields_set and data.type is not None:
        if data.type != container.type:
            raise ValueError("Container type cannot be changed")

    # Check for duplicate name if name is being changed
    if "name" in data.model_fields_set and data.name is not None and data.name != container.name:
        existing = db.query(Container).filter(
            Container.budget_id == budget_id,
            Container.name == data.name,
            Container.deleted_at.is_(None),
            Container.id != container_id,
        ).first()
        if existing:
            return None

    # Type-specific validation for updated fields (defense-in-depth)
    if container.type == ContainerType.CASHBOX:
        if "overdraft_limit" in data.model_fields_set and data.overdraft_limit is not None:
            if data.overdraft_limit > 0:
                raise ValueError("overdraft_limit must be <= 0 (negative floor or 0)")
    elif container.type == ContainerType.DEBT:
        if "credit_limit" in data.model_fields_set and data.credit_limit is not None:
            if data.credit_limit > 0:
                raise ValueError("credit_limit must be <= 0 (negative floor or 0)")
        if "interest_rate" in data.model_fields_set and data.interest_rate is not None:
            if data.interest_rate <= 0:
                raise ValueError("interest_rate must be > 0")
        if "required_payment" in data.model_fields_set and data.required_payment is not None:
            if data.required_payment <= 0:
                raise ValueError("required_payment must be > 0")

    # Update fields if provided
    if "name" in data.model_fields_set and data.name is not None:
        container.name = data.name
    if "starting_balance" in data.model_fields_set and data.starting_balance is not None:
        container.starting_balance = data.starting_balance
    if "bank_name" in data.model_fields_set:
        container.bank_name = data.bank_name
    if "bank_account_name" in data.model_fields_set:
        container.bank_account_name = data.bank_account_name
    if "bank_reg_number" in data.model_fields_set:
        container.bank_reg_number = data.bank_reg_number
    if "bank_account_number" in data.model_fields_set:
        container.bank_account_number = data.bank_account_number
    if "overdraft_limit" in data.model_fields_set:
        container.overdraft_limit = data.overdraft_limit
    if "locked" in data.model_fields_set:
        container.locked = data.locked
    if "credit_limit" in data.model_fields_set:
        container.credit_limit = data.credit_limit
    if "allow_withdrawals" in data.model_fields_set:
        container.allow_withdrawals = data.allow_withdrawals
    if "interest_rate" in data.model_fields_set:
        container.interest_rate = data.interest_rate
    if "interest_frequency" in data.model_fields_set:
        container.interest_frequency = data.interest_frequency
    if "required_payment" in data.model_fields_set:
        container.required_payment = data.required_payment

    container.updated_by = user_id

    db.commit()
    db.refresh(container)

    return container


def soft_delete_container(
    db: Session,
    budget_id: uuid.UUID,
    container_id: uuid.UUID,
) -> bool:
    """
    Soft delete a container.

    Args:
        db: Database session
        budget_id: Budget ID (for authorization check)
        container_id: Container ID to delete

    Returns:
        True if container was deleted, False if not found or not in budget
    """
    container = get_container_by_id(db, budget_id, container_id)
    if not container:
        return False

    container.deleted_at = datetime.now(UTC)
    db.commit()

    return True
