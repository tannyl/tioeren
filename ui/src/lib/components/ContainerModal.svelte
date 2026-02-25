<script lang="ts">
	import { _ } from '$lib/i18n';
	import type { Container, ContainerType } from '$lib/api/containers';

	let {
		show = $bindable(false),
		container = undefined,
		budgetId,
		presetType = undefined,
		onSave
	}: {
		show?: boolean;
		container?: Container;
		budgetId: string;
		presetType?: ContainerType;
		onSave: (data: any) => Promise<void>;
	} = $props();

	// Form state variables
	let name = $state('');
	let containerType = $state<ContainerType>('cashbox');
	let startingBalance = $state('');

	// Bank link fields (collapsible section)
	let showBankDetails = $state(false);
	let bankName = $state('');
	let bankAccountName = $state('');
	let bankRegNumber = $state('');
	let bankAccountNumber = $state('');

	// Cashbox-specific
	let hasOverdraftLimit = $state(true);
	let overdraftLimit = $state('0');

	// Piggybank-specific
	let locked = $state(false);

	// Debt-specific
	let creditLimit = $state('0');
	let allowWithdrawals = $state(false);
	let interestRate = $state('');
	let interestFrequency = $state<string>('');
	let requiredPayment = $state('');

	// Form state
	let saving = $state(false);
	let error = $state<string | null>(null);

	// Reset form when modal opens or container changes
	$effect(() => {
		if (show) {
			if (container) {
				// Editing mode: fill fields from container
				name = container.name;
				containerType = container.type;
				startingBalance = (container.starting_balance / 100).toFixed(2);

				// Bank details
				showBankDetails = !!(container.bank_name || container.bank_account_name ||
					container.bank_reg_number || container.bank_account_number);
				bankName = container.bank_name || '';
				bankAccountName = container.bank_account_name || '';
				bankRegNumber = container.bank_reg_number || '';
				bankAccountNumber = container.bank_account_number || '';

				// Cashbox-specific
				if (container.overdraft_limit === null) {
					hasOverdraftLimit = false;
					overdraftLimit = '0';
				} else {
					hasOverdraftLimit = true;
					overdraftLimit = (Math.abs(container.overdraft_limit) / 100).toFixed(2);
				}

				// Piggybank-specific
				locked = container.locked || false;

				// Debt-specific
				creditLimit = container.credit_limit ? (Math.abs(container.credit_limit) / 100).toFixed(2) : '0';
				allowWithdrawals = container.allow_withdrawals || false;
				interestRate = container.interest_rate ? container.interest_rate.toString() : '';
				interestFrequency = container.interest_frequency || '';
				requiredPayment = container.required_payment ? (container.required_payment / 100).toFixed(2) : '';
			} else {
				// Creating mode: reset to defaults
				name = '';
				containerType = presetType || 'cashbox';
				startingBalance = '0.00';

				showBankDetails = false;
				bankName = '';
				bankAccountName = '';
				bankRegNumber = '';
				bankAccountNumber = '';

				hasOverdraftLimit = true;
				overdraftLimit = '0';

				locked = false;

				creditLimit = '0';
				allowWithdrawals = false;
				interestRate = '';
				interestFrequency = '';
				requiredPayment = '';
			}
			error = null;
		}
	});

	// Reset type-specific fields when container type changes
	$effect(() => {
		if (containerType === 'cashbox') {
			// Reset fields that don't apply to cashbox
			locked = false;
			creditLimit = '0';
			allowWithdrawals = false;
			interestRate = '';
			interestFrequency = '';
			requiredPayment = '';
		} else if (containerType === 'piggybank') {
			// Reset fields that don't apply to piggybank
			hasOverdraftLimit = true;
			overdraftLimit = '0';
			creditLimit = '0';
			allowWithdrawals = false;
			interestRate = '';
			interestFrequency = '';
			requiredPayment = '';
		} else if (containerType === 'debt') {
			// Reset fields that don't apply to debt
			hasOverdraftLimit = true;
			overdraftLimit = '0';
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
			const data: any = {
				name: name.trim(),
				type: containerType,
				starting_balance: Math.round(parseFloat(startingBalance || '0') * 100)
			};

			// Bank fields
			if (showBankDetails) {
				if (bankName.trim()) data.bank_name = bankName.trim();
				if (bankAccountName.trim()) data.bank_account_name = bankAccountName.trim();
				if (bankRegNumber.trim()) data.bank_reg_number = bankRegNumber.trim();
				if (bankAccountNumber.trim()) data.bank_account_number = bankAccountNumber.trim();
			} else {
				// When hiding bank details, send null to clear them
				data.bank_name = null;
				data.bank_account_name = null;
				data.bank_reg_number = null;
				data.bank_account_number = null;
			}

			// Type-specific fields
			if (containerType === 'cashbox') {
				data.overdraft_limit = !hasOverdraftLimit
					? null
					: -Math.abs(Math.round(parseFloat(overdraftLimit || '0') * 100));
			}

			if (containerType === 'piggybank') {
				data.locked = locked;
			}

			if (containerType === 'debt') {
				data.credit_limit = -Math.abs(Math.round(parseFloat(creditLimit || '0') * 100));
				data.allow_withdrawals = allowWithdrawals;
				if (interestRate && parseFloat(interestRate) > 0) {
					data.interest_rate = parseFloat(interestRate);
				}
				if (interestFrequency) {
					data.interest_frequency = interestFrequency;
				}
				if (requiredPayment && parseFloat(requiredPayment) > 0) {
					data.required_payment = Math.round(parseFloat(requiredPayment) * 100);
				}
			}

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

	function toggleBankDetails() {
		showBankDetails = !showBankDetails;
	}
</script>

{#if show}
	<div class="modal-backdrop" onclick={handleBackdropClick} role="presentation">
		<div class="modal" role="dialog" aria-modal="true" onclick={(e) => e.stopPropagation()}>
			<div class="modal-header">
				<h2>
					{container ? $_('container.modal.editTitle') : $_('container.modal.createTitle')}
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
					<!-- Common fields -->
					<div class="form-group">
						<label for="container-name">
							{$_('container.field.name')}
							<span class="required">*</span>
						</label>
						<input
							id="container-name"
							type="text"
							bind:value={name}
							required
							placeholder={$_('container.field.name')}
							disabled={saving}
						/>
					</div>

					<div class="form-row">
						<div class="form-group">
							<label for="container-type">{$_('container.field.type')}</label>
							<select
								id="container-type"
								bind:value={containerType}
								disabled={saving || !!container || !!presetType}
							>
								<option value="cashbox">{$_('container.type.cashbox')}</option>
								<option value="piggybank">{$_('container.type.piggybank')}</option>
								<option value="debt">{$_('container.type.debt')}</option>
							</select>
						</div>

						<div class="form-group">
							<label for="container-balance">{$_('container.field.startingBalance')}</label>
							<input
								id="container-balance"
								type="number"
								step="0.01"
								bind:value={startingBalance}
								placeholder="0.00"
								disabled={saving}
							/>
						</div>
					</div>

					<!-- Bank link section (collapsible) -->
					<div class="bank-section">
						<button
							type="button"
							class="section-toggle"
							onclick={toggleBankDetails}
							disabled={saving}
						>
							<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class:rotated={showBankDetails}>
								<polyline points="9 18 15 12 9 6"></polyline>
							</svg>
							<span>{$_('container.field.bankDetails')}</span>
						</button>
						<span class="hint">{$_('container.field.bankDetailsHint')}</span>

						{#if showBankDetails}
							<div class="bank-fields">
								<div class="form-group">
									<label for="bank-name">{$_('container.field.bankName')}</label>
									<input
										id="bank-name"
										type="text"
										bind:value={bankName}
										placeholder={$_('container.field.bankName')}
										disabled={saving}
									/>
								</div>

								<div class="form-group">
									<label for="bank-account-name">{$_('container.field.bankAccountName')}</label>
									<input
										id="bank-account-name"
										type="text"
										bind:value={bankAccountName}
										placeholder={$_('container.field.bankAccountName')}
										disabled={saving}
									/>
								</div>

								<div class="form-row">
									<div class="form-group">
										<label for="bank-reg-number">{$_('container.field.bankRegNumber')}</label>
										<input
											id="bank-reg-number"
											type="text"
											bind:value={bankRegNumber}
											placeholder={$_('container.field.bankRegNumber')}
											disabled={saving}
										/>
									</div>

									<div class="form-group">
										<label for="bank-account-number">{$_('container.field.bankAccountNumber')}</label>
										<input
											id="bank-account-number"
											type="text"
											bind:value={bankAccountNumber}
											placeholder={$_('container.field.bankAccountNumber')}
											disabled={saving}
										/>
									</div>
								</div>
							</div>
						{/if}
					</div>

					<!-- Type-specific fields -->
					{#if containerType === 'cashbox'}
						<div class="form-group">
							<label class="checkbox-label">
								<input type="checkbox" bind:checked={hasOverdraftLimit} disabled={saving} />
								<span>{$_('container.field.hasOverdraftLimit')}</span>
							</label>
							<span class="hint">{$_('container.field.hasOverdraftLimitHint')}</span>
						</div>

						{#if hasOverdraftLimit}
							<div class="form-group">
								<label for="overdraft-limit">{$_('container.field.overdraftLimit')}</label>
								<span class="hint">{$_('container.field.overdraftLimitHint')}</span>
								<input
									id="overdraft-limit"
									type="number"
									step="0.01"
									min="0"
									bind:value={overdraftLimit}
									placeholder="0.00"
									disabled={saving}
								/>
							</div>
						{/if}
					{/if}

					{#if containerType === 'piggybank'}
						<div class="form-group">
							<label class="checkbox-label">
								<input type="checkbox" bind:checked={locked} disabled={saving} />
								<span>{$_('container.field.locked')}</span>
							</label>
							<span class="hint">{$_('container.field.lockedHint')}</span>
						</div>
					{/if}

					{#if containerType === 'debt'}
						<div class="form-group">
							<label for="credit-limit">
								{$_('container.field.creditLimit')}
								<span class="required">*</span>
							</label>
							<span class="hint">{$_('container.field.creditLimitHint')}</span>
							<input
								id="credit-limit"
								type="number"
								step="0.01"
								min="0"
								bind:value={creditLimit}
								placeholder="0.00"
								disabled={saving}
								required
							/>
						</div>

						<div class="form-group">
							<label class="checkbox-label">
								<input type="checkbox" bind:checked={allowWithdrawals} disabled={saving} />
								<span>{$_('container.field.allowWithdrawals')}</span>
							</label>
							<span class="hint">{$_('container.field.allowWithdrawalsHint')}</span>
						</div>

						<div class="form-row">
							<div class="form-group">
								<label for="interest-rate">{$_('container.field.interestRate')}</label>
								<span class="hint">{$_('container.field.interestRateHint')}</span>
								<input
									id="interest-rate"
									type="number"
									step="0.01"
									min="0"
									bind:value={interestRate}
									placeholder="0.00"
									disabled={saving}
								/>
							</div>

							{#if interestRate && parseFloat(interestRate) > 0}
								<div class="form-group">
									<label for="interest-frequency">{$_('container.field.interestFrequency')}</label>
									<select id="interest-frequency" bind:value={interestFrequency} disabled={saving}>
										<option value="">-</option>
										<option value="monthly">{$_('container.field.interestFrequencyMonthly')}</option>
										<option value="quarterly">{$_('container.field.interestFrequencyQuarterly')}</option>
										<option value="yearly">{$_('container.field.interestFrequencyYearly')}</option>
									</select>
								</div>
							{/if}
						</div>

						<div class="form-group">
							<label for="required-payment">{$_('container.field.requiredPayment')}</label>
							<span class="hint">{$_('container.field.requiredPaymentHint')}</span>
							<input
								id="required-payment"
								type="number"
								step="0.01"
								min="0"
								bind:value={requiredPayment}
								placeholder="0.00"
								disabled={saving}
							/>
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

	/* Bank section styles */
	.bank-section {
		display: flex;
		flex-direction: column;
		gap: var(--spacing-xs);
		padding: var(--spacing-md);
		background: var(--bg-page);
		border-radius: var(--radius-md);
	}

	.section-toggle {
		display: flex;
		align-items: center;
		gap: var(--spacing-sm);
		background: none;
		border: none;
		color: var(--text-primary);
		font-size: var(--font-size-base);
		font-weight: 500;
		cursor: pointer;
		padding: var(--spacing-xs) 0;
		transition: color 0.2s;
		text-align: left;
	}

	.section-toggle:hover:not(:disabled) {
		color: var(--accent);
	}

	.section-toggle:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}

	.section-toggle svg {
		transition: transform 0.2s;
	}

	.section-toggle svg.rotated {
		transform: rotate(90deg);
	}

	.bank-fields {
		display: flex;
		flex-direction: column;
		gap: var(--spacing-md);
		margin-top: var(--spacing-md);
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
