"""Forecast service for projecting balance N periods forward."""

import uuid
from dataclasses import dataclass
from datetime import date
from calendar import monthrange
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from api.models.container import Container, ContainerType
from api.models.transaction import Transaction
from api.models.budget_post import BudgetPost, BudgetPostDirection
from api.services.budget_post_service import expand_amount_patterns_to_occurrences


@dataclass
class MonthProjection:
    """Projection data for a single month."""

    month: str  # "2026-02", "2026-03", etc.
    start_balance: int  # øre
    expected_income: int  # øre
    expected_expenses: int  # øre
    end_balance: int  # øre


@dataclass
class ContainerMonthProjection:
    """Per-container projection for a single month."""

    container_id: str  # UUID as string
    container_name: str
    month: str  # "2026-02"
    start_balance: int  # øre
    min_balance: int  # øre (worst case)
    estimate_balance: int  # øre (point estimate)
    max_balance: int  # øre (best case)


@dataclass
class ForecastResult:
    """Complete forecast result with projections and insights."""

    projections: list[MonthProjection]
    container_projections: list[ContainerMonthProjection]
    lowest_point: dict  # {"month": "2026-04", "balance": 620000}
    next_large_expense: Optional[dict]  # {"name": "Insurance", "amount": -480000, "date": "2026-03-15"}


def _expand_single_pattern_to_total(
    pattern: "AmountPattern",
    month_start: date,
    month_end: date,
) -> int:
    """
    Expand a single amount pattern to total amount for the month.

    Uses the canonical recurrence expansion logic from budget_post_service
    to correctly handle all recurrence types (daily, weekly, monthly, yearly, etc.).

    Args:
        pattern: The amount pattern to expand
        month_start: Start of the month
        month_end: End of the month

    Returns:
        Total amount in øre for this pattern in the month (sum of all occurrences)
    """
    from api.services.budget_post_service import _expand_recurrence_pattern, adjust_to_bank_day
    from api.schemas.budget_post import RecurrenceType

    # Check if pattern is active in the month
    pattern_start = pattern.start_date
    pattern_end = pattern.end_date if pattern.end_date else date.max

    if pattern_end < month_start or pattern_start > month_end:
        return 0

    if not pattern.recurrence_pattern:
        return 0

    # Determine the effective date range for this pattern
    effective_start = max(month_start, pattern_start)
    effective_end = min(month_end, pattern_end)

    recurrence_type = pattern.recurrence_pattern.get("type")

    # Handle special cases (once and period_once)
    if recurrence_type == RecurrenceType.ONCE.value:
        # once: start_date IS the occurrence date
        if effective_start <= pattern_start <= effective_end:
            bank_day_adj = pattern.recurrence_pattern.get("bank_day_adjustment", "none")
            keep_in_month = pattern.recurrence_pattern.get("bank_day_keep_in_month", True)
            occ_date = adjust_to_bank_day(pattern_start, bank_day_adj, keep_in_month=keep_in_month) if bank_day_adj != "none" else pattern_start
            if occ_date <= effective_end:
                return pattern.amount
        return 0
    elif recurrence_type == RecurrenceType.PERIOD_ONCE.value:
        # period_once: start_date year+month determines the occurrence period
        occ_date = date(pattern_start.year, pattern_start.month, 1)
        # Check if occurrence is within the requested query range
        if month_start <= occ_date <= month_end:
            return pattern.amount
        return 0
    else:
        # Use canonical recurrence expansion for all other types
        occurrence_dates = _expand_recurrence_pattern(
            pattern.recurrence_pattern,
            effective_start,
            effective_end,
            pattern_start=pattern_start,
        )
        # Return total amount for all occurrences in this month
        return len(occurrence_dates) * pattern.amount


def compute_interval_for_post(
    post: BudgetPost,
    all_posts: list[BudgetPost],
    month_start: date,
    month_end: date,
    container_types: dict[uuid.UUID, ContainerType],
) -> dict[uuid.UUID, tuple[int, int, int]]:
    """
    Recursively compute min/max/estimate intervals for a budget post's contribution
    to each cashbox container for the given month.

    Args:
        post: The budget post to compute intervals for
        all_posts: All budget posts (for finding children)
        month_start: Start of the month
        month_end: End of the month
        container_types: Mapping of container ID to container type

    Returns:
        Dict mapping container_id -> (min_amount, estimate_amount, max_amount) in øre
    """
    # Find direct children of this post
    children = []
    if post.category_path:
        for other_post in all_posts:
            if other_post.id == post.id or not other_post.category_path:
                continue
            if other_post.direction != post.direction:
                continue

            # Check if other_post is a direct child (category_path is one level deeper and has this post as prefix)
            if (len(other_post.category_path) == len(post.category_path) + 1 and
                    other_post.category_path[:len(post.category_path)] == post.category_path):
                children.append(other_post)

    # Get all cashbox containers involved in this post's pool
    post_cashbox_ids = set()
    if post.container_ids:
        for cont_id_str in post.container_ids:
            try:
                cont_id = uuid.UUID(cont_id_str)
                if container_types.get(cont_id) == ContainerType.CASHBOX:
                    post_cashbox_ids.add(cont_id)
            except (ValueError, TypeError):
                continue

    # Initialize result dict for all cashbox containers in this post's pool
    result: dict[uuid.UUID, tuple[int, int, int]] = {
        cont_id: (0, 0, 0) for cont_id in post_cashbox_ids
    }

    if not children:
        # LEAF POST: Compute intervals directly from amount patterns
        # Compute total amount T across ALL active patterns in the month
        total_amount = 0
        for pattern in post.amount_patterns:
            pattern_total = _expand_single_pattern_to_total(pattern, month_start, month_end)
            total_amount += pattern_total

        if total_amount > 0 and post_cashbox_ids:
            # Distribute T across ALL of the post's cashbox containers
            n = len(post_cashbox_ids)
            sorted_cashbox_ids = sorted(post_cashbox_ids)

            for cont_id in post_cashbox_ids:
                if n == 1:
                    # Single container: min = max = estimate = T
                    result[cont_id] = (total_amount, total_amount, total_amount)
                else:
                    # Multiple containers: full ambiguity
                    # min = 0 (could all go elsewhere)
                    # max = T (could all come here)
                    # estimate = floor(T / N) with remainder to first container
                    base_amount = total_amount // n
                    is_first = (cont_id == sorted_cashbox_ids[0])
                    remainder = total_amount % n
                    estimate = base_amount + (remainder if is_first else 0)
                    result[cont_id] = (0, estimate, total_amount)

    else:
        # PARENT POST: Recursively compute children's intervals and apply ceiling
        # 1. Recursively compute children intervals
        children_totals: dict[uuid.UUID, tuple[int, int, int]] = {}
        for child in children:
            child_intervals = compute_interval_for_post(child, all_posts, month_start, month_end, container_types)
            for cont_id, (child_min, child_est, child_max) in child_intervals.items():
                if cont_id not in children_totals:
                    children_totals[cont_id] = (0, 0, 0)
                old_min, old_est, old_max = children_totals[cont_id]
                children_totals[cont_id] = (
                    old_min + child_min,
                    old_est + child_est,
                    old_max + child_max
                )

        # 2. Get ceiling C (sum of this post's own pattern amounts for the month)
        ceiling = 0
        has_active_pattern = False
        for pattern in post.amount_patterns:
            pattern_total = _expand_single_pattern_to_total(pattern, month_start, month_end)
            ceiling += pattern_total
            if pattern_total > 0:
                has_active_pattern = True

        # 2b. Determine active pattern cashbox IDs
        # If ANY pattern has amount > 0, then ALL post's cashbox containers are active
        active_pattern_cashbox_ids: set[uuid.UUID] = set()
        if has_active_pattern:
            active_pattern_cashbox_ids = post_cashbox_ids

        # 3. Apply ceiling formulas for each container
        # Compute children_est_total and unallocated remainder
        children_est_total = sum(children_totals.get(cid, (0, 0, 0))[1] for cid in post_cashbox_ids)
        unallocated = max(0, ceiling - children_est_total)

        # Compute effective upper bounds per container (children max + unallocated)
        effective_ub = {
            cid: children_totals.get(cid, (0, 0, 0))[2] + (unallocated if cid in active_pattern_cashbox_ids else 0)
            for cid in post_cashbox_ids
        }

        for cont_id in post_cashbox_ids:
            children_min, children_est, children_max = children_totals.get(cont_id, (0, 0, 0))

            # max: this container gets everything, others get their minimum from children
            sum_other_lb = sum(
                children_totals.get(other_id, (0, 0, 0))[0]
                for other_id in post_cashbox_ids
                if other_id != cont_id
            )
            max_amount = max(0, min(effective_ub[cont_id], ceiling - sum_other_lb))

            # min: other containers get their max, see what's left for this one
            sum_other_ub = sum(
                effective_ub[other_id]
                for other_id in post_cashbox_ids
                if other_id != cont_id
            )
            min_amount = max(children_min, ceiling - sum_other_ub)
            # Defensive clamp: ensure min <= max (data anomalies can cause inversion)
            min_amount = max(0, min(min_amount, max_amount))

            # Point estimate with ceiling
            # children_est_total is already computed above, reuse it

            if children_est_total == 0:
                # Equal distribution of C over active pattern's cashbox containers
                if cont_id in active_pattern_cashbox_ids and active_pattern_cashbox_ids:
                    n = len(active_pattern_cashbox_ids)
                    base = ceiling // n
                    sorted_ids = sorted(active_pattern_cashbox_ids)
                    remainder = ceiling % n
                    is_first = (cont_id == sorted_ids[0])
                    estimate_amount = base + (remainder if is_first else 0)
                else:
                    estimate_amount = 0
            elif children_est_total <= ceiling:
                # Keep children estimates + distribute remainder over active pattern containers
                rest = ceiling - children_est_total
                if cont_id in active_pattern_cashbox_ids and active_pattern_cashbox_ids:
                    n = len(active_pattern_cashbox_ids)
                    base = rest // n
                    sorted_ids = sorted(active_pattern_cashbox_ids)
                    remainder = rest % n
                    is_first = (cont_id == sorted_ids[0])
                    estimate_amount = children_est + base + (remainder if is_first else 0)
                else:
                    estimate_amount = children_est
            else:
                # Proportional reduction
                estimate_amount = (children_est * ceiling) // children_est_total
                # Handle rounding remainder: assign to largest contributor (tie-break: lowest UUID)
                total_assigned = sum(
                    (children_totals.get(cid, (0, 0, 0))[1] * ceiling) // children_est_total
                    for cid in post_cashbox_ids
                )
                remainder = ceiling - total_assigned
                # Sort by (contribution descending, UUID ascending)
                sorted_ids = sorted(post_cashbox_ids, key=lambda cid: (-children_totals.get(cid, (0, 0, 0))[1], cid))
                if cont_id == sorted_ids[0]:
                    estimate_amount += remainder

            result[cont_id] = (min_amount, estimate_amount, max_amount)

    return result


def get_current_balance(db: Session, budget_id: uuid.UUID) -> int:
    """
    Calculate current balance for cashbox containers in the budget.

    Args:
        db: Database session
        budget_id: Budget ID

    Returns:
        Current balance in øre (sum of starting_balance + transactions for cashbox containers)
    """
    # Get all cashbox containers with their transaction sums
    transaction_sum_subquery = (
        db.query(
            Transaction.container_id,
            func.coalesce(func.sum(Transaction.amount), 0).label("transaction_sum")
        )
        .filter(Transaction.container_id.in_(
            db.query(Container.id).filter(
                Container.budget_id == budget_id,
                Container.type == ContainerType.CASHBOX,
                Container.deleted_at.is_(None)
            )
        ))
        .group_by(Transaction.container_id)
        .subquery()
    )

    containers = (
        db.query(
            Container.starting_balance,
            func.coalesce(transaction_sum_subquery.c.transaction_sum, 0).label("transaction_sum")
        )
        .outerjoin(transaction_sum_subquery, Container.id == transaction_sum_subquery.c.container_id)
        .filter(
            Container.budget_id == budget_id,
            Container.type == ContainerType.CASHBOX,
            Container.deleted_at.is_(None)
        )
        .all()
    )

    total_balance = sum(cont.starting_balance + cont.transaction_sum for cont in containers)
    return total_balance


def get_per_container_balances(db: Session, budget_id: uuid.UUID) -> dict[uuid.UUID, int]:
    """
    Calculate current balance per cashbox container.

    Args:
        db: Database session
        budget_id: Budget ID

    Returns:
        Dict mapping container_id -> current balance in øre
    """
    transaction_sum_subquery = (
        db.query(
            Transaction.container_id,
            func.coalesce(func.sum(Transaction.amount), 0).label("transaction_sum")
        )
        .filter(Transaction.container_id.in_(
            db.query(Container.id).filter(
                Container.budget_id == budget_id,
                Container.type == ContainerType.CASHBOX,
                Container.deleted_at.is_(None)
            )
        ))
        .group_by(Transaction.container_id)
        .subquery()
    )

    containers = (
        db.query(
            Container.id,
            Container.starting_balance,
            func.coalesce(transaction_sum_subquery.c.transaction_sum, 0).label("transaction_sum")
        )
        .outerjoin(transaction_sum_subquery, Container.id == transaction_sum_subquery.c.container_id)
        .filter(
            Container.budget_id == budget_id,
            Container.type == ContainerType.CASHBOX,
            Container.deleted_at.is_(None)
        )
        .all()
    )

    return {cont.id: cont.starting_balance + cont.transaction_sum for cont in containers}


def calculate_forecast(db: Session, budget_id: uuid.UUID, months: int = 12) -> ForecastResult:
    """
    Calculate forecast projection for N months forward.

    Args:
        db: Database session
        budget_id: Budget ID to forecast
        months: Number of months to project forward (default 12)

    Returns:
        ForecastResult with monthly projections and insights
    """
    # Get current balance as starting point
    current_balance = get_current_balance(db, budget_id)

    # Get all active budget posts with their amount patterns and container relationships
    budget_posts = (
        db.query(BudgetPost)
        .options(
            joinedload(BudgetPost.amount_patterns),
            joinedload(BudgetPost.transfer_from_container),
            joinedload(BudgetPost.transfer_to_container),
        )
        .filter(
            BudgetPost.budget_id == budget_id,
            BudgetPost.deleted_at.is_(None)
        )
        .all()
    )

    # Load all containers for this budget (for type checking)
    containers = (
        db.query(Container)
        .filter(
            Container.budget_id == budget_id,
            Container.deleted_at.is_(None)
        )
        .all()
    )
    container_types = {cont.id: cont.type for cont in containers}

    # Filter to root-level income/expense posts with cashbox containers
    income_expense_posts = [
        post for post in budget_posts
        if post.direction in (BudgetPostDirection.INCOME, BudgetPostDirection.EXPENSE)
    ]

    # Filter to posts with at least one cashbox container
    cashbox_posts = []
    for post in income_expense_posts:
        if post.container_ids:
            has_cashbox = False
            for cont_id_str in post.container_ids:
                try:
                    cont_id = uuid.UUID(cont_id_str)
                    if container_types.get(cont_id) == ContainerType.CASHBOX:
                        has_cashbox = True
                        break
                except (ValueError, TypeError):
                    continue
            if has_cashbox:
                cashbox_posts.append(post)

    # Filter to root-level posts (posts with no ancestors in the hierarchy)
    root_posts = []
    for post in cashbox_posts:
        if not post.category_path:
            continue

        # Check if any other post is an ancestor (proper prefix of same direction)
        is_root = True
        for other_post in cashbox_posts:
            if other_post.id == post.id or not other_post.category_path:
                continue
            if other_post.direction != post.direction:
                continue

            # Check if other_post is an ancestor (proper prefix)
            if len(other_post.category_path) < len(post.category_path):
                if post.category_path[:len(other_post.category_path)] == other_post.category_path:
                    is_root = False
                    break

        if is_root:
            root_posts.append(post)

    # Get transfer posts
    transfer_posts = [
        post for post in budget_posts
        if post.direction == BudgetPostDirection.TRANSFER
    ]

    # Get per-container starting balances
    container_balances = get_per_container_balances(db, budget_id)

    # Get container names for per-container projections
    container_names = {cont.id: cont.name for cont in containers if cont.type == ContainerType.CASHBOX}

    # Generate projections for each month
    projections = []
    container_projections = []
    today = date.today()
    running_balance = current_balance

    # Track running balances per container (separate for min/est/max)
    running_container_min = container_balances.copy()
    running_container_est = container_balances.copy()
    running_container_max = container_balances.copy()

    # Track for insights
    lowest_balance = current_balance
    lowest_month = None
    next_large_expense = None
    large_expenses = []  # Track expenses in next 3 months for insights

    for month_offset in range(months):
        # Calculate target month
        year = today.year
        month = today.month + month_offset

        # Handle year overflow
        while month > 12:
            month -= 12
            year += 1

        # Calculate month date range
        month_start = date(year, month, 1)
        _, last_day = monthrange(year, month)
        month_end = date(year, month, last_day)
        month_str = month_start.strftime("%Y-%m")

        # Start balance is the running balance from previous month
        start_balance = running_balance

        # Generate expected transactions for this month
        expected_income = 0
        expected_expenses = 0

        # Per-container intervals for this month
        container_min_income: dict[uuid.UUID, int] = {cont_id: 0 for cont_id in container_balances}
        container_est_income: dict[uuid.UUID, int] = {cont_id: 0 for cont_id in container_balances}
        container_max_income: dict[uuid.UUID, int] = {cont_id: 0 for cont_id in container_balances}
        container_min_expense: dict[uuid.UUID, int] = {cont_id: 0 for cont_id in container_balances}
        container_est_expense: dict[uuid.UUID, int] = {cont_id: 0 for cont_id in container_balances}
        container_max_expense: dict[uuid.UUID, int] = {cont_id: 0 for cont_id in container_balances}
        container_transfers: dict[uuid.UUID, int] = {cont_id: 0 for cont_id in container_balances}

        # Process root-level income/expense posts
        for budget_post in root_posts:
            # Expand amount patterns to occurrences for this month
            occurrences = expand_amount_patterns_to_occurrences(
                budget_post,
                month_start,
                month_end
            )

            total_amount = sum(amount for _, amount in occurrences)

            # Compute per-container intervals using recursive algorithm
            intervals = compute_interval_for_post(
                budget_post,
                cashbox_posts,  # Pass all cashbox posts for hierarchy
                month_start,
                month_end,
                container_types
            )

            # Aggregate intervals per container
            for cont_id, (min_amt, est_amt, max_amt) in intervals.items():
                if budget_post.direction == BudgetPostDirection.INCOME:
                    container_min_income[cont_id] += min_amt
                    container_est_income[cont_id] += est_amt
                    container_max_income[cont_id] += max_amt
                elif budget_post.direction == BudgetPostDirection.EXPENSE:
                    container_min_expense[cont_id] += min_amt
                    container_est_expense[cont_id] += est_amt
                    container_max_expense[cont_id] += max_amt

            # Also track total (existing logic)
            if total_amount > 0:
                if budget_post.direction == BudgetPostDirection.INCOME:
                    expected_income += total_amount
                elif budget_post.direction == BudgetPostDirection.EXPENSE:
                    expected_expenses += total_amount

                    # Track large expenses in next 3 months for insights
                    if month_offset < 3 and budget_post.category_path:
                        for occurrence_date, amount in occurrences:
                            large_expenses.append({
                                "name": budget_post.category_path[-1],
                                "amount": -amount,  # Store as negative for display consistency
                                "date": occurrence_date.isoformat()
                            })

        # Process transfers
        for transfer_post in transfer_posts:
            # Check if both containers exist and get their types
            from_container = transfer_post.transfer_from_container
            to_container = transfer_post.transfer_to_container

            if not from_container or not to_container:
                continue

            from_is_cashbox = from_container.type == ContainerType.CASHBOX
            to_is_cashbox = to_container.type == ContainerType.CASHBOX

            # Expand amount patterns to occurrences for this month
            occurrences = expand_amount_patterns_to_occurrences(
                transfer_post,
                month_start,
                month_end
            )

            total_transfer = sum(amount for _, amount in occurrences)
            if total_transfer == 0:
                continue

            # For total forecast: skip if both are cashbox or neither are cashbox (net-zero)
            if not (from_is_cashbox == to_is_cashbox):
                if from_is_cashbox and not to_is_cashbox:
                    # pengekasse → non-pengekasse: reduces balance (treat as expense)
                    expected_expenses += total_transfer
                elif not from_is_cashbox and to_is_cashbox:
                    # non-pengekasse → pengekasse: increases balance (treat as income)
                    expected_income += total_transfer

            # For per-container: track all transfers involving cashboxes
            # (pengekasse↔pengekasse transfers ARE included per-container)
            if from_is_cashbox and from_container.id in container_transfers:
                container_transfers[from_container.id] -= total_transfer
            if to_is_cashbox and to_container.id in container_transfers:
                container_transfers[to_container.id] += total_transfer

        # Calculate end balance (expenses are added as positive, so subtract them)
        end_balance = start_balance + expected_income - expected_expenses

        projections.append(MonthProjection(
            month=month_str,
            start_balance=start_balance,
            expected_income=expected_income,
            expected_expenses=-expected_expenses,  # Store as negative for display consistency
            end_balance=end_balance
        ))

        # Calculate per-container balances with min/max/estimate
        for cont_id in running_container_est:
            # Use estimate as display start balance
            cont_start_balance = running_container_est[cont_id]

            # min_balance: start from min + min_income - max_expense + transfers (worst case)
            min_balance = (
                running_container_min[cont_id] +
                container_min_income[cont_id] -
                container_max_expense[cont_id] +
                container_transfers[cont_id]
            )

            # estimate_balance: start from est + est_income - est_expense + transfers
            estimate_balance = (
                running_container_est[cont_id] +
                container_est_income[cont_id] -
                container_est_expense[cont_id] +
                container_transfers[cont_id]
            )

            # max_balance: start from max + max_income - min_expense + transfers (best case)
            max_balance = (
                running_container_max[cont_id] +
                container_max_income[cont_id] -
                container_min_expense[cont_id] +
                container_transfers[cont_id]
            )

            container_projections.append(ContainerMonthProjection(
                container_id=str(cont_id),
                container_name=container_names.get(cont_id, "Unknown"),
                month=month_str,
                start_balance=cont_start_balance,
                min_balance=min_balance,
                estimate_balance=estimate_balance,
                max_balance=max_balance
            ))

            # Update each running balance for next iteration
            running_container_min[cont_id] = min_balance
            running_container_est[cont_id] = estimate_balance
            running_container_max[cont_id] = max_balance

        # Track lowest point
        if end_balance < lowest_balance:
            lowest_balance = end_balance
            lowest_month = month_str

        # Update running balance for next iteration
        running_balance = end_balance

    # Identify next large expense (largest single expense in next 3 months)
    if large_expenses:
        next_large_expense = min(large_expenses, key=lambda x: x["amount"])

    # Build lowest point dict
    lowest_point = {
        "month": lowest_month if lowest_month else month_str,
        "balance": lowest_balance
    }

    return ForecastResult(
        projections=projections,
        container_projections=container_projections,
        lowest_point=lowest_point,
        next_large_expense=next_large_expense
    )
