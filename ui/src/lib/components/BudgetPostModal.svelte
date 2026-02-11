<script lang="ts">
	import { _ } from '$lib/i18n';
	import type { BudgetPost, BudgetPostType, RecurrencePattern, RecurrenceType, RelativePosition } from '$lib/api/budgetPosts';
	import type { Category } from '$lib/api/categories';

	let {
		show = $bindable(false),
		budgetPost = undefined,
		categories = [],
		onSave
	}: {
		show?: boolean;
		budgetPost?: BudgetPost | undefined;
		categories: Category[];
		onSave: (data: any) => Promise<void>;
	} = $props();

	// Form state
	let name = $state('');
	let type = $state<BudgetPostType>('fixed');
	let amountMin = $state(''); // In kr (will convert to øre)
	let amountMax = $state(''); // In kr (will convert to øre)
	let categoryId = $state('');
	let recurrenceType = $state<RecurrenceType>('monthly_fixed');
	let recurrenceInterval = $state<number>(1);
	let recurrenceWeekday = $state<number>(0); // 0=Monday
	let recurrenceDayOfMonth = $state<number>(1);
	let recurrenceRelativePosition = $state<RelativePosition>('first');
	let recurrenceMonth = $state<number>(1); // 1-12
	let recurrenceMonths = $state<number[]>([]);
	let recurrenceDate = $state('');
	let recurrencePostponeWeekend = $state(false);
	let yearlyUseRelative = $state(false); // Toggle for yearly: fixed day vs relative weekday
	let saving = $state(false);
	let error = $state<string | null>(null);

	// Reset form when modal opens or budgetPost changes
	$effect(() => {
		if (show) {
			if (budgetPost) {
				// Edit mode - populate from existing post
				name = budgetPost.name;
				type = budgetPost.type;
				amountMin = (budgetPost.amount_min / 100).toFixed(2);
				amountMax = budgetPost.amount_max ? (budgetPost.amount_max / 100).toFixed(2) : '';
				categoryId = budgetPost.category_id;

				if (budgetPost.recurrence_pattern) {
					recurrenceType = budgetPost.recurrence_pattern.type;
					recurrenceInterval = budgetPost.recurrence_pattern.interval || 1;
					recurrenceWeekday = budgetPost.recurrence_pattern.weekday || 0;
					recurrenceDayOfMonth = budgetPost.recurrence_pattern.day_of_month || 1;
					recurrenceRelativePosition = budgetPost.recurrence_pattern.relative_position || 'first';
					recurrenceMonth = budgetPost.recurrence_pattern.month || 1;
					recurrenceMonths = budgetPost.recurrence_pattern.months || [];
					recurrenceDate = budgetPost.recurrence_pattern.date || '';
					recurrencePostponeWeekend = budgetPost.recurrence_pattern.postpone_weekend || false;
					// Detect if yearly pattern uses relative weekday
					if (budgetPost.recurrence_pattern.type === 'yearly') {
						yearlyUseRelative = budgetPost.recurrence_pattern.relative_position !== undefined && budgetPost.recurrence_pattern.weekday !== undefined;
					}
				} else {
					recurrenceType = 'monthly_fixed';
					recurrenceInterval = 1;
					recurrenceWeekday = 0;
					recurrenceDayOfMonth = 1;
					recurrenceRelativePosition = 'first';
					recurrenceMonth = 1;
					recurrenceMonths = [];
					recurrenceDate = '';
					recurrencePostponeWeekend = false;
				}
			} else {
				// Create mode - reset to defaults
				name = '';
				type = 'fixed';
				amountMin = '';
				amountMax = '';
				categoryId = categories.length > 0 ? categories[0].id : '';
				recurrenceType = 'monthly_fixed';
				recurrenceInterval = 1;
				recurrenceWeekday = 0;
				recurrenceDayOfMonth = 1;
				recurrenceRelativePosition = 'first';
				recurrenceMonth = 1;
				recurrenceMonths = [];
				recurrenceDate = '';
				recurrencePostponeWeekend = false;
				yearlyUseRelative = false;
			}
			error = null;
		}
	});

	function handleClose() {
		show = false;
	}

	async function handleSubmit(event: Event) {
		event.preventDefault();
		error = null;

		// Validate required fields with specific error messages
		if (!name.trim()) {
			error = $_('budgetPosts.validation.nameRequired');
			return;
		}
		if (amountMin === '' || amountMin === null || amountMin === undefined) {
			error = $_('budgetPosts.validation.amountRequired');
			return;
		}
		if (!categoryId) {
			error = $_('budgetPosts.validation.categoryRequired');
			return;
		}

		saving = true;

		try {
			// Convert kr to øre (multiply by 100)
			const amountMinInOre = Math.round(parseFloat(amountMin) * 100);
			const amountMaxInOre = amountMax ? Math.round(parseFloat(amountMax) * 100) : null;

			// Build recurrence pattern based on type
			const recurrence: RecurrencePattern = {
				type: recurrenceType
			};

			if (recurrenceType === 'once') {
				recurrence.date = recurrenceDate;
			} else if (recurrenceType === 'daily') {
				recurrence.interval = recurrenceInterval;
				recurrence.postpone_weekend = recurrencePostponeWeekend;
			} else if (recurrenceType === 'weekly') {
				recurrence.weekday = recurrenceWeekday;
				recurrence.interval = recurrenceInterval;
				recurrence.postpone_weekend = recurrencePostponeWeekend;
			} else if (recurrenceType === 'monthly_fixed') {
				recurrence.day_of_month = recurrenceDayOfMonth;
				recurrence.interval = recurrenceInterval;
				recurrence.postpone_weekend = recurrencePostponeWeekend;
			} else if (recurrenceType === 'monthly_relative') {
				recurrence.weekday = recurrenceWeekday;
				recurrence.relative_position = recurrenceRelativePosition;
				recurrence.interval = recurrenceInterval;
				recurrence.postpone_weekend = recurrencePostponeWeekend;
			} else if (recurrenceType === 'yearly') {
				recurrence.month = recurrenceMonth;
				recurrence.interval = recurrenceInterval;
				recurrence.postpone_weekend = recurrencePostponeWeekend;
				// Yearly can use either day_of_month OR weekday+relative_position
				if (yearlyUseRelative) {
					recurrence.weekday = recurrenceWeekday;
					recurrence.relative_position = recurrenceRelativePosition;
				} else {
					recurrence.day_of_month = recurrenceDayOfMonth;
				}
			} else if (recurrenceType === 'period_once') {
				recurrence.months = recurrenceMonths;
			} else if (recurrenceType === 'period_yearly') {
				recurrence.months = recurrenceMonths;
				recurrence.interval = recurrenceInterval;
			}

			const data = {
				name: name.trim(),
				type,
				amount_min: amountMinInOre,
				amount_max: amountMaxInOre,
				category_id: categoryId,
				recurrence_pattern: recurrence
			};

			await onSave(data);
			show = false;
		} catch (err) {
			error = err instanceof Error ? $_(err.message) : $_('common.error');
		} finally {
			saving = false;
		}
	}

	function handleBackdropClick(event: MouseEvent) {
		if (event.target === event.currentTarget) {
			handleClose();
		}
	}

	function toggleMonth(month: number) {
		if (recurrenceMonths.includes(month)) {
			recurrenceMonths = recurrenceMonths.filter(m => m !== month);
		} else {
			recurrenceMonths = [...recurrenceMonths, month].sort((a, b) => a - b);
		}
	}

	// Flatten categories for selection (including nested ones)
	function flattenCategories(cats: Category[], prefix = ''): Array<{ id: string; name: string }> {
		let result: Array<{ id: string; name: string }> = [];
		for (const cat of cats) {
			const displayName = prefix ? `${prefix} › ${cat.name}` : cat.name;
			result.push({ id: cat.id, name: displayName });
			if (cat.children && cat.children.length > 0) {
				result = result.concat(flattenCategories(cat.children, displayName));
			}
		}
		return result;
	}

	let flatCategories = $derived(flattenCategories(categories));

	// Month labels for selection (abbreviated)
	let monthLabels = $derived([
		$_('months.jan'),
		$_('months.feb'),
		$_('months.mar'),
		$_('months.apr'),
		$_('months.may'),
		$_('months.jun'),
		$_('months.jul'),
		$_('months.aug'),
		$_('months.sep'),
		$_('months.oct'),
		$_('months.nov'),
		$_('months.dec')
	]);
</script>

{#if show}
	<div class="modal-backdrop" onclick={handleBackdropClick} role="presentation">
		<div class="modal" role="dialog" aria-modal="true">
			<div class="modal-header">
				<h2>
					{budgetPost ? $_('budgetPosts.edit') : $_('budgetPosts.create')}
				</h2>
				<button
					class="close-button"
					onclick={handleClose}
					type="button"
					aria-label={$_('common.close')}
				>
					<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
						<line x1="18" y1="6" x2="6" y2="18" />
						<line x1="6" y1="6" x2="18" y2="18" />
					</svg>
				</button>
			</div>

			<form onsubmit={handleSubmit}>
				<div class="modal-body">
					<div class="form-group">
						<label for="post-name">
							{$_('budgetPosts.name')}
							<span class="required">*</span>
						</label>
						<input
							id="post-name"
							type="text"
							bind:value={name}
							required
							placeholder={$_('budgetPosts.name')}
							disabled={saving}
						/>
					</div>

					<div class="form-group">
						<label for="post-type">
							{$_('budgetPosts.type.label')}
							<span class="required">*</span>
						</label>
						<select id="post-type" bind:value={type} required disabled={saving}>
							<option value="fixed">{$_('budgetPosts.type.fixed')}</option>
							<option value="ceiling">{$_('budgetPosts.type.ceiling')}</option>
							<option value="rolling">{$_('budgetPosts.type.rolling')}</option>
						</select>
					</div>

					<div class="form-row">
						<div class="form-group">
							<label for="post-amount-min">
								{$_('budgetPosts.amountMin')} (kr)
								<span class="required">*</span>
							</label>
							<input
								id="post-amount-min"
								type="number"
								step="0.01"
								min="0"
								bind:value={amountMin}
								required
								placeholder="0.00"
								disabled={saving}
							/>
						</div>

						{#if type === 'ceiling' || type === 'rolling'}
							<div class="form-group">
								<label for="post-amount-max">
									{$_('budgetPosts.amountMax')} (kr)
								</label>
								<input
									id="post-amount-max"
									type="number"
									step="0.01"
									min="0"
									bind:value={amountMax}
									placeholder="0.00"
									disabled={saving}
								/>
							</div>
						{/if}
					</div>

					<div class="form-group">
						<label for="post-category">
							{$_('budgetPosts.category')}
							<span class="required">*</span>
						</label>
						<select id="post-category" bind:value={categoryId} required disabled={saving}>
							{#if flatCategories.length === 0}
								<option value="">{$_('budgetPosts.noCategory')}</option>
							{:else}
								{#each flatCategories as cat (cat.id)}
									<option value={cat.id}>{cat.name}</option>
								{/each}
							{/if}
						</select>
					</div>

					<div class="form-section">
						<h3>{$_('budgetPosts.recurrence.label')}</h3>

						<div class="form-group">
							<label for="recurrence-type">{$_('budgetPosts.type.label')}</label>
							<select id="recurrence-type" bind:value={recurrenceType} disabled={saving}>
								<option value="once">{$_('budgetPosts.recurrence.once')}</option>
								<option value="daily">{$_('budgetPosts.recurrence.daily')}</option>
								<option value="weekly">{$_('budgetPosts.recurrence.weekly')}</option>
								<option value="monthly_fixed">{$_('budgetPosts.recurrence.monthly_fixed')}</option>
								<option value="monthly_relative">{$_('budgetPosts.recurrence.monthly_relative')}</option>
								<option value="yearly">{$_('budgetPosts.recurrence.yearly')}</option>
								<option value="period_once">{$_('budgetPosts.recurrence.period_once')}</option>
								<option value="period_yearly">{$_('budgetPosts.recurrence.period_yearly')}</option>
							</select>
						</div>

						{#if recurrenceType === 'once'}
							<!-- Date picker for one-time event -->
							<div class="form-group">
								<label for="recurrence-date">{$_('budgetPosts.recurrence.date')}</label>
								<input
									id="recurrence-date"
									type="date"
									bind:value={recurrenceDate}
									disabled={saving}
								/>
							</div>

						{:else if recurrenceType === 'daily'}
							<!-- Interval for daily -->
							<div class="form-group">
								<label for="recurrence-interval">{$_('budgetPosts.recurrence.interval')}</label>
								<input
									id="recurrence-interval"
									type="number"
									min="1"
									bind:value={recurrenceInterval}
									disabled={saving}
								/>
								<span class="form-hint">{$_('budgetPosts.recurrence.everyN', { values: { n: recurrenceInterval } })}</span>
							</div>

						{:else if recurrenceType === 'weekly'}
							<!-- Weekday + interval -->
							<div class="form-row">
								<div class="form-group">
									<label for="recurrence-weekday">{$_('budgetPosts.recurrence.weekday')}</label>
									<select id="recurrence-weekday" bind:value={recurrenceWeekday} disabled={saving}>
										<option value={0}>{$_('budgetPosts.weekday.monday')}</option>
										<option value={1}>{$_('budgetPosts.weekday.tuesday')}</option>
										<option value={2}>{$_('budgetPosts.weekday.wednesday')}</option>
										<option value={3}>{$_('budgetPosts.weekday.thursday')}</option>
										<option value={4}>{$_('budgetPosts.weekday.friday')}</option>
										<option value={5}>{$_('budgetPosts.weekday.saturday')}</option>
										<option value={6}>{$_('budgetPosts.weekday.sunday')}</option>
									</select>
								</div>
								<div class="form-group">
									<label for="recurrence-interval-weekly">{$_('budgetPosts.recurrence.interval')}</label>
									<input
										id="recurrence-interval-weekly"
										type="number"
										min="1"
										bind:value={recurrenceInterval}
										disabled={saving}
									/>
								</div>
							</div>

						{:else if recurrenceType === 'monthly_fixed'}
							<!-- Day of month + interval -->
							<div class="form-row">
								<div class="form-group">
									<label for="recurrence-day-of-month">{$_('budgetPosts.recurrence.dayOfMonth')}</label>
									<input
										id="recurrence-day-of-month"
										type="number"
										min="1"
										max="31"
										bind:value={recurrenceDayOfMonth}
										disabled={saving}
									/>
								</div>
								<div class="form-group">
									<label for="recurrence-interval-monthly">{$_('budgetPosts.recurrence.interval')}</label>
									<input
										id="recurrence-interval-monthly"
										type="number"
										min="1"
										bind:value={recurrenceInterval}
										disabled={saving}
									/>
								</div>
							</div>

						{:else if recurrenceType === 'monthly_relative'}
							<!-- Weekday + relative position + interval -->
							<div class="form-row">
								<div class="form-group">
									<label for="recurrence-relative-position">{$_('budgetPosts.recurrence.relativePosition')}</label>
									<select id="recurrence-relative-position" bind:value={recurrenceRelativePosition} disabled={saving}>
										<option value="first">{$_('budgetPosts.relativePosition.first')}</option>
										<option value="last">{$_('budgetPosts.relativePosition.last')}</option>
									</select>
								</div>
								<div class="form-group">
									<label for="recurrence-weekday-relative">{$_('budgetPosts.recurrence.weekday')}</label>
									<select id="recurrence-weekday-relative" bind:value={recurrenceWeekday} disabled={saving}>
										<option value={0}>{$_('budgetPosts.weekday.monday')}</option>
										<option value={1}>{$_('budgetPosts.weekday.tuesday')}</option>
										<option value={2}>{$_('budgetPosts.weekday.wednesday')}</option>
										<option value={3}>{$_('budgetPosts.weekday.thursday')}</option>
										<option value={4}>{$_('budgetPosts.weekday.friday')}</option>
										<option value={5}>{$_('budgetPosts.weekday.saturday')}</option>
										<option value={6}>{$_('budgetPosts.weekday.sunday')}</option>
									</select>
								</div>
							</div>
							<div class="form-group">
								<label for="recurrence-interval-monthly-rel">{$_('budgetPosts.recurrence.interval')}</label>
								<input
									id="recurrence-interval-monthly-rel"
									type="number"
									min="1"
									bind:value={recurrenceInterval}
									disabled={saving}
								/>
							</div>

						{:else if recurrenceType === 'yearly'}
							<!-- Month selection -->
							<div class="form-group">
								<label for="recurrence-month">{$_('budgetPosts.recurrence.month')}</label>
								<select id="recurrence-month" bind:value={recurrenceMonth} disabled={saving}>
									{#each monthLabels as monthLabel, index}
										<option value={index + 1}>{monthLabel}</option>
									{/each}
								</select>
							</div>

							<!-- Day type toggle -->
							<div class="form-group">
								<label>{$_('budgetPosts.recurrence.dayType')}</label>
								<div class="radio-group">
									<label class="radio-label">
										<input
											type="radio"
											bind:group={yearlyUseRelative}
											value={false}
											disabled={saving}
										/>
										<span>{$_('budgetPosts.recurrence.fixedDay')}</span>
									</label>
									<label class="radio-label">
										<input
											type="radio"
											bind:group={yearlyUseRelative}
											value={true}
											disabled={saving}
										/>
										<span>{$_('budgetPosts.recurrence.relativeWeekday')}</span>
									</label>
								</div>
							</div>

							{#if yearlyUseRelative}
								<!-- Relative weekday selection -->
								<div class="form-row">
									<div class="form-group">
										<label for="recurrence-yearly-relative-position">{$_('budgetPosts.recurrence.relativePosition')}</label>
										<select id="recurrence-yearly-relative-position" bind:value={recurrenceRelativePosition} disabled={saving}>
											<option value="first">{$_('budgetPosts.relativePosition.first')}</option>
											<option value="last">{$_('budgetPosts.relativePosition.last')}</option>
										</select>
									</div>
									<div class="form-group">
										<label for="recurrence-yearly-weekday">{$_('budgetPosts.recurrence.weekday')}</label>
										<select id="recurrence-yearly-weekday" bind:value={recurrenceWeekday} disabled={saving}>
											<option value={0}>{$_('budgetPosts.weekday.monday')}</option>
											<option value={1}>{$_('budgetPosts.weekday.tuesday')}</option>
											<option value={2}>{$_('budgetPosts.weekday.wednesday')}</option>
											<option value={3}>{$_('budgetPosts.weekday.thursday')}</option>
											<option value={4}>{$_('budgetPosts.weekday.friday')}</option>
											<option value={5}>{$_('budgetPosts.weekday.saturday')}</option>
											<option value={6}>{$_('budgetPosts.weekday.sunday')}</option>
										</select>
									</div>
								</div>
							{:else}
								<!-- Fixed day selection -->
								<div class="form-group">
									<label for="recurrence-day-yearly">{$_('budgetPosts.recurrence.dayOfMonth')}</label>
									<input
										id="recurrence-day-yearly"
										type="number"
										min="1"
										max="31"
										bind:value={recurrenceDayOfMonth}
										disabled={saving}
									/>
								</div>
							{/if}

							<!-- Interval -->
							<div class="form-group">
								<label for="recurrence-interval-yearly">{$_('budgetPosts.recurrence.interval')}</label>
								<input
									id="recurrence-interval-yearly"
									type="number"
									min="1"
									bind:value={recurrenceInterval}
									disabled={saving}
								/>
							</div>

						{:else if recurrenceType === 'period_once' || recurrenceType === 'period_yearly'}
							<!-- Months selector -->
							<div class="form-group">
								<label>{$_('budgetPosts.recurrence.months')}</label>
								<div class="month-selector">
									{#each monthLabels as month, index}
										<button
											type="button"
											class="month-btn"
											class:selected={recurrenceMonths.includes(index + 1)}
											onclick={() => toggleMonth(index + 1)}
											disabled={saving}
										>
											{month}
										</button>
									{/each}
								</div>
							</div>
							{#if recurrenceType === 'period_yearly'}
								<div class="form-group">
									<label for="recurrence-interval-period">{$_('budgetPosts.recurrence.interval')}</label>
									<input
										id="recurrence-interval-period"
										type="number"
										min="1"
										bind:value={recurrenceInterval}
										disabled={saving}
									/>
								</div>
							{/if}
						{/if}

						<!-- Postpone weekend checkbox for date-based types -->
						{#if recurrenceType !== 'once' && recurrenceType !== 'period_once' && recurrenceType !== 'period_yearly'}
							<div class="form-group">
								<label class="checkbox-label">
									<input
										type="checkbox"
										bind:checked={recurrencePostponeWeekend}
										disabled={saving}
									/>
									<span>{$_('budgetPosts.recurrence.postponeWeekend')}</span>
								</label>
							</div>
						{/if}
					</div>

					{#if error}
						<div class="error-message">
							{error}
						</div>
					{/if}
				</div>

				<div class="modal-footer">
					<button type="button" class="btn-secondary" onclick={handleClose} disabled={saving}>
						{$_('common.cancel')}
					</button>
					<button type="submit" class="btn-primary" disabled={saving}>
						{saving ? $_('common.loading') : $_('common.save')}
					</button>
				</div>
			</form>
		</div>
	</div>
{/if}

<style>
	.modal-backdrop {
		position: fixed;
		top: 0;
		left: 0;
		right: 0;
		bottom: 0;
		background: rgba(0, 0, 0, 0.5);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 1000;
		padding: var(--spacing-md);
	}

	.modal {
		background: var(--bg-card);
		border-radius: var(--radius-lg);
		max-width: 700px;
		width: 100%;
		max-height: 90vh;
		overflow-y: auto;
		box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
	}

	.modal-header {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: var(--spacing-lg) var(--spacing-xl);
		border-bottom: 1px solid var(--border);
	}

	.modal-header h2 {
		font-size: var(--font-size-xl);
		font-weight: 600;
		color: var(--text-primary);
		margin: 0;
	}

	.close-button {
		background: none;
		border: none;
		color: var(--text-secondary);
		cursor: pointer;
		padding: var(--spacing-xs);
		display: flex;
		align-items: center;
		justify-content: center;
		border-radius: var(--radius-md);
		transition: all 0.2s;
	}

	.close-button:hover {
		background: var(--bg-page);
		color: var(--text-primary);
	}

	.modal-body {
		padding: var(--spacing-xl);
		display: flex;
		flex-direction: column;
		gap: var(--spacing-lg);
	}

	.form-group {
		display: flex;
		flex-direction: column;
		gap: var(--spacing-xs);
	}

	.form-row {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: var(--spacing-md);
	}

	.form-section {
		border-top: 1px solid var(--border);
		padding-top: var(--spacing-lg);
		margin-top: var(--spacing-sm);
	}

	.form-section h3 {
		font-size: var(--font-size-lg);
		font-weight: 600;
		color: var(--text-primary);
		margin-bottom: var(--spacing-md);
	}

	label {
		font-size: var(--font-size-base);
		font-weight: 500;
		color: var(--text-primary);
	}

	.required {
		color: var(--negative);
	}

	.form-hint {
		font-size: var(--font-size-sm);
		color: var(--text-secondary);
		font-style: italic;
	}

	.checkbox-label {
		display: flex;
		align-items: center;
		gap: var(--spacing-sm);
		cursor: pointer;
		font-weight: normal;
	}

	.checkbox-label input[type='checkbox'] {
		cursor: pointer;
	}

	.radio-group {
		display: flex;
		gap: var(--spacing-md);
		flex-wrap: wrap;
	}

	.radio-label {
		display: flex;
		align-items: center;
		gap: var(--spacing-sm);
		cursor: pointer;
		font-weight: normal;
	}

	.radio-label input[type='radio'] {
		cursor: pointer;
	}

	input[type='text'],
	input[type='number'],
	input[type='date'],
	select {
		padding: var(--spacing-sm) var(--spacing-md);
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		font-size: var(--font-size-base);
		color: var(--text-primary);
		background: var(--bg-page);
		transition: border-color 0.2s;
	}

	input[type='text']:focus,
	input[type='number']:focus,
	input[type='date']:focus,
	select:focus {
		outline: none;
		border-color: var(--accent);
	}

	input[type='text']:disabled,
	input[type='number']:disabled,
	input[type='date']:disabled,
	select:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}

	.month-selector {
		display: grid;
		grid-template-columns: repeat(4, 1fr);
		gap: var(--spacing-xs);
	}

	.month-btn {
		padding: var(--spacing-sm);
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		background: var(--bg-page);
		color: var(--text-secondary);
		font-size: var(--font-size-sm);
		cursor: pointer;
		transition: all 0.2s;
	}

	.month-btn:hover:not(:disabled) {
		border-color: var(--accent);
		color: var(--accent);
	}

	.month-btn.selected {
		background: var(--accent);
		color: white;
		border-color: var(--accent);
	}

	.month-btn:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}

	.error-message {
		padding: var(--spacing-sm) var(--spacing-md);
		background: rgba(239, 68, 68, 0.1);
		border: 1px solid var(--negative);
		border-radius: var(--radius-md);
		color: var(--negative);
		font-size: var(--font-size-sm);
	}

	.modal-footer {
		display: flex;
		gap: var(--spacing-md);
		justify-content: flex-end;
		padding: var(--spacing-lg) var(--spacing-xl);
		border-top: 1px solid var(--border);
	}

	.btn-primary,
	.btn-secondary {
		padding: var(--spacing-sm) var(--spacing-lg);
		border-radius: var(--radius-md);
		font-size: var(--font-size-base);
		font-weight: 500;
		cursor: pointer;
		transition: opacity 0.2s;
		border: none;
	}

	.btn-primary {
		background: var(--accent);
		color: white;
	}

	.btn-secondary {
		background: transparent;
		color: var(--accent);
		border: 1px solid var(--accent);
	}

	.btn-primary:disabled,
	.btn-secondary:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}

	.btn-primary:hover:not(:disabled),
	.btn-secondary:hover:not(:disabled) {
		opacity: 0.9;
	}

	@media (max-width: 768px) {
		.modal {
			max-width: 100%;
			max-height: 100vh;
			border-radius: 0;
		}

		.modal-body {
			padding: var(--spacing-lg);
		}

		.form-row {
			grid-template-columns: 1fr;
		}

		.month-selector {
			grid-template-columns: repeat(3, 1fr);
		}

		.modal-footer {
			flex-direction: column-reverse;
			padding: var(--spacing-lg);
		}

		.btn-primary,
		.btn-secondary {
			width: 100%;
		}
	}
</style>
