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
                category_path=["Indtægt"],
                display_order=[0],
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
                category_path=["Indtægt"],
                display_order=[0],
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

    def test_income_rejects_multiple_cashbox_containers(
        self, db: Session, test_budget: Budget, test_user: User, cashbox_container: Container, cashbox_container2: Container
    ):
        """Income posts must have exactly one container."""
        with pytest.raises(BudgetPostValidationError, match="exactly one container"):
            create_budget_post(
                db=db,
                budget_id=test_budget.id,
                user_id=test_user.id,
                direction=BudgetPostDirection.INCOME,
                category_path=["Indtægt"],
                display_order=[0],
                container_ids=[str(cashbox_container.id), str(cashbox_container2.id)],
                amount_patterns=[
                    {
                        "amount": 3000000,
                        "start_date": "2026-01-01",
                        "end_date": None,
                    }
                ],
            )

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
            match="error.budgetPost.viaRequiresNonCashbox",
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

    def test_update_clears_via_when_switching_to_cashbox(
        self, db: Session, test_budget: Budget, test_user: User,
        cashbox_container: Container, cashbox_container2: Container,
        piggybank_container: Container,
    ):
        """Updating to cashbox-only containers with via_container_id=None should succeed."""
        # Create with piggybank + via
        bp, _ = create_budget_post(
            db=db,
            budget_id=test_budget.id,
            user_id=test_user.id,
            direction=BudgetPostDirection.EXPENSE,
            category_path=["Via clear test"],
            display_order=[0],
            container_ids=[str(piggybank_container.id)],
            via_container_id=cashbox_container.id,
            amount_patterns=[{
                "amount": 10000,
                "start_date": "2026-01-01",
                "recurrence_pattern": {"type": "monthly_fixed", "day_of_month": 1},
                "container_ids": [str(piggybank_container.id)],
            }],
        )
        assert bp.via_container_id == cashbox_container.id

        # Update to cashbox-only, explicitly clearing via
        updated, _ = update_budget_post(
            db=db,
            post_id=bp.id,
            budget_id=test_budget.id,
            user_id=test_user.id,
            container_ids=[str(cashbox_container.id), str(cashbox_container2.id)],
            via_container_id=None,
            amount_patterns=[{
                "amount": 10000,
                "start_date": "2026-01-01",
                "recurrence_pattern": {"type": "monthly_fixed", "day_of_month": 1},
                "container_ids": [str(cashbox_container.id)],
            }],
        )
        assert updated is not None
        assert updated.via_container_id is None
        assert updated.container_ids == [str(cashbox_container.id), str(cashbox_container2.id)]

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
            match="error.budgetPost.viaRequiresNonCashbox",
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
            match="error.budgetPost.viaRequiresNonCashbox",
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
                category_path=["Indtægt"],
                display_order=[0],
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
            category_path=["Indtægt"],
            display_order=[0],
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
            category_path=["Indtægt"],
            display_order=[0],
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
        assert budget_post.category_path == ["Indtægt"]
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


class TestIncomeValidation:
    """Tests for income-specific validation rules."""

    def test_income_accepts_single_piggybank(
        self, db: Session, test_budget: Budget, test_user: User, piggybank_container: Container
    ):
        """Income posts can use a single piggybank container."""
        budget_post, _ = create_budget_post(
            db=db,
            budget_id=test_budget.id,
            user_id=test_user.id,
            direction=BudgetPostDirection.INCOME,
            category_path=["Freelance"],
            display_order=[0],
            container_ids=[str(piggybank_container.id)],
            amount_patterns=[{"amount": 500000, "start_date": "2026-01-01", "end_date": None}],
        )
        assert budget_post is not None
        assert budget_post.container_ids == [str(piggybank_container.id)]

    def test_income_accepts_single_debt(
        self, db: Session, test_budget: Budget, test_user: User, debt_container: Container
    ):
        """Income posts can use a single debt container."""
        budget_post, _ = create_budget_post(
            db=db,
            budget_id=test_budget.id,
            user_id=test_user.id,
            direction=BudgetPostDirection.INCOME,
            category_path=["Debt Paydown"],
            display_order=[0],
            container_ids=[str(debt_container.id)],
            amount_patterns=[{"amount": 100000, "start_date": "2026-01-01", "end_date": None}],
        )
        assert budget_post is not None
        assert budget_post.container_ids == [str(debt_container.id)]

    def test_income_rejects_child_under_income_post(
        self, db: Session, test_budget: Budget, test_user: User, cashbox_container: Container
    ):
        """Income posts cannot be nested under other income posts."""
        # Create parent income post
        create_budget_post(
            db=db,
            budget_id=test_budget.id,
            user_id=test_user.id,
            direction=BudgetPostDirection.INCOME,
            category_path=["Arbejdsindkomst"],
            display_order=[0],
            container_ids=[str(cashbox_container.id)],
            amount_patterns=[{"amount": 3000000, "start_date": "2026-01-01", "end_date": None}],
        )

        # Try to create child income post - should fail
        with pytest.raises(BudgetPostValidationError, match="cannot be nested under other income posts"):
            create_budget_post(
                db=db,
                budget_id=test_budget.id,
                user_id=test_user.id,
                direction=BudgetPostDirection.INCOME,
                category_path=["Arbejdsindkomst", "Grundløn"],
                display_order=[0, 0],
                container_ids=[str(cashbox_container.id)],
                amount_patterns=[{"amount": 2500000, "start_date": "2026-01-01", "end_date": None}],
            )

    def test_income_rejects_parent_of_existing_income(
        self, db: Session, test_budget: Budget, test_user: User, cashbox_container: Container
    ):
        """Cannot create income post that would be parent of existing income post."""
        # Create child income post first
        create_budget_post(
            db=db,
            budget_id=test_budget.id,
            user_id=test_user.id,
            direction=BudgetPostDirection.INCOME,
            category_path=["Arbejdsindkomst", "Grundløn"],
            display_order=[0, 0],
            container_ids=[str(cashbox_container.id)],
            amount_patterns=[{"amount": 2500000, "start_date": "2026-01-01", "end_date": None}],
        )

        # Try to create parent income post - should fail
        with pytest.raises(BudgetPostValidationError, match="cannot have children"):
            create_budget_post(
                db=db,
                budget_id=test_budget.id,
                user_id=test_user.id,
                direction=BudgetPostDirection.INCOME,
                category_path=["Arbejdsindkomst"],
                display_order=[0],
                container_ids=[str(cashbox_container.id)],
                amount_patterns=[{"amount": 3000000, "start_date": "2026-01-01", "end_date": None}],
            )

    def test_income_accepts_via_with_piggybank(
        self, db: Session, test_budget: Budget, test_user: User, piggybank_container: Container, cashbox_container: Container
    ):
        """Income posts can have via_container_id when using piggybank."""
        budget_post, _ = create_budget_post(
            db=db,
            budget_id=test_budget.id,
            user_id=test_user.id,
            direction=BudgetPostDirection.INCOME,
            category_path=["Freelance"],
            display_order=[0],
            container_ids=[str(piggybank_container.id)],
            via_container_id=cashbox_container.id,
            amount_patterns=[{"amount": 500000, "start_date": "2026-01-01", "end_date": None}],
        )
        assert budget_post is not None
        assert budget_post.via_container_id == cashbox_container.id

    def test_income_allows_deep_category_path(
        self, db: Session, test_budget: Budget, test_user: User, cashbox_container: Container
    ):
        """Income posts can have deep category paths when no conflicts exist."""
        budget_post, _ = create_budget_post(
            db=db,
            budget_id=test_budget.id,
            user_id=test_user.id,
            direction=BudgetPostDirection.INCOME,
            category_path=["Løn", "FirmaA", "Bonus"],
            display_order=[0, 0, 0],
            container_ids=[str(cashbox_container.id)],
            amount_patterns=[{"amount": 50000, "start_date": "2026-01-01", "end_date": None}],
        )
        assert budget_post is not None
        assert budget_post.category_path == ["Løn", "FirmaA", "Bonus"]

    def test_income_accepts_single_cashbox(
        self, db: Session, test_budget: Budget, test_user: User, cashbox_container: Container
    ):
        """Happy path: income with single cashbox works."""
        budget_post, _ = create_budget_post(
            db=db,
            budget_id=test_budget.id,
            user_id=test_user.id,
            direction=BudgetPostDirection.INCOME,
            category_path=["Løn"],
            display_order=[0],
            container_ids=[str(cashbox_container.id)],
            amount_patterns=[{"amount": 3000000, "start_date": "2026-01-01", "end_date": None}],
        )
        assert budget_post is not None
        assert len(budget_post.container_ids) == 1
        assert budget_post.category_path == ["Løn"]

    def test_income_rejects_multiple_containers_any_type(
        self, db: Session, test_budget: Budget, test_user: User, cashbox_container: Container, cashbox_container2: Container
    ):
        """Income posts must have exactly one container (any type)."""
        with pytest.raises(BudgetPostValidationError, match="exactly one container"):
            create_budget_post(
                db=db,
                budget_id=test_budget.id,
                user_id=test_user.id,
                direction=BudgetPostDirection.INCOME,
                category_path=["Løn"],
                display_order=[0],
                container_ids=[str(cashbox_container.id), str(cashbox_container2.id)],
                amount_patterns=[{"amount": 3000000, "start_date": "2026-01-01", "end_date": None}],
            )

    def test_income_update_rejects_multiple_containers(
        self, db: Session, test_budget: Budget, test_user: User, cashbox_container: Container, cashbox_container2: Container
    ):
        """Cannot update income post to have multiple containers."""
        budget_post, _ = create_budget_post(
            db=db,
            budget_id=test_budget.id,
            user_id=test_user.id,
            direction=BudgetPostDirection.INCOME,
            category_path=["Løn"],
            display_order=[0],
            container_ids=[str(cashbox_container.id)],
            amount_patterns=[{"amount": 3000000, "start_date": "2026-01-01", "end_date": None}],
        )

        with pytest.raises(BudgetPostValidationError, match="exactly one container"):
            update_budget_post(
                db=db,
                post_id=budget_post.id,
                budget_id=test_budget.id,
                user_id=test_user.id,
                container_ids=[str(cashbox_container.id), str(cashbox_container2.id)],
            )

    def test_income_update_rejects_creating_parent_child_relationship(
        self, db: Session, test_budget: Budget, test_user: User, cashbox_container: Container
    ):
        """Cannot update income post category_path to create parent-child relationship."""
        # Create first income post
        bp1, _ = create_budget_post(
            db=db,
            budget_id=test_budget.id,
            user_id=test_user.id,
            direction=BudgetPostDirection.INCOME,
            category_path=["Løn"],
            display_order=[0],
            container_ids=[str(cashbox_container.id)],
            amount_patterns=[{"amount": 3000000, "start_date": "2026-01-01", "end_date": None}],
        )

        # Create second income post
        bp2, _ = create_budget_post(
            db=db,
            budget_id=test_budget.id,
            user_id=test_user.id,
            direction=BudgetPostDirection.INCOME,
            category_path=["Bonus"],
            display_order=[0],
            container_ids=[str(cashbox_container.id)],
            amount_patterns=[{"amount": 50000, "start_date": "2026-01-01", "end_date": None}],
        )

        # Try to update bp2 to be child of bp1 - should fail
        with pytest.raises(BudgetPostValidationError, match="cannot be nested under other income posts"):
            update_budget_post(
                db=db,
                post_id=bp2.id,
                budget_id=test_budget.id,
                user_id=test_user.id,
                category_path=["Løn", "Bonus"],
            )


class TestCategoryPathRevalidation:
    """Tests for category_path update re-validation."""

    def test_update_category_path_revalidates_against_ancestor(
        self, db: Session, test_budget: Budget, test_user: User, cashbox_container: Container, cashbox_container2: Container
    ):
        """Moving a post under an ancestor re-validates container subset."""
        # Create ancestor with only cashbox_container
        ancestor, _ = create_budget_post(
            db=db,
            budget_id=test_budget.id,
            user_id=test_user.id,
            direction=BudgetPostDirection.EXPENSE,
            category_path=["Bolig"],
            display_order=[0],
            container_ids=[str(cashbox_container.id)],
            amount_patterns=[{"amount": 1000000, "start_date": "2026-01-01", "end_date": None}],
        )

        # Create a post with cashbox_container2 (different containers)
        child, _ = create_budget_post(
            db=db,
            budget_id=test_budget.id,
            user_id=test_user.id,
            direction=BudgetPostDirection.EXPENSE,
            category_path=["El"],
            display_order=[0],
            container_ids=[str(cashbox_container2.id)],
            amount_patterns=[{"amount": 200000, "start_date": "2026-01-01", "end_date": None}],
        )

        # Try to move "El" under "Bolig" → should fail because cashbox_container2 is not in ancestor's pool
        with pytest.raises(BudgetPostValidationError, match="subset of ancestor"):
            update_budget_post(
                db=db,
                post_id=child.id,
                budget_id=test_budget.id,
                user_id=test_user.id,
                category_path=["Bolig", "El"],
            )

    def test_update_category_path_cascades_to_new_descendants(
        self, db: Session, test_budget: Budget, test_user: User, cashbox_container: Container, cashbox_container2: Container
    ):
        """Moving a post cascades container narrowing to posts at the new path."""
        # Create an existing child that will become descendant of moved post
        existing_child, _ = create_budget_post(
            db=db,
            budget_id=test_budget.id,
            user_id=test_user.id,
            direction=BudgetPostDirection.EXPENSE,
            category_path=["Transport", "Bus"],
            display_order=[0, 0],
            container_ids=[str(cashbox_container.id), str(cashbox_container2.id)],
            amount_patterns=[{"amount": 50000, "start_date": "2026-01-01", "end_date": None}],
        )

        # Create a post "Transport" with only cashbox_container
        parent, affected = create_budget_post(
            db=db,
            budget_id=test_budget.id,
            user_id=test_user.id,
            direction=BudgetPostDirection.EXPENSE,
            category_path=["Transport"],
            display_order=[0],
            container_ids=[str(cashbox_container.id)],
            amount_patterns=[{"amount": 300000, "start_date": "2026-01-01", "end_date": None}],
        )

        # The existing child should have been cascaded
        db.refresh(existing_child)
        assert existing_child.container_ids == [str(cashbox_container.id)]
