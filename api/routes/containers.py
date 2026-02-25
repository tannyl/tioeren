"""Container routes."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.deps.auth import CurrentUser
from api.deps.database import get_db
from api.schemas.container import (
    ContainerCreate,
    ContainerUpdate,
    ContainerResponse,
    ContainerListResponse,
)
from api.services.container_service import (
    create_container,
    get_budget_containers,
    get_container_by_id,
    update_container,
    soft_delete_container,
)
from api.services.budget_service import get_budget_by_id


router = APIRouter(prefix="/budgets/{budget_id}/containers", tags=["containers"])


@router.get(
    "",
    response_model=ContainerListResponse,
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized to access this budget"},
        404: {"description": "Budget not found"},
    },
)
def list_containers(
    budget_id: str,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> ContainerListResponse:
    """
    List all containers for a budget.

    Returns all non-deleted containers. User must own the budget.
    """
    try:
        budget_uuid = uuid.UUID(budget_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found",
        )

    # Check budget ownership
    budget = get_budget_by_id(db, budget_uuid, current_user.id)
    if not budget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found",
        )

    containers = get_budget_containers(db, budget_uuid)

    return ContainerListResponse(
        data=[
            ContainerResponse(
                id=str(container.id),
                budget_id=str(container.budget_id),
                name=container.name,
                type=container.type,
                starting_balance=container.starting_balance,
                bank_name=container.bank_name,
                bank_account_name=container.bank_account_name,
                bank_reg_number=container.bank_reg_number,
                bank_account_number=container.bank_account_number,
                overdraft_limit=container.overdraft_limit,
                locked=container.locked,
                credit_limit=container.credit_limit,
                allow_withdrawals=container.allow_withdrawals,
                interest_rate=container.interest_rate,
                interest_frequency=container.interest_frequency,
                required_payment=container.required_payment,
                current_balance=container.starting_balance,  # TODO: Calculate with transactions
                created_at=container.created_at,
                updated_at=container.updated_at,
            )
            for container in containers
        ],
    )


@router.post(
    "",
    response_model=ContainerResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized to access this budget"},
        404: {"description": "Budget not found"},
        409: {"description": "Container with this name already exists in budget"},
        422: {"description": "Validation error"},
    },
)
def create_container_endpoint(
    budget_id: str,
    container_data: ContainerCreate,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> ContainerResponse:
    """
    Create a new container in a budget.

    Validates type-specific constraints and checks for duplicate names.
    """
    try:
        budget_uuid = uuid.UUID(budget_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found",
        )

    # Check budget ownership
    budget = get_budget_by_id(db, budget_uuid, current_user.id)
    if not budget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found",
        )

    # Create container
    try:
        container = create_container(
            db=db,
            budget_id=budget_uuid,
            data=container_data,
            user_id=current_user.id,
        )
    except ValueError as e:
        # Validation error (e.g., type-specific constraint violation)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )

    if not container:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Container with this name already exists in budget",
        )

    return ContainerResponse(
        id=str(container.id),
        budget_id=str(container.budget_id),
        name=container.name,
        type=container.type,
        starting_balance=container.starting_balance,
        bank_name=container.bank_name,
        bank_account_name=container.bank_account_name,
        bank_reg_number=container.bank_reg_number,
        bank_account_number=container.bank_account_number,
        overdraft_limit=container.overdraft_limit,
        locked=container.locked,
        credit_limit=container.credit_limit,
        allow_withdrawals=container.allow_withdrawals,
        interest_rate=container.interest_rate,
        interest_frequency=container.interest_frequency,
        required_payment=container.required_payment,
        current_balance=container.starting_balance,  # TODO: Calculate with transactions
        created_at=container.created_at,
        updated_at=container.updated_at,
    )


@router.get(
    "/{container_id}",
    response_model=ContainerResponse,
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized to access this budget"},
        404: {"description": "Budget or container not found"},
    },
)
def get_container(
    budget_id: str,
    container_id: str,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> ContainerResponse:
    """
    Get a single container by ID.

    Returns 404 if container not found, soft-deleted, or doesn't belong to budget.
    Returns 403 if user doesn't own the budget.
    """
    try:
        budget_uuid = uuid.UUID(budget_id)
        container_uuid = uuid.UUID(container_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget or container not found",
        )

    # Check budget ownership
    budget = get_budget_by_id(db, budget_uuid, current_user.id)
    if not budget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found",
        )

    # Get container
    container = get_container_by_id(db, budget_uuid, container_uuid)
    if not container:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Container not found",
        )

    return ContainerResponse(
        id=str(container.id),
        budget_id=str(container.budget_id),
        name=container.name,
        type=container.type,
        starting_balance=container.starting_balance,
        bank_name=container.bank_name,
        bank_account_name=container.bank_account_name,
        bank_reg_number=container.bank_reg_number,
        bank_account_number=container.bank_account_number,
        overdraft_limit=container.overdraft_limit,
        locked=container.locked,
        credit_limit=container.credit_limit,
        allow_withdrawals=container.allow_withdrawals,
        interest_rate=container.interest_rate,
        interest_frequency=container.interest_frequency,
        required_payment=container.required_payment,
        current_balance=container.starting_balance,  # TODO: Calculate with transactions
        created_at=container.created_at,
        updated_at=container.updated_at,
    )


@router.put(
    "/{container_id}",
    response_model=ContainerResponse,
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized to modify this budget"},
        404: {"description": "Budget or container not found"},
        409: {"description": "Container with this name already exists in budget"},
        422: {"description": "Validation error"},
    },
)
def update_container_endpoint(
    budget_id: str,
    container_id: str,
    container_data: ContainerUpdate,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> ContainerResponse:
    """
    Update a container.

    Only the budget owner can update containers.
    Returns 404 if container not found or soft-deleted.
    Returns 409 if name conflicts with another container in the budget.
    """
    try:
        budget_uuid = uuid.UUID(budget_id)
        container_uuid = uuid.UUID(container_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget or container not found",
        )

    # Check budget ownership
    budget = get_budget_by_id(db, budget_uuid, current_user.id)
    if not budget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found",
        )

    # Update container
    try:
        container = update_container(
            db=db,
            budget_id=budget_uuid,
            container_id=container_uuid,
            data=container_data,
            user_id=current_user.id,
        )
    except ValueError as e:
        # Validation error (e.g., type change attempt, type-specific constraint violation)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )

    if not container:
        # Check if it's a duplicate name issue by trying to get the original container
        original = get_container_by_id(db, budget_uuid, container_uuid)
        if original:
            # Container exists but update failed, likely due to duplicate name
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Container with this name already exists in budget",
            )
        else:
            # Container doesn't exist
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Container not found",
            )

    return ContainerResponse(
        id=str(container.id),
        budget_id=str(container.budget_id),
        name=container.name,
        type=container.type,
        starting_balance=container.starting_balance,
        bank_name=container.bank_name,
        bank_account_name=container.bank_account_name,
        bank_reg_number=container.bank_reg_number,
        bank_account_number=container.bank_account_number,
        overdraft_limit=container.overdraft_limit,
        locked=container.locked,
        credit_limit=container.credit_limit,
        allow_withdrawals=container.allow_withdrawals,
        interest_rate=container.interest_rate,
        interest_frequency=container.interest_frequency,
        required_payment=container.required_payment,
        current_balance=container.starting_balance,  # TODO: Calculate with transactions
        created_at=container.created_at,
        updated_at=container.updated_at,
    )


@router.delete(
    "/{container_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized to delete this container"},
        404: {"description": "Budget or container not found"},
    },
)
def delete_container(
    budget_id: str,
    container_id: str,
    current_user: CurrentUser,
    db: Session = Depends(get_db),
) -> None:
    """
    Soft delete a container.

    Only the budget owner can delete containers.
    Returns 404 if container not found or already deleted.
    """
    try:
        budget_uuid = uuid.UUID(budget_id)
        container_uuid = uuid.UUID(container_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget or container not found",
        )

    # Check budget ownership
    budget = get_budget_by_id(db, budget_uuid, current_user.id)
    if not budget:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found",
        )

    # Delete container
    success = soft_delete_container(db, budget_uuid, container_uuid)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Container not found",
        )
