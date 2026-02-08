<script lang="ts">
	import { page } from '$app/stores';
	import { _ } from '$lib/i18n';
	import { getBudget, updateBudget, deleteBudget } from '$lib/api/budgets';
	import { budgetStore } from '$lib/stores/budget';
	import { goto } from '$app/navigation';
	import type { Budget } from '$lib/api/budgets';
	import {
		listAccounts,
		createAccount,
		updateAccount,
		deleteAccount
	} from '$lib/api/accounts';
	import type { Account } from '$lib/api/accounts';
	import AccountModal from '$lib/components/AccountModal.svelte';
	import { addToast } from '$lib/stores/toast.svelte';

	// Get budget ID from route params and assert it exists (route guarantees it)
	let budgetId: string = $derived($page.params.id as string);
	let budget = $state<Budget | null>(null);
	let accounts = $state<Account[]>([]);
	let name = $state('');
	let warningThreshold = $state('');
	let loading = $state(true);
	let loadingAccounts = $state(false);
	let saving = $state(false);
	let deleting = $state(false);
	let showDeleteConfirm = $state(false);
	let error = $state<string | null>(null);
	let saveSuccess = $state(false);
	let showAccountModal = $state(false);
	let editingAccount = $state<Account | undefined>(undefined);
	let accountToDelete = $state<string | null>(null);

	// Reload data when budgetId changes
	$effect(() => {
		const id = budgetId; // Track dependency
		loadBudget();
		loadAccounts();
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
			error = err instanceof Error ? $_(err.message) : $_('common.error');
		} finally {
			loading = false;
		}
	}

	async function loadAccounts() {
		try {
			loadingAccounts = true;
			accounts = await listAccounts(budgetId);
		} catch (err) {
			console.error('Failed to load accounts:', err);
		} finally {
			loadingAccounts = false;
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
			addToast($_('toast.saveSuccess'), 'success');

			// Clear success message after 3 seconds
			setTimeout(() => {
				saveSuccess = false;
			}, 3000);
		} catch (err) {
			error = err instanceof Error ? $_(err.message) : $_('common.error');
			addToast(error, 'error');
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
			addToast($_('toast.deleteSuccess'), 'success');
			goto('/budgets');
		} catch (err) {
			error = err instanceof Error ? $_(err.message) : $_('common.error');
			addToast(error, 'error');
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

	function handleAddAccount() {
		editingAccount = undefined;
		showAccountModal = true;
	}

	function handleEditAccount(account: Account) {
		editingAccount = account;
		showAccountModal = true;
	}

	async function handleSaveAccount(data: any) {
		try {
			if (editingAccount) {
				await updateAccount(budgetId, editingAccount.id, data);
				addToast($_('toast.updateSuccess'), 'success');
			} else {
				await createAccount(budgetId, data);
				addToast($_('toast.createSuccess'), 'success');
			}
			await loadAccounts();
		} catch (err) {
			throw err;
		}
	}

	function handleShowDeleteAccount(accountId: string) {
		accountToDelete = accountId;
	}

	function handleCancelDeleteAccount() {
		accountToDelete = null;
	}

	async function handleDeleteAccount() {
		if (!accountToDelete) return;

		try {
			await deleteAccount(budgetId, accountToDelete);
			await loadAccounts();
			addToast($_('toast.deleteSuccess'), 'success');
			accountToDelete = null;
		} catch (err) {
			error = err instanceof Error ? $_(err.message) : $_('common.error');
			addToast(error, 'error');
		}
	}

	function getPurposeLabel(purpose: string): string {
		return $_(`account.purpose.${purpose}`);
	}

	function getDatasourceLabel(datasource: string): string {
		return $_(`account.datasource.${datasource}`);
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
					<div class="section-header">
						<h2>{$_('budget.settings.accounts')}</h2>
						<button type="button" class="btn-primary" onclick={handleAddAccount}>
							{$_('account.list.add')}
						</button>
					</div>

					{#if loadingAccounts}
						<div class="placeholder">
							<p>{$_('common.loading')}</p>
						</div>
					{:else if accounts.length === 0}
						<div class="placeholder">
							<p>{$_('account.list.empty')}</p>
						</div>
					{:else}
						<div class="account-list">
							{#each accounts as account (account.id)}
								<div class="account-item">
									<div class="account-info">
										<div class="account-name">{account.name}</div>
										<div class="account-meta">
											<span class="account-purpose">{getPurposeLabel(account.purpose)}</span>
											<span class="separator">•</span>
											<span class="account-datasource">{getDatasourceLabel(account.datasource)}</span>
										</div>
									</div>
									<div class="account-balance">
										{#if account.current_balance !== undefined}
											<span class="balance" class:negative={account.current_balance < 0}>
												{formatCurrency(account.current_balance)} {account.currency}
											</span>
										{:else}
											<span class="balance" class:negative={account.starting_balance < 0}>
												{formatCurrency(account.starting_balance)} {account.currency}
											</span>
										{/if}
									</div>
									<div class="account-actions">
										<button
											type="button"
											class="btn-icon"
											onclick={() => handleEditAccount(account)}
											title={$_('common.edit')}
										>
											<svg
												width="20"
												height="20"
												viewBox="0 0 24 24"
												fill="none"
												stroke="currentColor"
												stroke-width="2"
											>
												<path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
												<path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
											</svg>
										</button>
										{#if accountToDelete === account.id}
											<div class="delete-confirm-inline">
												<button
													type="button"
													class="btn-icon btn-danger"
													onclick={handleDeleteAccount}
													title={$_('common.confirm')}
												>
													<svg
														width="20"
														height="20"
														viewBox="0 0 24 24"
														fill="none"
														stroke="currentColor"
														stroke-width="2"
													>
														<polyline points="20 6 9 17 4 12" />
													</svg>
												</button>
												<button
													type="button"
													class="btn-icon"
													onclick={handleCancelDeleteAccount}
													title={$_('common.cancel')}
												>
													<svg
														width="20"
														height="20"
														viewBox="0 0 24 24"
														fill="none"
														stroke="currentColor"
														stroke-width="2"
													>
														<line x1="18" y1="6" x2="6" y2="18" />
														<line x1="6" y1="6" x2="18" y2="18" />
													</svg>
												</button>
											</div>
										{:else}
											<button
												type="button"
												class="btn-icon btn-danger"
												onclick={() => handleShowDeleteAccount(account.id)}
												title={$_('common.delete')}
											>
												<svg
													width="20"
													height="20"
													viewBox="0 0 24 24"
													fill="none"
													stroke="currentColor"
													stroke-width="2"
												>
													<polyline points="3 6 5 6 21 6" />
													<path
														d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"
													/>
												</svg>
											</button>
										{/if}
									</div>
								</div>
							{/each}
						</div>
					{/if}
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

<AccountModal
	bind:show={showAccountModal}
	account={editingAccount}
	{budgetId}
	onSave={handleSaveAccount}
/>

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

	.section-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: var(--spacing-lg);
	}

	.section-header h2 {
		margin-bottom: 0;
	}

	.account-list {
		display: flex;
		flex-direction: column;
		gap: var(--spacing-sm);
	}

	.account-item {
		display: flex;
		align-items: center;
		gap: var(--spacing-md);
		padding: var(--spacing-md);
		background: var(--bg-page);
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		transition: border-color 0.2s;
	}

	.account-item:hover {
		border-color: var(--accent);
	}

	.account-info {
		flex: 1;
		min-width: 0;
	}

	.account-name {
		font-size: var(--font-size-base);
		font-weight: 500;
		color: var(--text-primary);
		margin-bottom: var(--spacing-xs);
	}

	.account-meta {
		font-size: var(--font-size-sm);
		color: var(--text-secondary);
		display: flex;
		align-items: center;
		gap: var(--spacing-xs);
	}

	.separator {
		opacity: 0.5;
	}

	.account-balance {
		flex-shrink: 0;
	}

	.balance {
		font-size: var(--font-size-lg);
		font-weight: 700;
		color: var(--positive);
	}

	.balance.negative {
		color: var(--negative);
	}

	.account-actions {
		display: flex;
		gap: var(--spacing-xs);
		flex-shrink: 0;
	}

	.delete-confirm-inline {
		display: flex;
		gap: var(--spacing-xs);
	}

	.btn-icon {
		padding: var(--spacing-xs);
		background: none;
		border: none;
		color: var(--text-secondary);
		cursor: pointer;
		border-radius: var(--radius-md);
		transition: all 0.2s;
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.btn-icon:hover {
		background: var(--bg-card);
		color: var(--text-primary);
	}

	.btn-icon.btn-danger {
		color: var(--negative);
	}

	.btn-icon.btn-danger:hover {
		background: rgba(239, 68, 68, 0.1);
		color: var(--negative);
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

		.section-header {
			flex-direction: column;
			align-items: stretch;
			gap: var(--spacing-md);
		}

		.section-header .btn-primary {
			width: 100%;
		}

		.account-item {
			flex-wrap: wrap;
		}

		.account-info {
			flex-basis: 100%;
		}

		.account-balance {
			flex: 1;
		}
	}
</style>
