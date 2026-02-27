"""Tests for budget post validation logic."""

import pytest
from datetime import datetime, UTC
from uuid import uuid4

from sqlalchemy.orm import Session

from api.models.budget import Budget
from api.models.container import Container, ContainerType
from api.models.budget_post import BudgetPostDirection
from api.models.user import User
from api.services.budget_post_service import (
    create_budget_post,
    update_budget_post,
    BudgetPostValidationError,
)


@pytest.fixture
def test_user(db: Session) -> User:
    """Create a test user."""
    user = User(
        email="budget_post_validation@example.com",
        password_hash="dummy_hash",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def test_budget(db: Session, test_user: User) -> Budget:
    """Create a test budget."""
    budget = Budget(
        name="Test Budget",
        owner_id=test_user.id,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db.add(budget)
    db.commit()
    db.refresh(budget)
    return budget


@pytest.fixture
def cashbox_container(db: Session, test_budget: Budget, test_user: User) -> Container:
    """Create a CASHBOX container."""
    container = Container(
        budget_id=test_budget.id,
        name="Checking Container",
        type=ContainerType.CASHBOX,
        starting_balance=100000,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db.add(container)
    db.commit()
    db.refresh(container)
    return container


@pytest.fixture
def cashbox_container2(db: Session, test_budget: Budget, test_user: User) -> Container:
    """Create a second CASHBOX container."""
    container = Container(
        budget_id=test_budget.id,
        name="Second Checking",
        type=ContainerType.CASHBOX,
        starting_balance=0,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db.add(container)
    db.commit()
    db.refresh(container)
    return container


@pytest.fixture
def piggybank_container(db: Session, test_budget: Budget, test_user: User) -> Container:
    """Create a PIGGYBANK container."""
    container = Container(
        budget_id=test_budget.id,
        name="Savings Container",
        type=ContainerType.PIGGYBANK,
        starting_balance=50000,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db.add(container)
    db.commit()
    db.refresh(container)
    return container


@pytest.fixture
def debt_container(db: Session, test_budget: Budget, test_user: User) -> Container:
    """Create a DEBT container."""
    container = Container(
        budget_id=test_budget.id,
        name="Car Loan",
        type=ContainerType.DEBT,
        starting_balance=-200000,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db.add(container)
    db.commit()
    db.refresh(container)
    return container


class TestIncomeExpenseValidation:
    """Test validation for income/expense budget posts."""

    def test_income_requires_category(
        self, db: Session, test_budget: Budget, test_user: User, cashbox_container: Container
    ):
        """Income budget posts require a category_path."""
        with pytest.raises(BudgetPostValidationError, match="income budget posts require a category_path"):
            create_budget_post(
                db=db,
                budget_id=test_budget.id,
                user_id=test_user.id,
                direction=BudgetPostDirection.INCOME,
                category_path=None,  # Missing category_path
                container_ids=[str(cashbox_container.id)],
                amount_patterns=[
                    {
                        "amount": 3000000,
                        "start_date": "2026-01-01",
                        "end_date": None,
                        "recurrence_pattern": {"type": "monthly_fixed", "day_of_month": 25},
                    }
                ],
            )

    def test_expense_requires_category(
        self, db: Session, test_budget: Budget, test_user: User, cashbox_container: Container
    ):
        """Expense budget posts require a category_path."""
        with pytest.raises(BudgetPostValidationError, match="expense budget posts require a category_path"):
            create_budget_post(
                db=db,
                budget_id=test_budget.id,
                user_id=test_user.id,
                direction=BudgetPostDirection.EXPENSE,
                category_path=None,  # Missing category_path
                container_ids=[str(cashbox_container.id)],
                amount_patterns=[
                    {
                        "amount": 500000,
                        "start_date": "2026-01-01",
                        "end_date": None,
                    }
                ],
            )

    def test_income_requires_container_ids(
        self, db: Session, test_budget: Budget, test_user: User
    ):
        """Income budget posts require at least one container_id."""
        with pytest.raises(BudgetPostValidationError, match="income budget posts require at least one container_id"):
            create_budget_post(
                db=db,
                budget_id=test_budget.id,
                user_id=test_user.id,
                direction=BudgetPostDirection.INCOME,
                category_path=["Indtægt", "Løn"],
                display_order=[0, 0],
                container_ids=[],  # Empty list not allowed
                amount_patterns=[
                    {
                        "amount": 3000000,
                        "start_date": "2026-01-01",
                        "end_date": None,
                    }
                ],
            )

    def test_expense_allows_single_piggybank_container(
        self, db: Session, test_budget: Budget, test_user: User, piggybank_container: Container
    ):
        """Expense post can have savings account in pool (max 1 non-normal allowed)."""
        budget_post, _ = create_budget_post(
            db=db,
            budget_id=test_budget.id,
            user_id=test_user.id,
            direction=BudgetPostDirection.EXPENSE,
            category_path=["Udgift", "Opsparing"],
            display_order=[0, 0],
            container_ids=[str(piggybank_container.id)],
            amount_patterns=[
                {
                    "amount": 100000,
                    "start_date": "2026-01-01",
                    "end_date": None,
                    "container_ids": [str(piggybank_container.id)],
                }
            ],
        )

        assert budget_post is not None
        assert budget_post.container_ids == [str(piggybank_container.id)]

    def test_expense_rejects_multiple_non_cashbox_containers(
        self, db: Session, test_budget: Budget, test_user: User, piggybank_container: Container, debt_container: Container
    ):
        """Expense post cannot have more than 1 non-NORMAL account in pool."""
        with pytest.raises(BudgetPostValidationError, match="At most one non-cashbox container"):
            create_budget_post(
                db=db,
                budget_id=test_budget.id,
                user_id=test_user.id,
                direction=BudgetPostDirection.EXPENSE,
                category_path=["Udgift", "Test"],
                display_order=[0, 0],
                container_ids=[str(piggybank_container.id), str(debt_container.id)],  # 2 non-normal
                amount_patterns=[
                    {
                        "amount": 100000,
                        "start_date": "2026-01-01",
                        "end_date": None,
                    }
                ],
            )

    def test_via_account_must_be_normal(
        self, db: Session, test_budget: Budget, test_user: User, cashbox_container: Container, piggybank_container: Container
    ):
        """via_container_id must reference a CASHBOX container."""
        with pytest.raises(BudgetPostValidationError, match="via_container_id must reference a CASHBOX container"):
            create_budget_post(
                db=db,
                budget_id=test_budget.id,
                user_id=test_user.id,
                direction=BudgetPostDirection.EXPENSE,
                category_path=["Udgift", "Test"],
                display_order=[0, 0],
                container_ids=[str(cashbox_container.id)],
                via_container_id=piggybank_container.id,  # SAVINGS not allowed as via
                amount_patterns=[
                    {
                        "amount": 100000,
                        "start_date": "2026-01-01",
                        "end_date": None,
                    }
                ],
            )

    def test_via_account_cannot_be_in_pool(
        self, db: Session, test_budget: Budget, test_user: User, cashbox_container: Container, cashbox_container2: Container
    ):
        """via_container_id cannot be in container_ids pool."""
        with pytest.raises(BudgetPostValidationError, match="via_container_id cannot be in the container_ids pool"):
            create_budget_post(
                db=db,
                budget_id=test_budget.id,
                user_id=test_user.id,
                direction=BudgetPostDirection.EXPENSE,
                category_path=["Udgift", "Test"],
                display_order=[0, 0],
                container_ids=[str(cashbox_container.id)],
                via_container_id=cashbox_container.id,  # Same as in pool
                amount_patterns=[
                    {
                        "amount": 100000,
                        "start_date": "2026-01-01",
                        "end_date": None,
                    }
                ],
            )

    def test_income_cannot_have_transfer_accounts(
        self, db: Session, test_budget: Budget, test_user: User, cashbox_container: Container
    ):
        """Income posts cannot have transfer_from/to_account_id."""
        with pytest.raises(BudgetPostValidationError, match="income budget posts cannot have transfer containers"):
            create_budget_post(
                db=db,
                budget_id=test_budget.id,
                user_id=test_user.id,
                direction=BudgetPostDirection.INCOME,
                category_path=["Indtægt", "Løn"],
                display_order=[0, 0],
                container_ids=[str(cashbox_container.id)],
                transfer_from_container_id=cashbox_container.id,  # Not allowed
                amount_patterns=[
                    {
                        "amount": 3000000,
                        "start_date": "2026-01-01",
                        "end_date": None,
                    }
                ],
            )


class TestAccountBindingMutualExclusivity:
    """Test mutual exclusivity and via-account restrictions for account bindings."""

    def test_expense_rejects_mixed_normal_and_savings(
        self, db: Session, test_budget: Budget, test_user: User, cashbox_container: Container, piggybank_container: Container
    ):
        """Cannot mix cashbox and non-cashbox containers (mutual exclusivity)."""
        with pytest.raises(BudgetPostValidationError, match="Cannot mix cashbox and non-cashbox containers"):
            create_budget_post(
                db=db,
                budget_id=test_budget.id,
                user_id=test_user.id,
                direction=BudgetPostDirection.EXPENSE,
                category_path=["Udgift", "Test"],
                display_order=[0, 0],
                container_ids=[str(cashbox_container.id), str(piggybank_container.id)],  # Mixed!
                amount_patterns=[
                    {
                        "amount": 100000,
                        "start_date": "2026-01-01",
                        "end_date": None,
                    }
                ],
            )

    def test_income_accepts_multiple_cashbox_containers(
        self, db: Session, test_budget: Budget, test_user: User, cashbox_container: Container, cashbox_container2: Container
    ):
        """Multiple normal accounts are allowed."""
        budget_post, _ = create_budget_post(
            db=db,
            budget_id=test_budget.id,
            user_id=test_user.id,
            direction=BudgetPostDirection.INCOME,
            category_path=["Indtægt", "Løn"],
            display_order=[0, 0],
            container_ids=[str(cashbox_container.id), str(cashbox_container2.id)],
            amount_patterns=[
                {
                    "amount": 3000000,
                    "start_date": "2026-01-01",
                    "end_date": None,
                    "container_ids": [str(cashbox_container.id), str(cashbox_container2.id)],
                }
            ],
        )

        assert budget_post is not None
        assert len(budget_post.container_ids) == 2

    def test_expense_accepts_single_piggybank_container(
        self, db: Session, test_budget: Budget, test_user: User, piggybank_container: Container
    ):
        """Single non-normal account is allowed."""
        budget_post, _ = create_budget_post(
            db=db,
            budget_id=test_budget.id,
            user_id=test_user.id,
            direction=BudgetPostDirection.EXPENSE,
            category_path=["Udgift", "Opsparing"],
            display_order=[0, 0],
            container_ids=[str(piggybank_container.id)],
            amount_patterns=[
                {
                    "amount": 100000,
                    "start_date": "2026-01-01",
                    "end_date": None,
                    "container_ids": [str(piggybank_container.id)],
                }
            ],
        )

        assert budget_post is not None
        assert budget_post.container_ids == [str(piggybank_container.id)]

    def test_via_account_rejected_with_only_cashbox_containers(
        self, db: Session, test_budget: Budget, test_user: User, cashbox_container: Container, cashbox_container2: Container
    ):
        """via_container_id is only allowed with non-normal accounts."""
        with pytest.raises(
            BudgetPostValidationError,
            match="via_container_id is only allowed when a non-cashbox container .* is in the container pool",
        ):
            create_budget_post(
                db=db,
                budget_id=test_budget.id,
                user_id=test_user.id,
                direction=BudgetPostDirection.EXPENSE,
                category_path=["Udgift", "Test"],
                display_order=[0, 0],
                container_ids=[str(cashbox_container.id)],
                via_container_id=cashbox_container2.id,  # Not allowed with only normal accounts
                amount_patterns=[
                    {
                        "amount": 100000,
                        "start_date": "2026-01-01",
                        "end_date": None,
                    }
                ],
            )

    def test_via_account_accepted_with_piggybank_container(
        self, db: Session, test_budget: Budget, test_user: User, cashbox_container: Container, piggybank_container: Container
    ):
        """via_container_id is allowed when a non-normal account is in the pool."""
        budget_post, _ = create_budget_post(
            db=db,
            budget_id=test_budget.id,
            user_id=test_user.id,
            direction=BudgetPostDirection.EXPENSE,
            category_path=["Udgift", "Opsparing"],
            display_order=[0, 0],
            container_ids=[str(piggybank_container.id)],
            via_container_id=cashbox_container.id,  # Allowed with savings account
            amount_patterns=[
                {
                    "amount": 100000,
                    "start_date": "2026-01-01",
                    "end_date": None,
                    "container_ids": [str(piggybank_container.id)],
                }
            ],
        )

        assert budget_post is not None
        assert budget_post.via_container_id == cashbox_container.id

    def test_update_rejects_adding_via_account_to_normal_only_pool(
        self, db: Session, test_budget: Budget, test_user: User, cashbox_container: Container, cashbox_container2: Container
    ):
        """Updating to add via_container_id should fail if only normal accounts in pool."""
        # Create budget post with only normal accounts
        budget_post, _ = create_budget_post(
            db=db,
            budget_id=test_budget.id,
            user_id=test_user.id,
            direction=BudgetPostDirection.EXPENSE,
            category_path=["Udgift", "Test"],
            display_order=[0, 0],
            container_ids=[str(cashbox_container.id)],
            amount_patterns=[
                {
                    "amount": 100000,
                    "start_date": "2026-01-01",
                    "end_date": None,
                    "container_ids": [str(cashbox_container.id)],
                }
            ],
        )

        assert budget_post is not None

        # Try to update and add via_container_id - should fail
        with pytest.raises(
            BudgetPostValidationError,
            match="via_container_id is only allowed when a non-cashbox container .* is in the container pool",
        ):
            update_budget_post(
                db=db,
                post_id=budget_post.id,
                budget_id=test_budget.id,
                user_id=test_user.id,
                via_container_id=cashbox_container2.id,
            )

    def test_update_rejects_changing_to_cashbox_containers_while_keeping_via_account(
        self, db: Session, test_budget: Budget, test_user: User, cashbox_container: Container, cashbox_container2: Container, piggybank_container: Container
    ):
        """Updating container_ids to only normal should fail if via_container_id is set."""
        # Create budget post with savings account and via_account
        budget_post, _ = create_budget_post(
            db=db,
            budget_id=test_budget.id,
            user_id=test_user.id,
            direction=BudgetPostDirection.EXPENSE,
            category_path=["Udgift", "Opsparing"],
            display_order=[0, 0],
            container_ids=[str(piggybank_container.id)],
            via_container_id=cashbox_container.id,
            amount_patterns=[
                {
                    "amount": 100000,
                    "start_date": "2026-01-01",
                    "end_date": None,
                    "container_ids": [str(piggybank_container.id)],
                }
            ],
        )

        assert budget_post is not None

        # Try to update container_ids to only normal accounts (keeping via_container_id) - should fail
        with pytest.raises(
            BudgetPostValidationError,
            match="via_container_id is only allowed when a non-cashbox container .* is in the container pool",
        ):
            update_budget_post(
                db=db,
                post_id=budget_post.id,
                budget_id=test_budget.id,
                user_id=test_user.id,
                container_ids=[str(cashbox_container2.id)],  # Change to only normal, but via_container_id still set
            )


class TestTransferValidation:
    """Test validation for transfer budget posts."""

    def test_transfer_forbids_category_path(
        self, db: Session, test_budget: Budget, test_user: User, cashbox_container: Container, cashbox_container2: Container
    ):
        """Transfer budget posts cannot have a category_path."""
        with pytest.raises(BudgetPostValidationError, match="Transfer budget posts cannot have a category_path"):
            create_budget_post(
                db=db,
                budget_id=test_budget.id,
                user_id=test_user.id,
                direction=BudgetPostDirection.TRANSFER,
                category_path=["Udgift", "Mad"],  # Not allowed
                display_order=[0, 0],
                transfer_from_container_id=cashbox_container.id,
                transfer_to_container_id=cashbox_container2.id,
                amount_patterns=[
                    {
                        "amount": 100000,
                        "start_date": "2026-01-01",
                        "end_date": None,
                    }
                ],
            )

    def test_transfer_forbids_container_ids(
        self, db: Session, test_budget: Budget, test_user: User, cashbox_container: Container, cashbox_container2: Container
    ):
        """Transfer budget posts cannot have container_ids."""
        with pytest.raises(BudgetPostValidationError, match="Transfer budget posts cannot have container_ids"):
            create_budget_post(
                db=db,
                budget_id=test_budget.id,
                user_id=test_user.id,
                direction=BudgetPostDirection.TRANSFER,
                container_ids=[str(cashbox_container.id)],  # Not allowed
                transfer_from_container_id=cashbox_container.id,
                transfer_to_container_id=cashbox_container2.id,
                amount_patterns=[
                    {
                        "amount": 100000,
                        "start_date": "2026-01-01",
                        "end_date": None,
                    }
                ],
            )

    def test_transfer_forbids_via_container_id(
        self, db: Session, test_budget: Budget, test_user: User, cashbox_container: Container, cashbox_container2: Container
    ):
        """Transfer budget posts cannot have via_container_id."""
        with pytest.raises(BudgetPostValidationError, match="Transfer budget posts cannot have via_container_id"):
            create_budget_post(
                db=db,
                budget_id=test_budget.id,
                user_id=test_user.id,
                direction=BudgetPostDirection.TRANSFER,
                via_container_id=cashbox_container.id,  # Not allowed
                transfer_from_container_id=cashbox_container.id,
                transfer_to_container_id=cashbox_container2.id,
                amount_patterns=[
                    {
                        "amount": 100000,
                        "start_date": "2026-01-01",
                        "end_date": None,
                    }
                ],
            )

    def test_transfer_requires_from_account(
        self, db: Session, test_budget: Budget, test_user: User, cashbox_container: Container
    ):
        """Transfer budget posts require transfer_from_container_id."""
        with pytest.raises(BudgetPostValidationError, match="Transfer budget posts require transfer_from_container_id"):
            create_budget_post(
                db=db,
                budget_id=test_budget.id,
                user_id=test_user.id,
                direction=BudgetPostDirection.TRANSFER,
                transfer_from_container_id=None,  # Missing
                transfer_to_container_id=cashbox_container.id,
                amount_patterns=[
                    {
                        "amount": 100000,
                        "start_date": "2026-01-01",
                        "end_date": None,
                    }
                ],
            )

    def test_transfer_requires_to_account(
        self, db: Session, test_budget: Budget, test_user: User, cashbox_container: Container
    ):
        """Transfer budget posts require transfer_to_container_id."""
        with pytest.raises(BudgetPostValidationError, match="Transfer budget posts require transfer_to_container_id"):
            create_budget_post(
                db=db,
                budget_id=test_budget.id,
                user_id=test_user.id,
                direction=BudgetPostDirection.TRANSFER,
                transfer_from_container_id=cashbox_container.id,
                transfer_to_container_id=None,  # Missing
                amount_patterns=[
                    {
                        "amount": 100000,
                        "start_date": "2026-01-01",
                        "end_date": None,
                    }
                ],
            )

    def test_transfer_accounts_must_be_different(
        self, db: Session, test_budget: Budget, test_user: User, cashbox_container: Container
    ):
        """Transfer from/to accounts must be different."""
        with pytest.raises(
            BudgetPostValidationError, match="transfer_from_container_id and transfer_to_container_id must be different"
        ):
            create_budget_post(
                db=db,
                budget_id=test_budget.id,
                user_id=test_user.id,
                direction=BudgetPostDirection.TRANSFER,
                transfer_from_container_id=cashbox_container.id,
                transfer_to_container_id=cashbox_container.id,  # Same account
                amount_patterns=[
                    {
                        "amount": 100000,
                        "start_date": "2026-01-01",
                        "end_date": None,
                    }
                ],
            )

    def test_transfer_allows_any_account_types(
        self, db: Session, test_budget: Budget, test_user: User, cashbox_container: Container, piggybank_container: Container
    ):
        """Transfer posts can use any account types (NORMAL-only restriction removed)."""
        budget_post, _ = create_budget_post(
            db=db,
            budget_id=test_budget.id,
            user_id=test_user.id,
            direction=BudgetPostDirection.TRANSFER,
            transfer_from_container_id=cashbox_container.id,
            transfer_to_container_id=piggybank_container.id,  # SAVINGS is now allowed
            amount_patterns=[
                {
                    "amount": 100000,
                    "start_date": "2026-01-01",
                    "end_date": None,
                }
            ],
        )

        assert budget_post is not None
        assert budget_post.transfer_from_container_id == cashbox_container.id
        assert budget_post.transfer_to_container_id == piggybank_container.id


class TestAccumulateValidation:
    """Test validation for accumulate flag."""

    def test_accumulate_allowed_for_expense(
        self, db: Session, test_budget: Budget, test_user: User, cashbox_container: Container
    ):
        """Accumulate can be set to true for expense budget posts."""
        budget_post, _ = create_budget_post(
            db=db,
            budget_id=test_budget.id,
            user_id=test_user.id,
            direction=BudgetPostDirection.EXPENSE,
            category_path=["Udgift", "Mad"],
            display_order=[0, 0],
            container_ids=[str(cashbox_container.id)],
            accumulate=True,
            amount_patterns=[
                {
                    "amount": 500000,
                    "start_date": "2026-01-01",
                    "end_date": None,
                    "container_ids": [str(cashbox_container.id)],
                }
            ],
        )
        assert budget_post is not None
        assert budget_post.accumulate is True

    def test_accumulate_rejected_for_income(
        self, db: Session, test_budget: Budget, test_user: User, cashbox_container: Container
    ):
        """Test that accumulate=True is rejected for income budget posts."""
        with pytest.raises(BudgetPostValidationError, match="accumulate can only be enabled for expense"):
            create_budget_post(
                db=db,
                budget_id=test_budget.id,
                user_id=test_user.id,
                direction=BudgetPostDirection.INCOME,
                category_path=["Indtægt", "Test"],
                display_order=[0, 0],
                container_ids=[str(cashbox_container.id)],
                accumulate=True,
                amount_patterns=[
                    {
                        "amount": 100000,
                        "start_date": "2026-01-01",
                        "recurrence_pattern": {"type": "monthly_fixed", "day_of_month": 1, "interval": 1},
                        "container_ids": [str(cashbox_container.id)],
                    }
                ],
            )

    def test_accumulate_rejected_for_transfer(
        self, db: Session, test_budget: Budget, test_user: User, cashbox_container: Container, cashbox_container2: Container
    ):
        """Test that accumulate=True is rejected for transfer budget posts."""
        with pytest.raises(BudgetPostValidationError, match="accumulate can only be enabled for expense"):
            create_budget_post(
                db=db,
                budget_id=test_budget.id,
                user_id=test_user.id,
                direction=BudgetPostDirection.TRANSFER,
                transfer_from_container_id=cashbox_container.id,
                transfer_to_container_id=cashbox_container2.id,
                accumulate=True,
                amount_patterns=[
                    {
                        "amount": 100000,
                        "start_date": "2026-01-01",
                        "recurrence_pattern": {"type": "monthly_fixed", "day_of_month": 1, "interval": 1},
                    }
                ],
            )

    def test_update_accumulate_rejected_for_income(
        self, db: Session, test_budget: Budget, test_user: User, cashbox_container: Container
    ):
        """Test that updating accumulate to True is rejected for income budget posts."""
        # Create income post with accumulate=False
        budget_post, _ = create_budget_post(
            db=db,
            budget_id=test_budget.id,
            user_id=test_user.id,
            direction=BudgetPostDirection.INCOME,
            category_path=["Indtægt", "Test"],
            display_order=[0, 0],
            container_ids=[str(cashbox_container.id)],
            accumulate=False,
            amount_patterns=[
                {
                    "amount": 100000,
                    "start_date": "2026-01-01",
                    "recurrence_pattern": {"type": "monthly_fixed", "day_of_month": 1, "interval": 1},
                    "container_ids": [str(cashbox_container.id)],
                }
            ],
        )

        assert budget_post is not None

        # Try to update accumulate to True - should fail
        with pytest.raises(BudgetPostValidationError, match="accumulate can only be enabled for expense"):
            update_budget_post(
                db=db,
                post_id=budget_post.id,
                budget_id=test_budget.id,
                user_id=test_user.id,
                accumulate=True,
            )


class TestAmountPatternAccountIdsValidation:
    """Test validation for amount pattern container_ids."""

    def test_pattern_container_ids_must_be_subset(
        self, db: Session, test_budget: Budget, test_user: User, cashbox_container: Container, cashbox_container2: Container
    ):
        """Pattern container_ids must be a subset of budget post's container_ids."""
        with pytest.raises(
            BudgetPostValidationError, match="Amount pattern container .* is not in budget post's container pool"
        ):
            create_budget_post(
                db=db,
                budget_id=test_budget.id,
                user_id=test_user.id,
                direction=BudgetPostDirection.INCOME,
                category_path=["Indtægt", "Løn"],
                display_order=[0, 0],
                container_ids=[str(cashbox_container.id)],  # Only cashbox_container in pool
                amount_patterns=[
                    {
                        "amount": 3000000,
                        "start_date": "2026-01-01",
                        "end_date": None,
                        "container_ids": [str(cashbox_container2.id)],  # Not in pool!
                    }
                ],
            )

    def test_transfer_cannot_have_pattern_container_ids(
        self, db: Session, test_budget: Budget, test_user: User, cashbox_container: Container, cashbox_container2: Container
    ):
        """Transfer patterns cannot have container_ids."""
        with pytest.raises(
            BudgetPostValidationError, match="Amount patterns for transfer budget posts cannot have container_ids"
        ):
            create_budget_post(
                db=db,
                budget_id=test_budget.id,
                user_id=test_user.id,
                direction=BudgetPostDirection.TRANSFER,
                transfer_from_container_id=cashbox_container.id,
                transfer_to_container_id=cashbox_container2.id,
                amount_patterns=[
                    {
                        "amount": 100000,
                        "start_date": "2026-01-01",
                        "end_date": None,
                        "container_ids": [str(cashbox_container.id)],  # Not allowed
                    }
                ],
            )

    def test_income_pattern_container_ids_cannot_be_null(
        self, db: Session, test_budget: Budget, test_user: User, cashbox_container: Container
    ):
        """Income pattern container_ids cannot be null."""
        with pytest.raises(
            BudgetPostValidationError, match="Amount pattern container_ids is required for income/expense"
        ):
            create_budget_post(
                db=db,
                budget_id=test_budget.id,
                user_id=test_user.id,
                direction=BudgetPostDirection.INCOME,
                category_path=["Indtægt", "Løn"],
                display_order=[0, 0],
                container_ids=[str(cashbox_container.id)],
                amount_patterns=[
                    {
                        "amount": 3000000,
                        "start_date": "2026-01-01",
                        "end_date": None,
                        "container_ids": None,  # Not allowed
                    }
                ],
            )

    def test_expense_pattern_container_ids_cannot_be_empty(
        self, db: Session, test_budget: Budget, test_user: User, cashbox_container: Container
    ):
        """Expense pattern container_ids cannot be empty list."""
        with pytest.raises(
            BudgetPostValidationError, match="Amount pattern container_ids is required for income/expense"
        ):
            create_budget_post(
                db=db,
                budget_id=test_budget.id,
                user_id=test_user.id,
                direction=BudgetPostDirection.EXPENSE,
                category_path=["Udgift", "Mad"],
                display_order=[0, 0],
                container_ids=[str(cashbox_container.id)],
                amount_patterns=[
                    {
                        "amount": 100000,
                        "start_date": "2026-01-01",
                        "end_date": None,
                        "container_ids": [],  # Not allowed
                    }
                ],
            )

    def test_income_pattern_with_valid_container_ids(
        self, db: Session, test_budget: Budget, test_user: User, cashbox_container: Container
    ):
        """Income pattern can have valid container_ids."""
        budget_post, _ = create_budget_post(
            db=db,
            budget_id=test_budget.id,
            user_id=test_user.id,
            direction=BudgetPostDirection.INCOME,
            category_path=["Indtægt", "Løn"],
            display_order=[0, 0],
            container_ids=[str(cashbox_container.id)],
            amount_patterns=[
                {
                    "amount": 3000000,
                    "start_date": "2026-01-01",
                    "end_date": None,
                    "container_ids": [str(cashbox_container.id)],
                }
            ],
        )

        assert budget_post is not None
        assert len(budget_post.amount_patterns) == 1
        assert budget_post.amount_patterns[0].container_ids == [str(cashbox_container.id)]


class TestValidBudgetPostCreation:
    """Test successful budget post creation with valid data."""

    def test_create_income_with_single_account(
        self, db: Session, test_budget: Budget, test_user: User, cashbox_container: Container
    ):
        """Successfully create income post with single account."""
        budget_post, _ = create_budget_post(
            db=db,
            budget_id=test_budget.id,
            user_id=test_user.id,
            direction=BudgetPostDirection.INCOME,
            category_path=["Indtægt", "Løn"],
            display_order=[0, 0],
            container_ids=[str(cashbox_container.id)],
            amount_patterns=[
                {
                    "amount": 3000000,
                    "start_date": "2026-01-01",
                    "end_date": None,
                    "recurrence_pattern": {"type": "monthly_fixed", "day_of_month": 25},
                    "container_ids": [str(cashbox_container.id)],
                }
            ],
        )

        assert budget_post is not None
        assert budget_post.direction == BudgetPostDirection.INCOME
        assert budget_post.category_path == ["Indtægt", "Løn"]
        assert budget_post.container_ids == [str(cashbox_container.id)]
        assert len(budget_post.amount_patterns) == 1

    def test_create_expense_with_multiple_cashbox_containers(
        self, db: Session, test_budget: Budget, test_user: User, cashbox_container: Container, cashbox_container2: Container
    ):
        """Successfully create expense post with multiple NORMAL accounts in pool."""
        budget_post, _ = create_budget_post(
            db=db,
            budget_id=test_budget.id,
            user_id=test_user.id,
            direction=BudgetPostDirection.EXPENSE,
            category_path=["Udgift", "Mad"],
            display_order=[0, 0],
            container_ids=[str(cashbox_container.id), str(cashbox_container2.id)],
            amount_patterns=[
                {
                    "amount": 100000,
                    "start_date": "2026-01-01",
                    "end_date": None,
                    "container_ids": [str(cashbox_container.id), str(cashbox_container2.id)],
                }
            ],
        )

        assert budget_post is not None
        assert budget_post.direction == BudgetPostDirection.EXPENSE
        assert len(budget_post.container_ids) == 2

    def test_create_transfer(
        self, db: Session, test_budget: Budget, test_user: User, cashbox_container: Container, cashbox_container2: Container
    ):
        """Successfully create transfer post."""
        budget_post, _ = create_budget_post(
            db=db,
            budget_id=test_budget.id,
            user_id=test_user.id,
            direction=BudgetPostDirection.TRANSFER,
            transfer_from_container_id=cashbox_container.id,
            transfer_to_container_id=cashbox_container2.id,
            amount_patterns=[
                {
                    "amount": 50000,
                    "start_date": "2026-01-01",
                    "end_date": None,
                    "recurrence_pattern": {"type": "monthly_fixed", "day_of_month": 1},
                }
            ],
        )

        assert budget_post is not None
        assert budget_post.direction == BudgetPostDirection.TRANSFER
        assert budget_post.category_path is None
        assert budget_post.container_ids is None
        assert budget_post.transfer_from_container_id == cashbox_container.id
        assert budget_post.transfer_to_container_id == cashbox_container2.id
