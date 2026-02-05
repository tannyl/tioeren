<script lang="ts">
	import { _ } from '$lib/i18n';
	import type { Account } from '$lib/api/accounts';

	let {
		show = $bindable(false),
		budgetId,
		accounts,
		onSave
	}: {
		show?: boolean;
		budgetId: string;
		accounts: Account[];
		onSave: (data: any) => Promise<void>;
	} = $props();

	let date = $state('');
	let description = $state('');
	let amount = $state('');
	let accountId = $state('');
	let saving = $state(false);
	let error = $state<string | null>(null);

	// Reset form when modal opens
	$effect(() => {
		if (show) {
			// Set today's date in YYYY-MM-DD format
			const today = new Date();
			date = today.toISOString().split('T')[0];
			description = '';
			amount = '';
			accountId = accounts.length > 0 ? accounts[0].id : '';
			error = null;
		}
	});

	function handleClose() {
		show = false;
	}

	async function handleSubmit(event: Event) {
		event.preventDefault();
		error = null;

		if (!description.trim() || !amount || !accountId) {
			error = $_('common.error');
			return;
		}

		saving = true;

		try {
			// Convert DKK to øre (multiply by 100)
			const amountInOre = Math.round(parseFloat(amount) * 100);

			const data = {
				account_id: accountId,
				date,
				amount: amountInOre,
				description: description.trim()
			};

			await onSave(data);
			show = false;
		} catch (err) {
			error = err instanceof Error ? $_(err.message) : $_('common.error');
		} finally {
			saving = false;
		}
	}

	// Handle clicking outside modal
	function handleBackdropClick(event: MouseEvent) {
		if (event.target === event.currentTarget) {
			handleClose();
		}
	}
</script>

{#if show}
	<div class="modal-backdrop" onclick={handleBackdropClick} role="presentation">
		<div class="modal" role="dialog" aria-modal="true">
			<div class="modal-header">
				<h2>
					{$_('transaction.create.title')}
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
						<label for="transaction-date">
							{$_('transaction.field.date')}
							<span class="required">*</span>
						</label>
						<input
							id="transaction-date"
							type="date"
							bind:value={date}
							required
							disabled={saving}
						/>
					</div>

					<div class="form-group">
						<label for="transaction-description">
							{$_('transaction.field.description')}
							<span class="required">*</span>
						</label>
						<input
							id="transaction-description"
							type="text"
							bind:value={description}
							required
							placeholder={$_('transaction.field.description')}
							disabled={saving}
						/>
					</div>

					<div class="form-group">
						<label for="transaction-amount">
							{$_('transaction.field.amount')}
							<span class="required">*</span>
						</label>
						<input
							id="transaction-amount"
							type="number"
							step="0.01"
							bind:value={amount}
							required
							placeholder="0.00"
							disabled={saving}
						/>
						<small class="hint">{$_('transaction.create.amountHint')}</small>
					</div>

					<div class="form-group">
						<label for="transaction-account">
							{$_('transaction.field.account')}
							<span class="required">*</span>
						</label>
						<select id="transaction-account" bind:value={accountId} required disabled={saving}>
							{#each accounts as account (account.id)}
								<option value={account.id}>{account.name}</option>
							{/each}
						</select>
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
		max-width: 600px;
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

	label {
		font-size: var(--font-size-base);
		font-weight: 500;
		color: var(--text-primary);
	}

	.required {
		color: var(--negative);
	}

	.hint {
		font-size: var(--font-size-sm);
		color: var(--text-secondary);
		font-style: italic;
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
