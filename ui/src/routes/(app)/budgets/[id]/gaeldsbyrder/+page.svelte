<script lang="ts">
	import { page } from '$app/stores';
	import { _ } from '$lib/i18n';
	import { listContainers, deleteContainer, createContainer, updateContainer } from '$lib/api/containers';
	import type { Container } from '$lib/api/containers';
	import ContainerModal from '$lib/components/ContainerModal.svelte';
	import { addToast } from '$lib/stores/toast.svelte';

	let budgetId: string = $derived($page.params.id as string);
	let allContainers = $state<Container[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let showModal = $state(false);
	let editingContainer = $state<Container | undefined>(undefined);
	let containerToDelete = $state<string | null>(null);

	// Filter to only show debt containers
	let debtContainers = $derived(allContainers.filter((c) => c.type === 'debt'));

	// Calculate total debt (sum of all debt balances)
	let totalDebt = $derived(
		debtContainers.reduce((sum, container) => sum + container.current_balance, 0)
	);

	// Reload containers when budgetId changes
	$effect(() => {
		const id = budgetId; // Track dependency
		loadContainers();
	});

	async function loadContainers() {
		try {
			loading = true;
			error = null;
			allContainers = await listContainers(budgetId);
		} catch (err) {
			error = err instanceof Error ? $_(err.message) : $_('common.error');
		} finally {
			loading = false;
		}
	}

	function formatCurrency(amountInOre: number): string {
		return (amountInOre / 100).toLocaleString('da-DK', {
			minimumFractionDigits: 2,
			maximumFractionDigits: 2
		});
	}

	function formatInterestFrequency(frequency: string | null): string {
		if (!frequency) return '';
		switch (frequency) {
			case 'monthly':
				return $_('gaeldsbyrder.interestMonthly');
			case 'quarterly':
				return $_('gaeldsbyrder.interestQuarterly');
			case 'yearly':
				return $_('gaeldsbyrder.interestYearly');
			default:
				return frequency;
		}
	}

	function handleAdd() {
		editingContainer = undefined;
		showModal = true;
	}

	function handleEdit(container: Container) {
		editingContainer = container;
		showModal = true;
	}

	async function handleSave(data: any) {
		try {
			if (editingContainer) {
				await updateContainer(budgetId, editingContainer.id, data);
				addToast($_('toast.updateSuccess'), 'success');
			} else {
				await createContainer(budgetId, data);
				addToast($_('toast.createSuccess'), 'success');
			}
			await loadContainers();
		} catch (err) {
			throw err;
		}
	}

	function confirmDelete(containerId: string) {
		containerToDelete = containerId;
	}

	function cancelDelete() {
		containerToDelete = null;
	}

	async function handleDelete() {
		if (!containerToDelete) return;

		try {
			await deleteContainer(budgetId, containerToDelete);
			containerToDelete = null;
			await loadContainers();
			addToast($_('toast.deleteSuccess'), 'success');
		} catch (err) {
			error = err instanceof Error ? $_(err.message) : $_('common.error');
		}
	}
</script>

<div class="page">
	<div class="page-header">
		<h1>{$_('gaeldsbyrder.title')}</h1>
		<button class="btn-primary" onclick={handleAdd}>
			<svg
				width="20"
				height="20"
				viewBox="0 0 24 24"
				fill="none"
				stroke="currentColor"
				stroke-width="2"
				stroke-linecap="round"
				stroke-linejoin="round"
			>
				<line x1="12" y1="5" x2="12" y2="19" />
				<line x1="5" y1="12" x2="19" y2="12" />
			</svg>
			{$_('gaeldsbyrder.add')}
		</button>
	</div>

	{#if loading}
		<div class="loading">{$_('common.loading')}</div>
	{:else if error}
		<div class="error-message">
			<p>{error}</p>
		</div>
	{:else}
		<!-- Total Debt Summary -->
		<section class="card summary-card">
			<div class="summary-content">
				<div class="summary-label">{$_('gaeldsbyrder.totalDebt')}</div>
				<div class="summary-value" class:negative={totalDebt < 0}>
					{formatCurrency(totalDebt)} kr
				</div>
			</div>
		</section>

		<!-- Debt Containers List -->
		{#if debtContainers.length === 0}
			<div class="placeholder">
				<p>{$_('gaeldsbyrder.empty')}</p>
			</div>
		{:else}
			<div class="container-list">
				{#each debtContainers as container (container.id)}
					<div class="container-card card">
						<div class="container-header">
							<div class="container-main">
								<h3 class="container-name">{container.name}</h3>
								<div class="container-balance negative">
									{formatCurrency(container.current_balance)} kr
								</div>
							</div>
						</div>

						<div class="container-details">
							<!-- Type badge -->
							<div class="detail-row">
								<span class="type-badge">
									{container.allow_withdrawals
										? $_('gaeldsbyrder.overdraftFacility')
										: $_('gaeldsbyrder.loan')}
								</span>
							</div>

							<!-- Credit limit -->
							{#if container.credit_limit !== null}
								<div class="detail-row">
									<span class="detail-label">{$_('gaeldsbyrder.creditLimit')}:</span>
									<span class="detail-value">
										{formatCurrency(Math.abs(container.credit_limit))} kr
									</span>
								</div>
							{/if}

							<!-- Interest info -->
							{#if container.interest_rate !== null}
								<div class="detail-row">
									<span class="detail-label">{$_('gaeldsbyrder.interestRate')}:</span>
									<span class="detail-value">
										{container.interest_rate}% {formatInterestFrequency(container.interest_frequency)}
									</span>
								</div>
							{/if}

							<!-- Required payment -->
							{#if container.required_payment !== null}
								<div class="detail-row">
									<span class="detail-label">{$_('gaeldsbyrder.requiredPayment')}:</span>
									<span class="detail-value">
										{formatCurrency(container.required_payment)} kr
									</span>
								</div>
							{/if}
						</div>

						<div class="container-actions">
							<button class="btn-secondary" onclick={() => handleEdit(container)}>
								<svg
									width="16"
									height="16"
									viewBox="0 0 24 24"
									fill="none"
									stroke="currentColor"
									stroke-width="2"
									stroke-linecap="round"
									stroke-linejoin="round"
								>
									<path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
									<path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
								</svg>
								{$_('common.edit')}
							</button>
							<button class="btn-danger" onclick={() => confirmDelete(container.id)}>
								<svg
									width="16"
									height="16"
									viewBox="0 0 24 24"
									fill="none"
									stroke="currentColor"
									stroke-width="2"
									stroke-linecap="round"
									stroke-linejoin="round"
								>
									<polyline points="3 6 5 6 21 6" />
									<path
										d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"
									/>
								</svg>
								{$_('common.delete')}
							</button>
						</div>
					</div>
				{/each}
			</div>
		{/if}
	{/if}
</div>

<!-- Container Modal -->
<ContainerModal bind:show={showModal} container={editingContainer} {budgetId} presetType="debt" onSave={handleSave} />

<!-- Delete Confirmation Modal -->
{#if containerToDelete}
	<div class="modal-backdrop" onclick={cancelDelete} role="presentation">
		<div class="modal" role="dialog" aria-modal="true" onclick={(e) => e.stopPropagation()}>
			<div class="modal-header">
				<h2>{$_('common.confirm')}</h2>
			</div>
			<div class="modal-body">
				<p>{$_('gaeldsbyrder.confirmDelete')}</p>
				<p class="warning-text">{$_('gaeldsbyrder.deleteWarning')}</p>
			</div>
			<div class="modal-footer">
				<button class="btn-secondary" onclick={cancelDelete}>
					{$_('common.cancel')}
				</button>
				<button class="btn-danger" onclick={handleDelete}>
					{$_('common.delete')}
				</button>
			</div>
		</div>
	</div>
{/if}

<style>
	.page {
		max-width: 1200px;
		margin: 0 auto;
		padding: var(--spacing-xl);
	}

	.page-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: var(--spacing-xl);
	}

	.page-header h1 {
		font-size: var(--font-size-2xl);
		font-weight: 700;
		color: var(--text-primary);
		margin: 0;
	}

	.btn-primary {
		display: flex;
		align-items: center;
		gap: var(--spacing-xs);
		padding: var(--spacing-sm) var(--spacing-lg);
		background: var(--accent);
		color: white;
		border: none;
		border-radius: var(--radius-md);
		font-size: var(--font-size-base);
		font-weight: 500;
		cursor: pointer;
		transition: opacity 0.2s;
	}

	.btn-primary:hover {
		opacity: 0.9;
	}

	.btn-secondary {
		display: flex;
		align-items: center;
		gap: var(--spacing-xs);
		padding: var(--spacing-sm) var(--spacing-md);
		background: transparent;
		color: var(--accent);
		border: 1px solid var(--accent);
		border-radius: var(--radius-md);
		font-size: var(--font-size-sm);
		font-weight: 500;
		cursor: pointer;
		transition: all 0.2s;
	}

	.btn-secondary:hover {
		background: var(--accent);
		color: white;
	}

	.btn-danger {
		display: flex;
		align-items: center;
		gap: var(--spacing-xs);
		padding: var(--spacing-sm) var(--spacing-md);
		background: transparent;
		color: var(--negative);
		border: 1px solid var(--negative);
		border-radius: var(--radius-md);
		font-size: var(--font-size-sm);
		font-weight: 500;
		cursor: pointer;
		transition: all 0.2s;
	}

	.btn-danger:hover {
		background: var(--negative);
		color: white;
	}

	.loading {
		text-align: center;
		padding: var(--spacing-xl);
		color: var(--text-secondary);
	}

	.error-message {
		padding: var(--spacing-md);
		background: rgba(239, 68, 68, 0.1);
		border: 1px solid var(--negative);
		border-radius: var(--radius-md);
		color: var(--negative);
	}

	.card {
		background: var(--bg-card);
		border: 1px solid var(--border);
		border-radius: var(--radius-lg);
		padding: var(--spacing-xl);
	}

	/* Summary Card */
	.summary-card {
		text-align: center;
		margin-bottom: var(--spacing-lg);
	}

	.summary-content {
		display: flex;
		flex-direction: column;
		gap: var(--spacing-sm);
	}

	.summary-label {
		font-size: var(--font-size-lg);
		color: var(--text-secondary);
		font-weight: 500;
	}

	.summary-value {
		font-size: 3rem;
		font-weight: 700;
	}

	.summary-value.negative {
		color: var(--negative);
	}

	/* Container List */
	.container-list {
		display: flex;
		flex-direction: column;
		gap: var(--spacing-md);
	}

	.container-card {
		display: flex;
		flex-direction: column;
		gap: var(--spacing-md);
	}

	.container-header {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
	}

	.container-main {
		flex: 1;
		display: flex;
		justify-content: space-between;
		align-items: center;
	}

	.container-name {
		font-size: var(--font-size-lg);
		font-weight: 600;
		color: var(--text-primary);
		margin: 0;
	}

	.container-balance {
		font-size: var(--font-size-xl);
		font-weight: 700;
	}

	.container-balance.negative {
		color: var(--negative);
	}

	.container-details {
		display: flex;
		flex-direction: column;
		gap: var(--spacing-sm);
		padding: var(--spacing-md);
		background: var(--bg-page);
		border-radius: var(--radius-md);
	}

	.detail-row {
		display: flex;
		align-items: center;
		gap: var(--spacing-sm);
	}

	.type-badge {
		display: inline-block;
		padding: var(--spacing-xs) var(--spacing-sm);
		background: var(--accent);
		color: white;
		border-radius: var(--radius-sm);
		font-size: var(--font-size-sm);
		font-weight: 500;
	}

	.detail-label {
		font-size: var(--font-size-sm);
		color: var(--text-secondary);
	}

	.detail-value {
		font-size: var(--font-size-sm);
		color: var(--text-primary);
		font-weight: 500;
	}

	.container-actions {
		display: flex;
		gap: var(--spacing-sm);
		justify-content: flex-end;
	}

	.placeholder {
		padding: var(--spacing-xl);
		text-align: center;
		color: var(--text-secondary);
		background: var(--bg-card);
		border: 1px solid var(--border);
		border-radius: var(--radius-lg);
	}

	/* Delete Modal */
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
		max-width: 500px;
		width: 100%;
		box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
	}

	.modal-header {
		padding: var(--spacing-lg) var(--spacing-xl);
		border-bottom: 1px solid var(--border);
	}

	.modal-header h2 {
		font-size: var(--font-size-xl);
		font-weight: 600;
		color: var(--text-primary);
		margin: 0;
	}

	.modal-body {
		padding: var(--spacing-xl);
		display: flex;
		flex-direction: column;
		gap: var(--spacing-md);
	}

	.modal-body p {
		margin: 0;
		color: var(--text-primary);
	}

	.warning-text {
		font-size: var(--font-size-sm);
		color: var(--text-secondary);
	}

	.modal-footer {
		display: flex;
		gap: var(--spacing-md);
		justify-content: flex-end;
		padding: var(--spacing-lg) var(--spacing-xl);
		border-top: 1px solid var(--border);
	}

	/* Responsive Design */
	@media (max-width: 768px) {
		.page {
			padding: var(--spacing-md);
		}

		.page-header {
			flex-direction: column;
			align-items: stretch;
			gap: var(--spacing-md);
		}

		.page-header h1 {
			font-size: var(--font-size-xl);
		}

		.btn-primary {
			justify-content: center;
		}

		.card {
			padding: var(--spacing-lg);
		}

		.summary-value {
			font-size: 2rem;
		}

		.container-main {
			flex-direction: column;
			align-items: flex-start;
			gap: var(--spacing-sm);
		}

		.container-balance {
			font-size: var(--font-size-lg);
		}

		.container-actions {
			flex-direction: column;
			width: 100%;
		}

		.btn-secondary,
		.btn-danger {
			width: 100%;
			justify-content: center;
		}

		.modal-footer {
			flex-direction: column-reverse;
		}

		.modal-footer button {
			width: 100%;
		}
	}
</style>
