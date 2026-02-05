<script lang="ts">
	import { _ } from '$lib/i18n';
	import { createBudget } from '$lib/api/budgets';
	import { budgetStore } from '$lib/stores/budget';
	import { goto } from '$app/navigation';
	import { addToast } from '$lib/stores/toast.svelte';

	let name = $state('');
	let warningThreshold = $state('');
	let loading = $state(false);
	let error = $state<string | null>(null);

	async function handleSubmit(event: Event) {
		event.preventDefault();
		error = null;

		if (!name.trim()) {
			error = $_('budget.messages.nameRequired');
			addToast(error, 'error');
			return;
		}

		loading = true;

		try {
			// Convert DKK to øre (multiply by 100)
			const thresholdInOre = warningThreshold
				? Math.round(parseFloat(warningThreshold) * 100)
				: undefined;

			const budget = await createBudget({
				name: name.trim(),
				warning_threshold: thresholdInOre
			});

			// Add to store
			budgetStore.addBudget(budget);

			addToast($_('toast.createSuccess'), 'success');

			// Redirect to settings page
			goto(`/budgets/${budget.id}/settings`);
		} catch (err) {
			error = err instanceof Error ? $_(err.message) : $_('common.error');
			addToast(error, 'error');
			loading = false;
		}
	}

	function handleCancel() {
		goto('/budgets');
	}
</script>

<div class="page">
	<div class="form-container">
		<header>
			<h1>{$_('budget.create.title')}</h1>
		</header>

		<form onsubmit={handleSubmit}>
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
					disabled={loading}
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
					disabled={loading}
				/>
				<span class="hint">{$_('budget.field.warningThresholdHint')}</span>
			</div>

			{#if error}
				<div class="error-message">
					{error}
				</div>
			{/if}

			<div class="form-actions">
				<button type="button" class="btn-secondary" onclick={handleCancel} disabled={loading}>
					{$_('common.cancel')}
				</button>
				<button type="submit" class="btn-primary" disabled={loading}>
					{loading ? $_('common.loading') : $_('common.save')}
				</button>
			</div>
		</form>
	</div>
</div>

<style>
	.page {
		max-width: 600px;
		margin: 0 auto;
		padding: var(--spacing-xl);
	}

	.form-container {
		background: var(--bg-card);
		border: 1px solid var(--border);
		border-radius: var(--radius-lg);
		padding: var(--spacing-xl);
	}

	header {
		margin-bottom: var(--spacing-xl);
	}

	h1 {
		font-size: var(--font-size-2xl);
		font-weight: 700;
		color: var(--text-primary);
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

	.error-message {
		padding: var(--spacing-sm) var(--spacing-md);
		background: rgba(239, 68, 68, 0.1);
		border: 1px solid var(--negative);
		border-radius: var(--radius-md);
		color: var(--negative);
		font-size: var(--font-size-sm);
	}

	.form-actions {
		display: flex;
		gap: var(--spacing-md);
		justify-content: flex-end;
		margin-top: var(--spacing-md);
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
		.page {
			padding: var(--spacing-md);
		}

		.form-container {
			padding: var(--spacing-lg);
		}

		.form-actions {
			flex-direction: column-reverse;
		}

		.btn-primary,
		.btn-secondary {
			width: 100%;
		}
	}
</style>
