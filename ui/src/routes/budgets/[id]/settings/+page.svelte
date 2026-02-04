<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { _ } from '$lib/i18n';
	import { getBudget, updateBudget, deleteBudget } from '$lib/api/budgets';
	import { budgetStore } from '$lib/stores/budget';
	import { goto } from '$app/navigation';
	import type { Budget } from '$lib/api/budgets';

	let budgetId = $derived($page.params.id);
	let budget = $state<Budget | null>(null);
	let name = $state('');
	let warningThreshold = $state('');
	let loading = $state(true);
	let saving = $state(false);
	let deleting = $state(false);
	let showDeleteConfirm = $state(false);
	let error = $state<string | null>(null);
	let saveSuccess = $state(false);

	onMount(async () => {
		await loadBudget();
	});

	async function loadBudget() {
		try {
			loading = true;
			error = null;
			const data = await getBudget(budgetId);
			budget = data;
			name = data.name;
			warningThreshold = data.warning_threshold
				? (data.warning_threshold / 100).toFixed(2)
				: '';
		} catch (err) {
			error = err instanceof Error ? err.message : $_('common.error');
		} finally {
			loading = false;
		}
	}

	async function handleSubmit(event: Event) {
		event.preventDefault();
		error = null;
		saveSuccess = false;

		if (!name.trim()) {
			error = $_('budget.messages.nameRequired');
			return;
		}

		saving = true;

		try {
			// Convert DKK to øre, or null if empty
			const thresholdInOre = warningThreshold
				? Math.round(parseFloat(warningThreshold) * 100)
				: null;

			const updatedBudget = await updateBudget(budgetId, {
				name: name.trim(),
				warning_threshold: thresholdInOre
			});

			// Update in store
			budgetStore.updateBudget(updatedBudget);
			budget = updatedBudget;
			saveSuccess = true;

			// Clear success message after 3 seconds
			setTimeout(() => {
				saveSuccess = false;
			}, 3000);
		} catch (err) {
			error = err instanceof Error ? err.message : $_('common.error');
		} finally {
			saving = false;
		}
	}

	function handleShowDeleteConfirm() {
		showDeleteConfirm = true;
	}

	function handleCancelDelete() {
		showDeleteConfirm = false;
	}

	async function handleDelete() {
		deleting = true;
		error = null;

		try {
			await deleteBudget(budgetId);
			budgetStore.removeBudget(budgetId);
			goto('/budgets');
		} catch (err) {
			error = err instanceof Error ? err.message : $_('common.error');
			deleting = false;
			showDeleteConfirm = false;
		}
	}

	function handleCancel() {
		goto('/budgets');
	}

	function formatCurrency(amountInOre: number): string {
		return (amountInOre / 100).toFixed(2);
	}
</script>

<div class="page">
	<div class="container">
		{#if loading}
			<div class="loading">
				<p>{$_('common.loading')}</p>
			</div>
		{:else if !budget}
			<div class="error-message">
				<p>{$_('budget.messages.notFound')}</p>
				<a href="/budgets" class="btn-secondary">{$_('budget.messages.backToBudgets')}</a>
			</div>
		{:else}
			<header class="page-header">
				<h1>{$_('budget.settings.title')}</h1>
			</header>

			<div class="settings-container">
				<form onsubmit={handleSubmit}>
					<div class="form-section">
						<h2>{$_('budget.settings.general')}</h2>

						<div class="form-group">
							<label for="name">
								{$_('budget.field.name')}
								<span class="required">*</span>
							</label>
							<input
								id="name"
								type="text"
								bind:value={name}
								required
								placeholder={$_('budget.field.name')}
								disabled={saving}
							/>
						</div>

						<div class="form-group">
							<label for="warningThreshold">
								{$_('budget.field.warningThreshold')}
							</label>
							<input
								id="warningThreshold"
								type="number"
								step="0.01"
								min="0"
								bind:value={warningThreshold}
								placeholder="0.00"
								disabled={saving}
							/>
							<span class="hint">{$_('budget.field.warningThresholdHint')}</span>
						</div>

						{#if budget.total_balance !== undefined}
							<div class="info-row">
								<span class="label">{$_('budget.messages.currentBalance')}:</span>
								<span class="value" class:negative={budget.total_balance < 0}>
									{formatCurrency(budget.total_balance)} kr
								</span>
							</div>
						{/if}

						{#if error}
							<div class="error-message">
								{error}
							</div>
						{/if}

						{#if saveSuccess}
							<div class="success-message">
								{$_('budget.messages.saved')}
							</div>
						{/if}

						<div class="form-actions">
							<button type="button" class="btn-secondary" onclick={handleCancel} disabled={saving}>
								{$_('common.cancel')}
							</button>
							<button type="submit" class="btn-primary" disabled={saving}>
								{saving ? $_('common.loading') : $_('common.save')}
							</button>
						</div>
					</div>
				</form>

				<div class="form-section">
					<h2>{$_('budget.settings.accounts')}</h2>
					<div class="placeholder">
						<p>{$_('budget.settings.accountsPlaceholder')}</p>
					</div>
				</div>

				<div class="form-section danger-zone">
					<h2>{$_('budget.settings.dangerZone')}</h2>
					<p class="danger-text">
						{$_('budget.settings.deleteDescription')}
					</p>

					{#if !showDeleteConfirm}
						<button class="btn-danger" onclick={handleShowDeleteConfirm}>
							{$_('common.delete')} Budget
						</button>
					{:else}
						<div class="delete-confirm">
							<p class="confirm-text">{$_('budget.delete.confirm')}</p>
							<div class="confirm-actions">
								<button class="btn-secondary" onclick={handleCancelDelete} disabled={deleting}>
									{$_('common.cancel')}
								</button>
								<button class="btn-danger" onclick={handleDelete} disabled={deleting}>
									{deleting ? $_('common.loading') : $_('common.delete')}
								</button>
							</div>
						</div>
					{/if}
				</div>
			</div>
		{/if}
	</div>
</div>

<style>
	.page {
		max-width: 900px;
		margin: 0 auto;
		padding: var(--spacing-xl);
	}

	.container {
		min-height: 60vh;
	}

	.loading {
		text-align: center;
		padding: var(--spacing-xl);
		color: var(--text-secondary);
	}

	.page-header {
		margin-bottom: var(--spacing-xl);
	}

	h1 {
		font-size: var(--font-size-3xl);
		font-weight: 700;
		color: var(--text-primary);
	}

	.settings-container {
		display: flex;
		flex-direction: column;
		gap: var(--spacing-xl);
	}

	.form-section {
		background: var(--bg-card);
		border: 1px solid var(--border);
		border-radius: var(--radius-lg);
		padding: var(--spacing-xl);
	}

	.form-section h2 {
		font-size: var(--font-size-xl);
		font-weight: 600;
		color: var(--text-primary);
		margin-bottom: var(--spacing-lg);
	}

	form {
		display: flex;
		flex-direction: column;
		gap: var(--spacing-lg);
	}

	.form-group {
		display: flex;
		flex-direction: column;
		gap: var(--spacing-xs);
	}

	label {
		font-size: var(--font-size-base);
		font-weight: 500;
		color: var(--text-primary);
	}

	.required {
		color: var(--negative);
	}

	input {
		padding: var(--spacing-sm) var(--spacing-md);
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		font-size: var(--font-size-base);
		color: var(--text-primary);
		background: var(--bg-page);
		transition: border-color 0.2s;
	}

	input:focus {
		outline: none;
		border-color: var(--accent);
	}

	input:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}

	.hint {
		font-size: var(--font-size-sm);
		color: var(--text-secondary);
	}

	.info-row {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: var(--spacing-md);
		background: var(--bg-page);
		border-radius: var(--radius-md);
	}

	.info-row .label {
		font-weight: 500;
		color: var(--text-secondary);
	}

	.info-row .value {
		font-size: var(--font-size-lg);
		font-weight: 700;
		color: var(--positive);
	}

	.info-row .value.negative {
		color: var(--negative);
	}

	.placeholder {
		padding: var(--spacing-lg);
		background: var(--bg-page);
		border-radius: var(--radius-md);
		text-align: center;
		color: var(--text-secondary);
	}

	.error-message {
		padding: var(--spacing-sm) var(--spacing-md);
		background: rgba(239, 68, 68, 0.1);
		border: 1px solid var(--negative);
		border-radius: var(--radius-md);
		color: var(--negative);
		font-size: var(--font-size-sm);
	}

	.success-message {
		padding: var(--spacing-sm) var(--spacing-md);
		background: rgba(16, 185, 129, 0.1);
		border: 1px solid var(--positive);
		border-radius: var(--radius-md);
		color: var(--positive);
		font-size: var(--font-size-sm);
	}

	.form-actions {
		display: flex;
		gap: var(--spacing-md);
		justify-content: flex-end;
		margin-top: var(--spacing-md);
	}

	.btn-primary,
	.btn-secondary,
	.btn-danger {
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

	.btn-danger {
		background: var(--negative);
		color: white;
	}

	.btn-primary:disabled,
	.btn-secondary:disabled,
	.btn-danger:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}

	.btn-primary:hover:not(:disabled),
	.btn-secondary:hover:not(:disabled),
	.btn-danger:hover:not(:disabled) {
		opacity: 0.9;
	}

	.danger-zone {
		border-color: var(--negative);
	}

	.danger-text {
		color: var(--text-secondary);
		margin-bottom: var(--spacing-md);
		line-height: 1.6;
	}

	.delete-confirm {
		background: rgba(239, 68, 68, 0.05);
		border: 1px solid var(--negative);
		border-radius: var(--radius-md);
		padding: var(--spacing-md);
	}

	.confirm-text {
		color: var(--negative);
		font-weight: 500;
		margin-bottom: var(--spacing-md);
	}

	.confirm-actions {
		display: flex;
		gap: var(--spacing-md);
		justify-content: flex-end;
	}

	@media (max-width: 768px) {
		.page {
			padding: var(--spacing-md);
		}

		.form-section {
			padding: var(--spacing-lg);
		}

		.form-actions,
		.confirm-actions {
			flex-direction: column-reverse;
		}

		.btn-primary,
		.btn-secondary,
		.btn-danger {
			width: 100%;
		}
	}
</style>
