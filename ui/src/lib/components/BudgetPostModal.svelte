<script lang="ts">
	import { _ } from '$lib/i18n';
	import type { BudgetPost, BudgetPostType, RecurrencePattern } from '$lib/api/budgetPosts';
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
	let recurrenceType = $state<'monthly' | 'quarterly' | 'yearly' | 'once'>('monthly');
	let recurrenceDay = $state<number>(1);
	let recurrenceMonths = $state<number[]>([]);
	let recurrenceDate = $state('');
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
					recurrenceDay = budgetPost.recurrence_pattern.day || 1;
					recurrenceMonths = budgetPost.recurrence_pattern.months || [];
					recurrenceDate = budgetPost.recurrence_pattern.date || '';
				} else {
					recurrenceType = 'monthly';
					recurrenceDay = 1;
					recurrenceMonths = [];
					recurrenceDate = '';
				}
			} else {
				// Create mode - reset to defaults
				name = '';
				type = 'fixed';
				amountMin = '';
				amountMax = '';
				categoryId = categories.length > 0 ? categories[0].id : '';
				recurrenceType = 'monthly';
				recurrenceDay = 1;
				recurrenceMonths = [];
				recurrenceDate = '';
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

		if (!name.trim() || amountMin === '' || amountMin === null || amountMin === undefined || !categoryId) {
			error = $_('common.error');
			return;
		}

		saving = true;

		try {
			// Convert kr to øre (multiply by 100)
			const amountMinInOre = Math.round(parseFloat(amountMin) * 100);
			const amountMaxInOre = amountMax ? Math.round(parseFloat(amountMax) * 100) : null;

			// Build recurrence pattern
			const recurrence: RecurrencePattern = {
				type: recurrenceType
			};

			if (recurrenceType === 'monthly') {
				recurrence.day = recurrenceDay;
			} else if (recurrenceType === 'quarterly' || recurrenceType === 'yearly') {
				recurrence.months = recurrenceMonths;
				recurrence.day = recurrenceDay;
			} else if (recurrenceType === 'once') {
				recurrence.date = recurrenceDate;
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
								<option value="monthly">{$_('budgetPosts.recurrence.monthly')}</option>
								<option value="quarterly">{$_('budgetPosts.recurrence.quarterly')}</option>
								<option value="yearly">{$_('budgetPosts.recurrence.yearly')}</option>
								<option value="once">{$_('budgetPosts.recurrence.once')}</option>
							</select>
						</div>

						{#if recurrenceType === 'monthly'}
							<div class="form-group">
								<label for="recurrence-day">{$_('budgetPosts.recurrence.day')}</label>
								<input
									id="recurrence-day"
									type="number"
									min="1"
									max="31"
									bind:value={recurrenceDay}
									disabled={saving}
								/>
							</div>
						{:else if recurrenceType === 'quarterly' || recurrenceType === 'yearly'}
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
							<div class="form-group">
								<label for="recurrence-day-multi">{$_('budgetPosts.recurrence.day')}</label>
								<input
									id="recurrence-day-multi"
									type="number"
									min="1"
									max="31"
									bind:value={recurrenceDay}
									disabled={saving}
								/>
							</div>
						{:else if recurrenceType === 'once'}
							<div class="form-group">
								<label for="recurrence-date">{$_('budgetPosts.recurrence.date')}</label>
								<input
									id="recurrence-date"
									type="date"
									bind:value={recurrenceDate}
									disabled={saving}
								/>
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
