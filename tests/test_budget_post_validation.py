"""Tests for budget post validation logic."""

import pytest
from datetime import datetime, UTC
from uuid import uuid4

from sqlalchemy.orm import Session

from api.models.budget import Budget
from api.models.account import Account, AccountPurpose, AccountDatasource
from api.models.budget_post import BudgetPostDirection, BudgetPostType, CounterpartyType
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
        name="Savings Transfer Account",
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
                counterparty_type=CounterpartyType.EXTERNAL,
                amount_patterns=[
                    {
                        "amount": 3000000,
                        "start_date": "2026-01-01",
                        "end_date": None,
                        "recurrence_pattern": {"type": "monthly_fixed", "day_of_month": 25},
                        "account_ids": [str(normal_account.id)],
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
                counterparty_type=CounterpartyType.EXTERNAL,
                amount_patterns=[
                    {
                        "amount": 500000,
                        "start_date": "2026-01-01",
                        "end_date": None,
                        "account_ids": [str(normal_account.id)],
                    }
                ],
            )

    def test_income_requires_counterparty_type(
        self, db: Session, test_budget: Budget, test_user: User, normal_account: Account
    ):
        """Income budget posts require counterparty_type."""
        with pytest.raises(BudgetPostValidationError, match="income budget posts require a counterparty_type"):
            create_budget_post(
                db=db,
                budget_id=test_budget.id,
                user_id=test_user.id,
                direction=BudgetPostDirection.INCOME,
                post_type=BudgetPostType.FIXED,
                category_path=["Indtægt", "Løn"],
                display_order=[0, 0],
                counterparty_type=None,  # Missing counterparty_type
                amount_patterns=[
                    {
                        "amount": 3000000,
                        "start_date": "2026-01-01",
                        "end_date": None,
                        "account_ids": [str(normal_account.id)],
                    }
                ],
            )

    def test_income_with_account_counterparty_requires_account_id(
        self, db: Session, test_budget: Budget, test_user: User, normal_account: Account
    ):
        """Income with ACCOUNT counterparty requires counterparty_account_id."""
        with pytest.raises(
            BudgetPostValidationError, match="counterparty_account_id is required when counterparty_type is ACCOUNT"
        ):
            create_budget_post(
                db=db,
                budget_id=test_budget.id,
                user_id=test_user.id,
                direction=BudgetPostDirection.INCOME,
                post_type=BudgetPostType.FIXED,
                category_path=["Indtægt", "Løn"],
                display_order=[0, 0],
                counterparty_type=CounterpartyType.ACCOUNT,
                counterparty_account_id=None,  # Missing account
                amount_patterns=[
                    {
                        "amount": 3000000,
                        "start_date": "2026-01-01",
                        "end_date": None,
                        "account_ids": [str(normal_account.id)],
                    }
                ],
            )

    def test_income_with_account_counterparty_must_be_savings_or_loan(
        self, db: Session, test_budget: Budget, test_user: User, normal_account: Account
    ):
        """Counterparty account must have purpose SAVINGS or LOAN."""
        with pytest.raises(BudgetPostValidationError, match="Counterparty account must have purpose SAVINGS or LOAN"):
            create_budget_post(
                db=db,
                budget_id=test_budget.id,
                user_id=test_user.id,
                direction=BudgetPostDirection.INCOME,
                post_type=BudgetPostType.FIXED,
                category_path=["Indtægt", "Løn"],
                display_order=[0, 0],
                counterparty_type=CounterpartyType.ACCOUNT,
                counterparty_account_id=normal_account.id,  # NORMAL account not allowed
                amount_patterns=[
                    {
                        "amount": 3000000,
                        "start_date": "2026-01-01",
                        "end_date": None,
                        "account_ids": [str(normal_account.id)],
                    }
                ],
            )

    def test_income_with_external_counterparty_forbids_account_id(
        self, db: Session, test_budget: Budget, test_user: User, normal_account: Account, savings_account: Account
    ):
        """Income with EXTERNAL counterparty cannot have counterparty_account_id."""
        with pytest.raises(
            BudgetPostValidationError, match="counterparty_account_id must be null when counterparty_type is EXTERNAL"
        ):
            create_budget_post(
                db=db,
                budget_id=test_budget.id,
                user_id=test_user.id,
                direction=BudgetPostDirection.INCOME,
                post_type=BudgetPostType.FIXED,
                category_path=["Indtægt", "Løn"],
                display_order=[0, 0],
                counterparty_type=CounterpartyType.EXTERNAL,
                counterparty_account_id=savings_account.id,  # Should be null
                amount_patterns=[
                    {
                        "amount": 3000000,
                        "start_date": "2026-01-01",
                        "end_date": None,
                        "account_ids": [str(normal_account.id)],
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
                counterparty_type=CounterpartyType.EXTERNAL,
                transfer_from_account_id=normal_account.id,  # Not allowed
                amount_patterns=[
                    {
                        "amount": 3000000,
                        "start_date": "2026-01-01",
                        "end_date": None,
                        "account_ids": [str(normal_account.id)],
                    }
                ],
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

    def test_transfer_forbids_counterparty_type(
        self, db: Session, test_budget: Budget, test_user: User, normal_account: Account, normal_account2: Account
    ):
        """Transfer budget posts cannot have counterparty_type."""
        with pytest.raises(BudgetPostValidationError, match="Transfer budget posts cannot have a counterparty_type"):
            create_budget_post(
                db=db,
                budget_id=test_budget.id,
                user_id=test_user.id,
                direction=BudgetPostDirection.TRANSFER,
                post_type=BudgetPostType.FIXED,
                counterparty_type=CounterpartyType.EXTERNAL,  # Not allowed
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

    def test_transfer_accounts_must_be_normal(
        self, db: Session, test_budget: Budget, test_user: User, normal_account: Account, savings_account: Account
    ):
        """Transfer accounts must have purpose NORMAL."""
        with pytest.raises(
            BudgetPostValidationError, match="transfer_from_account_id must reference a NORMAL account"
        ):
            create_budget_post(
                db=db,
                budget_id=test_budget.id,
                user_id=test_user.id,
                direction=BudgetPostDirection.TRANSFER,
                post_type=BudgetPostType.FIXED,
                transfer_from_account_id=savings_account.id,  # SAVINGS not allowed
                transfer_to_account_id=normal_account.id,
                amount_patterns=[
                    {
                        "amount": 100000,
                        "start_date": "2026-01-01",
                        "end_date": None,
                    }
                ],
            )


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
                counterparty_type=CounterpartyType.EXTERNAL,
                accumulate=True,  # Not allowed for FIXED
                amount_patterns=[
                    {
                        "amount": 500000,
                        "start_date": "2026-01-01",
                        "end_date": None,
                        "account_ids": [str(normal_account.id)],
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
            counterparty_type=CounterpartyType.EXTERNAL,
            accumulate=True,  # Allowed for CEILING
            amount_patterns=[
                {
                    "amount": 500000,
                    "start_date": "2026-01-01",
                    "end_date": None,
                    "account_ids": [str(normal_account.id)],
                }
            ],
        )
        assert budget_post is not None
        assert budget_post.accumulate is True


class TestAmountPatternAccountIdsValidation:
    """Test validation for amount pattern account_ids."""

    def test_external_counterparty_requires_account_ids(
        self, db: Session, test_budget: Budget, test_user: User
    ):
        """Amount patterns for EXTERNAL counterparty must have account_ids."""
        with pytest.raises(
            BudgetPostValidationError,
            match="Amount patterns for income/expense with EXTERNAL counterparty must specify at least one account_id",
        ):
            create_budget_post(
                db=db,
                budget_id=test_budget.id,
                user_id=test_user.id,
                direction=BudgetPostDirection.INCOME,
                post_type=BudgetPostType.FIXED,
                category_path=["Indtægt", "Løn"],
                display_order=[0, 0],
                counterparty_type=CounterpartyType.EXTERNAL,
                amount_patterns=[
                    {
                        "amount": 3000000,
                        "start_date": "2026-01-01",
                        "end_date": None,
                        "account_ids": [],  # Empty not allowed
                    }
                ],
            )

    def test_account_counterparty_requires_exactly_one_account_id(
        self, db: Session, test_budget: Budget, test_user: User, normal_account: Account, normal_account2: Account, savings_account: Account
    ):
        """Amount patterns for ACCOUNT counterparty must have exactly one account_id."""
        with pytest.raises(
            BudgetPostValidationError,
            match="Amount patterns for income/expense with ACCOUNT counterparty must specify exactly one account_id",
        ):
            create_budget_post(
                db=db,
                budget_id=test_budget.id,
                user_id=test_user.id,
                direction=BudgetPostDirection.INCOME,
                post_type=BudgetPostType.FIXED,
                category_path=["Indtægt", "Løn"],
                display_order=[0, 0],
                counterparty_type=CounterpartyType.ACCOUNT,
                counterparty_account_id=savings_account.id,
                amount_patterns=[
                    {
                        "amount": 3000000,
                        "start_date": "2026-01-01",
                        "end_date": None,
                        "account_ids": [str(normal_account.id), str(normal_account2.id)],  # Too many
                    }
                ],
            )

    def test_pattern_account_must_be_normal(
        self, db: Session, test_budget: Budget, test_user: User, savings_account: Account
    ):
        """Amount pattern account_ids must reference NORMAL accounts."""
        with pytest.raises(
            BudgetPostValidationError, match="must be a NORMAL account for amount patterns"
        ):
            create_budget_post(
                db=db,
                budget_id=test_budget.id,
                user_id=test_user.id,
                direction=BudgetPostDirection.INCOME,
                post_type=BudgetPostType.FIXED,
                category_path=["Indtægt", "Løn"],
                display_order=[0, 0],
                counterparty_type=CounterpartyType.EXTERNAL,
                amount_patterns=[
                    {
                        "amount": 3000000,
                        "start_date": "2026-01-01",
                        "end_date": None,
                        "account_ids": [str(savings_account.id)],  # SAVINGS not allowed
                    }
                ],
            )

    def test_transfer_cannot_have_account_ids(
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

    def test_create_income_with_external_counterparty(
        self, db: Session, test_budget: Budget, test_user: User, normal_account: Account
    ):
        """Successfully create income post with EXTERNAL counterparty."""
        budget_post = create_budget_post(
            db=db,
            budget_id=test_budget.id,
            user_id=test_user.id,
            direction=BudgetPostDirection.INCOME,
            post_type=BudgetPostType.FIXED,
            category_path=["Indtægt", "Løn"],
                display_order=[0, 0],
            counterparty_type=CounterpartyType.EXTERNAL,
            amount_patterns=[
                {
                    "amount": 3000000,
                    "start_date": "2026-01-01",
                    "end_date": None,
                    "recurrence_pattern": {"type": "monthly_fixed", "day_of_month": 25},
                    "account_ids": [str(normal_account.id)],
                }
            ],
        )

        assert budget_post is not None
        assert budget_post.direction == BudgetPostDirection.INCOME
        assert budget_post.category_path == ["Indtægt", "Løn"]
        assert budget_post.counterparty_type == CounterpartyType.EXTERNAL
        assert len(budget_post.amount_patterns) == 1

    def test_create_expense_with_account_counterparty(
        self, db: Session, test_budget: Budget, test_user: User, normal_account: Account, savings_account: Account
    ):
        """Successfully create expense post with ACCOUNT counterparty."""
        budget_post = create_budget_post(
            db=db,
            budget_id=test_budget.id,
            user_id=test_user.id,
            direction=BudgetPostDirection.EXPENSE,
            post_type=BudgetPostType.FIXED,
            category_path=["Udgift", "Mad"],
                display_order=[0, 0],
            counterparty_type=CounterpartyType.ACCOUNT,
            counterparty_account_id=savings_account.id,
            amount_patterns=[
                {
                    "amount": 100000,
                    "start_date": "2026-01-01",
                    "end_date": None,
                    "account_ids": [str(normal_account.id)],
                }
            ],
        )

        assert budget_post is not None
        assert budget_post.direction == BudgetPostDirection.EXPENSE
        assert budget_post.counterparty_type == CounterpartyType.ACCOUNT
        assert budget_post.counterparty_account_id == savings_account.id

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
        assert budget_post.counterparty_type is None
        assert budget_post.transfer_from_account_id == normal_account.id
        assert budget_post.transfer_to_account_id == normal_account2.id
