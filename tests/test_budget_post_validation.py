"""Tests for budget post validation logic."""

import pytest
from datetime import datetime, UTC
from uuid import uuid4

from sqlalchemy.orm import Session

from api.models.budget import Budget
from api.models.account import Account, AccountPurpose, AccountDatasource
from api.models.budget_post import BudgetPostDirection, BudgetPostType
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
def normal_account(db: Session, test_budget: Budget, test_user: User) -> Account:
    """Create a NORMAL account."""
    account = Account(
        budget_id=test_budget.id,
        name="Checking Account",
        purpose=AccountPurpose.NORMAL,
        datasource=AccountDatasource.BANK,
        currency="DKK",
        starting_balance=100000,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@pytest.fixture
def normal_account2(db: Session, test_budget: Budget, test_user: User) -> Account:
    """Create a second NORMAL account."""
    account = Account(
        budget_id=test_budget.id,
        name="Second Checking",
        purpose=AccountPurpose.NORMAL,
        datasource=AccountDatasource.BANK,
        currency="DKK",
        starting_balance=0,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@pytest.fixture
def savings_account(db: Session, test_budget: Budget, test_user: User) -> Account:
    """Create a SAVINGS account."""
    account = Account(
        budget_id=test_budget.id,
        name="Savings Account",
        purpose=AccountPurpose.SAVINGS,
        datasource=AccountDatasource.BANK,
        currency="DKK",
        starting_balance=50000,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@pytest.fixture
def loan_account(db: Session, test_budget: Budget, test_user: User) -> Account:
    """Create a LOAN account."""
    account = Account(
        budget_id=test_budget.id,
        name="Car Loan",
        purpose=AccountPurpose.LOAN,
        datasource=AccountDatasource.VIRTUAL,
        currency="DKK",
        starting_balance=-200000,
        created_by=test_user.id,
        updated_by=test_user.id,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


class TestIncomeExpenseValidation:
    """Test validation for income/expense budget posts."""

    def test_income_requires_category(
        self, db: Session, test_budget: Budget, test_user: User, normal_account: Account
    ):
        """Income budget posts require a category_path."""
        with pytest.raises(BudgetPostValidationError, match="income budget posts require a category_path"):
            create_budget_post(
                db=db,
                budget_id=test_budget.id,
                user_id=test_user.id,
                direction=BudgetPostDirection.INCOME,
                post_type=BudgetPostType.FIXED,
                category_path=None,  # Missing category_path
                account_ids=[str(normal_account.id)],
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
        self, db: Session, test_budget: Budget, test_user: User, normal_account: Account
    ):
        """Expense budget posts require a category_path."""
        with pytest.raises(BudgetPostValidationError, match="expense budget posts require a category_path"):
            create_budget_post(
                db=db,
                budget_id=test_budget.id,
                user_id=test_user.id,
                direction=BudgetPostDirection.EXPENSE,
                post_type=BudgetPostType.FIXED,
                category_path=None,  # Missing category_path
                account_ids=[str(normal_account.id)],
                amount_patterns=[
                    {
                        "amount": 500000,
                        "start_date": "2026-01-01",
                        "end_date": None,
                    }
                ],
            )

    def test_income_requires_account_ids(
        self, db: Session, test_budget: Budget, test_user: User
    ):
        """Income budget posts require at least one account_id."""
        with pytest.raises(BudgetPostValidationError, match="income budget posts require at least one account_id"):
            create_budget_post(
                db=db,
                budget_id=test_budget.id,
                user_id=test_user.id,
                direction=BudgetPostDirection.INCOME,
                post_type=BudgetPostType.FIXED,
                category_path=["Indtægt", "Løn"],
                display_order=[0, 0],
                account_ids=[],  # Empty list not allowed
                amount_patterns=[
                    {
                        "amount": 3000000,
                        "start_date": "2026-01-01",
                        "end_date": None,
                    }
                ],
            )

    def test_expense_allows_single_savings_account(
        self, db: Session, test_budget: Budget, test_user: User, savings_account: Account
    ):
        """Expense post can have savings account in pool (max 1 non-normal allowed)."""
        budget_post = create_budget_post(
            db=db,
            budget_id=test_budget.id,
            user_id=test_user.id,
            direction=BudgetPostDirection.EXPENSE,
            post_type=BudgetPostType.FIXED,
            category_path=["Udgift", "Opsparing"],
            display_order=[0, 0],
            account_ids=[str(savings_account.id)],
            amount_patterns=[
                {
                    "amount": 100000,
                    "start_date": "2026-01-01",
                    "end_date": None,
                }
            ],
        )

        assert budget_post is not None
        assert budget_post.account_ids == [str(savings_account.id)]

    def test_expense_rejects_multiple_non_normal_accounts(
        self, db: Session, test_budget: Budget, test_user: User, savings_account: Account, loan_account: Account
    ):
        """Expense post cannot have more than 1 non-NORMAL account in pool."""
        with pytest.raises(BudgetPostValidationError, match="At most one non-normal account"):
            create_budget_post(
                db=db,
                budget_id=test_budget.id,
                user_id=test_user.id,
                direction=BudgetPostDirection.EXPENSE,
                post_type=BudgetPostType.FIXED,
                category_path=["Udgift", "Test"],
                display_order=[0, 0],
                account_ids=[str(savings_account.id), str(loan_account.id)],  # 2 non-normal
                amount_patterns=[
                    {
                        "amount": 100000,
                        "start_date": "2026-01-01",
                        "end_date": None,
                    }
                ],
            )

    def test_via_account_must_be_normal(
        self, db: Session, test_budget: Budget, test_user: User, normal_account: Account, savings_account: Account
    ):
        """via_account_id must reference a NORMAL account."""
        with pytest.raises(BudgetPostValidationError, match="via_account_id must reference a NORMAL account"):
            create_budget_post(
                db=db,
                budget_id=test_budget.id,
                user_id=test_user.id,
                direction=BudgetPostDirection.EXPENSE,
                post_type=BudgetPostType.FIXED,
                category_path=["Udgift", "Test"],
                display_order=[0, 0],
                account_ids=[str(normal_account.id)],
                via_account_id=savings_account.id,  # SAVINGS not allowed as via
                amount_patterns=[
                    {
                        "amount": 100000,
                        "start_date": "2026-01-01",
                        "end_date": None,
                    }
                ],
            )

    def test_via_account_cannot_be_in_pool(
        self, db: Session, test_budget: Budget, test_user: User, normal_account: Account, normal_account2: Account
    ):
        """via_account_id cannot be in account_ids pool."""
        with pytest.raises(BudgetPostValidationError, match="via_account_id cannot be in the account_ids pool"):
            create_budget_post(
                db=db,
                budget_id=test_budget.id,
                user_id=test_user.id,
                direction=BudgetPostDirection.EXPENSE,
                post_type=BudgetPostType.FIXED,
                category_path=["Udgift", "Test"],
                display_order=[0, 0],
                account_ids=[str(normal_account.id)],
                via_account_id=normal_account.id,  # Same as in pool
                amount_patterns=[
                    {
                        "amount": 100000,
                        "start_date": "2026-01-01",
                        "end_date": None,
                    }
                ],
            )

    def test_income_cannot_have_transfer_accounts(
        self, db: Session, test_budget: Budget, test_user: User, normal_account: Account
    ):
        """Income posts cannot have transfer_from/to_account_id."""
        with pytest.raises(BudgetPostValidationError, match="income budget posts cannot have transfer accounts"):
            create_budget_post(
                db=db,
                budget_id=test_budget.id,
                user_id=test_user.id,
                direction=BudgetPostDirection.INCOME,
                post_type=BudgetPostType.FIXED,
                category_path=["Indtægt", "Løn"],
                display_order=[0, 0],
                account_ids=[str(normal_account.id)],
                transfer_from_account_id=normal_account.id,  # Not allowed
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
        self, db: Session, test_budget: Budget, test_user: User, normal_account: Account, savings_account: Account
    ):
        """Cannot mix normal and non-normal accounts (mutual exclusivity)."""
        with pytest.raises(BudgetPostValidationError, match="Cannot mix normal and non-normal accounts"):
            create_budget_post(
                db=db,
                budget_id=test_budget.id,
                user_id=test_user.id,
                direction=BudgetPostDirection.EXPENSE,
                post_type=BudgetPostType.FIXED,
                category_path=["Udgift", "Test"],
                display_order=[0, 0],
                account_ids=[str(normal_account.id), str(savings_account.id)],  # Mixed!
                amount_patterns=[
                    {
                        "amount": 100000,
                        "start_date": "2026-01-01",
                        "end_date": None,
                    }
                ],
            )

    def test_income_accepts_multiple_normal_accounts(
        self, db: Session, test_budget: Budget, test_user: User, normal_account: Account, normal_account2: Account
    ):
        """Multiple normal accounts are allowed."""
        budget_post = create_budget_post(
            db=db,
            budget_id=test_budget.id,
            user_id=test_user.id,
            direction=BudgetPostDirection.INCOME,
            post_type=BudgetPostType.FIXED,
            category_path=["Indtægt", "Løn"],
            display_order=[0, 0],
            account_ids=[str(normal_account.id), str(normal_account2.id)],
            amount_patterns=[
                {
                    "amount": 3000000,
                    "start_date": "2026-01-01",
                    "end_date": None,
                }
            ],
        )

        assert budget_post is not None
        assert len(budget_post.account_ids) == 2

    def test_expense_accepts_single_savings_account(
        self, db: Session, test_budget: Budget, test_user: User, savings_account: Account
    ):
        """Single non-normal account is allowed."""
        budget_post = create_budget_post(
            db=db,
            budget_id=test_budget.id,
            user_id=test_user.id,
            direction=BudgetPostDirection.EXPENSE,
            post_type=BudgetPostType.FIXED,
            category_path=["Udgift", "Opsparing"],
            display_order=[0, 0],
            account_ids=[str(savings_account.id)],
            amount_patterns=[
                {
                    "amount": 100000,
                    "start_date": "2026-01-01",
                    "end_date": None,
                }
            ],
        )

        assert budget_post is not None
        assert budget_post.account_ids == [str(savings_account.id)]

    def test_via_account_rejected_with_only_normal_accounts(
        self, db: Session, test_budget: Budget, test_user: User, normal_account: Account, normal_account2: Account
    ):
        """via_account_id is only allowed with non-normal accounts."""
        with pytest.raises(
            BudgetPostValidationError,
            match="via_account_id is only allowed when a non-normal account .* is in the account pool",
        ):
            create_budget_post(
                db=db,
                budget_id=test_budget.id,
                user_id=test_user.id,
                direction=BudgetPostDirection.EXPENSE,
                post_type=BudgetPostType.FIXED,
                category_path=["Udgift", "Test"],
                display_order=[0, 0],
                account_ids=[str(normal_account.id)],
                via_account_id=normal_account2.id,  # Not allowed with only normal accounts
                amount_patterns=[
                    {
                        "amount": 100000,
                        "start_date": "2026-01-01",
                        "end_date": None,
                    }
                ],
            )

    def test_via_account_accepted_with_savings_account(
        self, db: Session, test_budget: Budget, test_user: User, normal_account: Account, savings_account: Account
    ):
        """via_account_id is allowed when a non-normal account is in the pool."""
        budget_post = create_budget_post(
            db=db,
            budget_id=test_budget.id,
            user_id=test_user.id,
            direction=BudgetPostDirection.EXPENSE,
            post_type=BudgetPostType.FIXED,
            category_path=["Udgift", "Opsparing"],
            display_order=[0, 0],
            account_ids=[str(savings_account.id)],
            via_account_id=normal_account.id,  # Allowed with savings account
            amount_patterns=[
                {
                    "amount": 100000,
                    "start_date": "2026-01-01",
                    "end_date": None,
                }
            ],
        )

        assert budget_post is not None
        assert budget_post.via_account_id == normal_account.id

    def test_update_rejects_adding_via_account_to_normal_only_pool(
        self, db: Session, test_budget: Budget, test_user: User, normal_account: Account, normal_account2: Account
    ):
        """Updating to add via_account_id should fail if only normal accounts in pool."""
        # Create budget post with only normal accounts
        budget_post = create_budget_post(
            db=db,
            budget_id=test_budget.id,
            user_id=test_user.id,
            direction=BudgetPostDirection.EXPENSE,
            post_type=BudgetPostType.FIXED,
            category_path=["Udgift", "Test"],
            display_order=[0, 0],
            account_ids=[str(normal_account.id)],
            amount_patterns=[
                {
                    "amount": 100000,
                    "start_date": "2026-01-01",
                    "end_date": None,
                }
            ],
        )

        assert budget_post is not None

        # Try to update and add via_account_id - should fail
        with pytest.raises(
            BudgetPostValidationError,
            match="via_account_id is only allowed when a non-normal account .* is in the account pool",
        ):
            update_budget_post(
                db=db,
                post_id=budget_post.id,
                budget_id=test_budget.id,
                user_id=test_user.id,
                via_account_id=normal_account2.id,
            )

    def test_update_rejects_changing_to_normal_accounts_while_keeping_via_account(
        self, db: Session, test_budget: Budget, test_user: User, normal_account: Account, normal_account2: Account, savings_account: Account
    ):
        """Updating account_ids to only normal should fail if via_account_id is set."""
        # Create budget post with savings account and via_account
        budget_post = create_budget_post(
            db=db,
            budget_id=test_budget.id,
            user_id=test_user.id,
            direction=BudgetPostDirection.EXPENSE,
            post_type=BudgetPostType.FIXED,
            category_path=["Udgift", "Opsparing"],
            display_order=[0, 0],
            account_ids=[str(savings_account.id)],
            via_account_id=normal_account.id,
            amount_patterns=[
                {
                    "amount": 100000,
                    "start_date": "2026-01-01",
                    "end_date": None,
                }
            ],
        )

        assert budget_post is not None

        # Try to update account_ids to only normal accounts (keeping via_account_id) - should fail
        with pytest.raises(
            BudgetPostValidationError,
            match="via_account_id is only allowed when a non-normal account .* is in the account pool",
        ):
            update_budget_post(
                db=db,
                post_id=budget_post.id,
                budget_id=test_budget.id,
                user_id=test_user.id,
                account_ids=[str(normal_account2.id)],  # Change to only normal, but via_account_id still set
            )


class TestTransferValidation:
    """Test validation for transfer budget posts."""

    def test_transfer_forbids_category_path(
        self, db: Session, test_budget: Budget, test_user: User, normal_account: Account, normal_account2: Account
    ):
        """Transfer budget posts cannot have a category_path."""
        with pytest.raises(BudgetPostValidationError, match="Transfer budget posts cannot have a category_path"):
            create_budget_post(
                db=db,
                budget_id=test_budget.id,
                user_id=test_user.id,
                direction=BudgetPostDirection.TRANSFER,
                post_type=BudgetPostType.FIXED,
                category_path=["Udgift", "Mad"],  # Not allowed
                display_order=[0, 0],
                transfer_from_account_id=normal_account.id,
                transfer_to_account_id=normal_account2.id,
                amount_patterns=[
                    {
                        "amount": 100000,
                        "start_date": "2026-01-01",
                        "end_date": None,
                    }
                ],
            )

    def test_transfer_forbids_account_ids(
        self, db: Session, test_budget: Budget, test_user: User, normal_account: Account, normal_account2: Account
    ):
        """Transfer budget posts cannot have account_ids."""
        with pytest.raises(BudgetPostValidationError, match="Transfer budget posts cannot have account_ids"):
            create_budget_post(
                db=db,
                budget_id=test_budget.id,
                user_id=test_user.id,
                direction=BudgetPostDirection.TRANSFER,
                post_type=BudgetPostType.FIXED,
                account_ids=[str(normal_account.id)],  # Not allowed
                transfer_from_account_id=normal_account.id,
                transfer_to_account_id=normal_account2.id,
                amount_patterns=[
                    {
                        "amount": 100000,
                        "start_date": "2026-01-01",
                        "end_date": None,
                    }
                ],
            )

    def test_transfer_forbids_via_account_id(
        self, db: Session, test_budget: Budget, test_user: User, normal_account: Account, normal_account2: Account
    ):
        """Transfer budget posts cannot have via_account_id."""
        with pytest.raises(BudgetPostValidationError, match="Transfer budget posts cannot have via_account_id"):
            create_budget_post(
                db=db,
                budget_id=test_budget.id,
                user_id=test_user.id,
                direction=BudgetPostDirection.TRANSFER,
                post_type=BudgetPostType.FIXED,
                via_account_id=normal_account.id,  # Not allowed
                transfer_from_account_id=normal_account.id,
                transfer_to_account_id=normal_account2.id,
                amount_patterns=[
                    {
                        "amount": 100000,
                        "start_date": "2026-01-01",
                        "end_date": None,
                    }
                ],
            )

    def test_transfer_requires_from_account(
        self, db: Session, test_budget: Budget, test_user: User, normal_account: Account
    ):
        """Transfer budget posts require transfer_from_account_id."""
        with pytest.raises(BudgetPostValidationError, match="Transfer budget posts require transfer_from_account_id"):
            create_budget_post(
                db=db,
                budget_id=test_budget.id,
                user_id=test_user.id,
                direction=BudgetPostDirection.TRANSFER,
                post_type=BudgetPostType.FIXED,
                transfer_from_account_id=None,  # Missing
                transfer_to_account_id=normal_account.id,
                amount_patterns=[
                    {
                        "amount": 100000,
                        "start_date": "2026-01-01",
                        "end_date": None,
                    }
                ],
            )

    def test_transfer_requires_to_account(
        self, db: Session, test_budget: Budget, test_user: User, normal_account: Account
    ):
        """Transfer budget posts require transfer_to_account_id."""
        with pytest.raises(BudgetPostValidationError, match="Transfer budget posts require transfer_to_account_id"):
            create_budget_post(
                db=db,
                budget_id=test_budget.id,
                user_id=test_user.id,
                direction=BudgetPostDirection.TRANSFER,
                post_type=BudgetPostType.FIXED,
                transfer_from_account_id=normal_account.id,
                transfer_to_account_id=None,  # Missing
                amount_patterns=[
                    {
                        "amount": 100000,
                        "start_date": "2026-01-01",
                        "end_date": None,
                    }
                ],
            )

    def test_transfer_accounts_must_be_different(
        self, db: Session, test_budget: Budget, test_user: User, normal_account: Account
    ):
        """Transfer from/to accounts must be different."""
        with pytest.raises(
            BudgetPostValidationError, match="transfer_from_account_id and transfer_to_account_id must be different"
        ):
            create_budget_post(
                db=db,
                budget_id=test_budget.id,
                user_id=test_user.id,
                direction=BudgetPostDirection.TRANSFER,
                post_type=BudgetPostType.FIXED,
                transfer_from_account_id=normal_account.id,
                transfer_to_account_id=normal_account.id,  # Same account
                amount_patterns=[
                    {
                        "amount": 100000,
                        "start_date": "2026-01-01",
                        "end_date": None,
                    }
                ],
            )

    def test_transfer_allows_any_account_types(
        self, db: Session, test_budget: Budget, test_user: User, normal_account: Account, savings_account: Account
    ):
        """Transfer posts can use any account types (NORMAL-only restriction removed)."""
        budget_post = create_budget_post(
            db=db,
            budget_id=test_budget.id,
            user_id=test_user.id,
            direction=BudgetPostDirection.TRANSFER,
            post_type=BudgetPostType.FIXED,
            transfer_from_account_id=normal_account.id,
            transfer_to_account_id=savings_account.id,  # SAVINGS is now allowed
            amount_patterns=[
                {
                    "amount": 100000,
                    "start_date": "2026-01-01",
                    "end_date": None,
                }
            ],
        )

        assert budget_post is not None
        assert budget_post.transfer_from_account_id == normal_account.id
        assert budget_post.transfer_to_account_id == savings_account.id


class TestAccumulateValidation:
    """Test validation for accumulate flag."""

    def test_accumulate_only_for_ceiling(
        self, db: Session, test_budget: Budget, test_user: User, normal_account: Account
    ):
        """Accumulate can only be true for CEILING type budget posts."""
        with pytest.raises(
            BudgetPostValidationError, match="accumulate can only be true for CEILING type budget posts"
        ):
            create_budget_post(
                db=db,
                budget_id=test_budget.id,
                user_id=test_user.id,
                direction=BudgetPostDirection.EXPENSE,
                post_type=BudgetPostType.FIXED,
                category_path=["Udgift", "Mad"],
                display_order=[0, 0],
                account_ids=[str(normal_account.id)],
                accumulate=True,  # Not allowed for FIXED
                amount_patterns=[
                    {
                        "amount": 500000,
                        "start_date": "2026-01-01",
                        "end_date": None,
                    }
                ],
            )

    def test_accumulate_allowed_for_ceiling(
        self, db: Session, test_budget: Budget, test_user: User, normal_account: Account
    ):
        """Accumulate can be true for CEILING type."""
        budget_post = create_budget_post(
            db=db,
            budget_id=test_budget.id,
            user_id=test_user.id,
            direction=BudgetPostDirection.EXPENSE,
            post_type=BudgetPostType.CEILING,
            category_path=["Udgift", "Mad"],
            display_order=[0, 0],
            account_ids=[str(normal_account.id)],
            accumulate=True,  # Allowed for CEILING
            amount_patterns=[
                {
                    "amount": 500000,
                    "start_date": "2026-01-01",
                    "end_date": None,
                }
            ],
        )
        assert budget_post is not None
        assert budget_post.accumulate is True


class TestAmountPatternAccountIdsValidation:
    """Test validation for amount pattern account_ids."""

    def test_pattern_account_ids_must_be_subset(
        self, db: Session, test_budget: Budget, test_user: User, normal_account: Account, normal_account2: Account
    ):
        """Pattern account_ids must be a subset of budget post's account_ids."""
        with pytest.raises(
            BudgetPostValidationError, match="Amount pattern account .* is not in budget post's account pool"
        ):
            create_budget_post(
                db=db,
                budget_id=test_budget.id,
                user_id=test_user.id,
                direction=BudgetPostDirection.INCOME,
                post_type=BudgetPostType.FIXED,
                category_path=["Indtægt", "Løn"],
                display_order=[0, 0],
                account_ids=[str(normal_account.id)],  # Only normal_account in pool
                amount_patterns=[
                    {
                        "amount": 3000000,
                        "start_date": "2026-01-01",
                        "end_date": None,
                        "account_ids": [str(normal_account2.id)],  # Not in pool!
                    }
                ],
            )

    def test_transfer_cannot_have_pattern_account_ids(
        self, db: Session, test_budget: Budget, test_user: User, normal_account: Account, normal_account2: Account
    ):
        """Transfer patterns cannot have account_ids."""
        with pytest.raises(
            BudgetPostValidationError, match="Amount patterns for transfer budget posts cannot have account_ids"
        ):
            create_budget_post(
                db=db,
                budget_id=test_budget.id,
                user_id=test_user.id,
                direction=BudgetPostDirection.TRANSFER,
                post_type=BudgetPostType.FIXED,
                transfer_from_account_id=normal_account.id,
                transfer_to_account_id=normal_account2.id,
                amount_patterns=[
                    {
                        "amount": 100000,
                        "start_date": "2026-01-01",
                        "end_date": None,
                        "account_ids": [str(normal_account.id)],  # Not allowed
                    }
                ],
            )


class TestValidBudgetPostCreation:
    """Test successful budget post creation with valid data."""

    def test_create_income_with_single_account(
        self, db: Session, test_budget: Budget, test_user: User, normal_account: Account
    ):
        """Successfully create income post with single account."""
        budget_post = create_budget_post(
            db=db,
            budget_id=test_budget.id,
            user_id=test_user.id,
            direction=BudgetPostDirection.INCOME,
            post_type=BudgetPostType.FIXED,
            category_path=["Indtægt", "Løn"],
            display_order=[0, 0],
            account_ids=[str(normal_account.id)],
            amount_patterns=[
                {
                    "amount": 3000000,
                    "start_date": "2026-01-01",
                    "end_date": None,
                    "recurrence_pattern": {"type": "monthly_fixed", "day_of_month": 25},
                }
            ],
        )

        assert budget_post is not None
        assert budget_post.direction == BudgetPostDirection.INCOME
        assert budget_post.category_path == ["Indtægt", "Løn"]
        assert budget_post.account_ids == [str(normal_account.id)]
        assert len(budget_post.amount_patterns) == 1

    def test_create_expense_with_multiple_normal_accounts(
        self, db: Session, test_budget: Budget, test_user: User, normal_account: Account, normal_account2: Account
    ):
        """Successfully create expense post with multiple NORMAL accounts in pool."""
        budget_post = create_budget_post(
            db=db,
            budget_id=test_budget.id,
            user_id=test_user.id,
            direction=BudgetPostDirection.EXPENSE,
            post_type=BudgetPostType.FIXED,
            category_path=["Udgift", "Mad"],
            display_order=[0, 0],
            account_ids=[str(normal_account.id), str(normal_account2.id)],
            amount_patterns=[
                {
                    "amount": 100000,
                    "start_date": "2026-01-01",
                    "end_date": None,
                }
            ],
        )

        assert budget_post is not None
        assert budget_post.direction == BudgetPostDirection.EXPENSE
        assert len(budget_post.account_ids) == 2

    def test_create_transfer(
        self, db: Session, test_budget: Budget, test_user: User, normal_account: Account, normal_account2: Account
    ):
        """Successfully create transfer post."""
        budget_post = create_budget_post(
            db=db,
            budget_id=test_budget.id,
            user_id=test_user.id,
            direction=BudgetPostDirection.TRANSFER,
            post_type=BudgetPostType.FIXED,
            transfer_from_account_id=normal_account.id,
            transfer_to_account_id=normal_account2.id,
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
        assert budget_post.account_ids is None
        assert budget_post.transfer_from_account_id == normal_account.id
        assert budget_post.transfer_to_account_id == normal_account2.id
