<script lang="ts">
	import { _ } from '$lib/i18n';
	import type { Account } from '$lib/api/accounts';

	let {
		show = $bindable(false),
		account = undefined,
		budgetId,
		onSave
	}: {
		show?: boolean;
		account?: Account;
		budgetId: string;
		onSave: (data: any) => Promise<void>;
	} = $props();

	let name = $state('');
	let purpose = $state<'normal' | 'savings' | 'loan' | 'kassekredit'>('normal');
	let datasource = $state<'bank' | 'cash' | 'virtual'>('bank');
	let startingBalance = $state('');
	let currency = $state('DKK');
	let hasCreditLimit = $state(true);
	let creditLimit = $state<string>('0');
	let locked = $state(false);
	let saving = $state(false);
	let error = $state<string | null>(null);

	// Reset form when account changes or modal opens
	$effect(() => {
		if (show) {
			if (account) {
				name = account.name;
				purpose = account.purpose;
				datasource = account.datasource;
				startingBalance = (account.starting_balance / 100).toFixed(2);
				currency = account.currency;
				// credit_limit from API is negative or null
				if (account.credit_limit === null) {
					hasCreditLimit = false;
					creditLimit = '0';
				} else {
					hasCreditLimit = true;
					creditLimit = (Math.abs(account.credit_limit) / 100).toFixed(2);
				}
				locked = account.locked;
			} else {
				name = '';
				purpose = 'normal';
				datasource = 'bank';
				startingBalance = '0.00';
				currency = 'DKK';
				hasCreditLimit = true;
				creditLimit = '0';
				locked = false;
			}
			error = null;
		}
	});

	// Reset locked when purpose changes away from savings
	$effect(() => {
		if (purpose !== 'savings') {
			locked = false;
		}
	});

	function handleClose() {
		show = false;
	}

	async function handleSubmit(event: Event) {
		event.preventDefault();
		error = null;

		if (!name.trim()) {
			error = $_('common.error');
			return;
		}

		saving = true;

		try {
			// Convert DKK to øre
			const balanceInOre = Math.round(parseFloat(startingBalance || '0') * 100);

			// Convert credit_limit: unchecked = null (no limit), checked = negate to negative øre
			const creditLimitInOre = !hasCreditLimit
				? null
				: -Math.abs(Math.round(parseFloat(creditLimit || '0') * 100));

			const data = {
				name: name.trim(),
				purpose,
				datasource,
				starting_balance: balanceInOre,
				currency,
				credit_limit: creditLimitInOre,
				locked: purpose === 'savings' ? locked : false
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
		<div class="modal" role="dialog" aria-modal="true" onclick={(e) => e.stopPropagation()}>
			<div class="modal-header">
				<h2>
					{account ? $_('account.modal.editTitle') : $_('account.modal.createTitle')}
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
						<label for="account-name">
							{$_('account.field.name')}
							<span class="required">*</span>
						</label>
						<input
							id="account-name"
							type="text"
							bind:value={name}
							required
							placeholder={$_('account.field.name')}
							disabled={saving}
						/>
					</div>

					<div class="form-row">
						<div class="form-group">
							<label for="account-purpose">{$_('account.field.purpose')}</label>
							<select id="account-purpose" bind:value={purpose} disabled={saving}>
								<option value="normal">{$_('account.purpose.normal')}</option>
								<option value="savings">{$_('account.purpose.savings')}</option>
								<option value="loan">{$_('account.purpose.loan')}</option>
								<option value="kassekredit">{$_('account.purpose.kassekredit')}</option>
							</select>
						</div>

						<div class="form-group">
							<label for="account-datasource">{$_('account.field.datasource')}</label>
							<select id="account-datasource" bind:value={datasource} disabled={saving}>
								<option value="bank">{$_('account.datasource.bank')}</option>
								<option value="cash">{$_('account.datasource.cash')}</option>
								<option value="virtual">{$_('account.datasource.virtual')}</option>
							</select>
						</div>
					</div>

					<div class="form-row">
						<div class="form-group">
							<label for="account-balance">{$_('account.field.startingBalance')}</label>
							<input
								id="account-balance"
								type="number"
								step="0.01"
								bind:value={startingBalance}
								placeholder="0.00"
								disabled={saving}
							/>
						</div>

						<div class="form-group">
							<label for="account-currency">{$_('account.field.currency')}</label>
							<input
								id="account-currency"
								type="text"
								bind:value={currency}
								placeholder="DKK"
								disabled={saving}
								maxlength="3"
							/>
						</div>
					</div>

					<div class="form-group">
						<label class="checkbox-label">
							<input type="checkbox" bind:checked={hasCreditLimit} disabled={saving} />
							<span>{$_('account.field.hasCreditLimit')}</span>
						</label>
						<span class="hint">{$_('account.field.hasCreditLimitHint')}</span>
					</div>

					{#if hasCreditLimit}
						<div class="form-group">
							<label for="account-credit-limit">{$_('account.field.creditLimit')}</label>
							<span class="hint">{$_('account.field.creditLimitHint')}</span>
							<input
								id="account-credit-limit"
								type="number"
								step="0.01"
								min="0"
								bind:value={creditLimit}
								placeholder="0.00"
								disabled={saving}
							/>
						</div>
					{/if}

					{#if purpose === 'savings'}
						<div class="form-group">
							<label class="checkbox-label">
								<input type="checkbox" bind:checked={locked} disabled={saving} />
								<span>{$_('account.field.locked')}</span>
							</label>
							<span class="hint">{$_('account.field.lockedHint')}</span>
						</div>
					{/if}

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

	.form-row {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: var(--spacing-md);
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
	select:focus {
		outline: none;
		border-color: var(--accent);
	}

	input[type='text']:disabled,
	input[type='number']:disabled,
	select:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}

	.checkbox-label {
		display: flex;
		align-items: center;
		gap: var(--spacing-sm);
		cursor: pointer;
		flex-direction: row;
	}

	.checkbox-label input[type='checkbox'] {
		cursor: pointer;
		width: 20px;
		height: 20px;
	}

	.checkbox-label span {
		font-weight: normal;
	}

	.hint {
		font-size: var(--font-size-sm);
		color: var(--text-secondary);
		font-weight: normal;
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
