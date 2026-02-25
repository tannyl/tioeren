<script lang="ts">
	import { page } from '$app/stores';
	import { _ } from '$lib/i18n';
	import { listContainers, deleteContainer } from '$lib/api/containers';
	import type { Container } from '$lib/api/containers';
	import ContainerModal from '$lib/components/ContainerModal.svelte';
	import { createContainer, updateContainer } from '$lib/api/containers';
	import { addToast } from '$lib/stores/toast.svelte';

	let budgetId: string = $derived($page.params.id as string);
	let containers = $state<Container[]>([]);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let showModal = $state(false);
	let editingContainer = $state<Container | undefined>(undefined);
	let containerToDelete = $state<string | null>(null);

	// Reload containers when budgetId changes
	$effect(() => {
		const id = budgetId; // Track dependency
		loadContainers();
	});

	async function loadContainers() {
		try {
			loading = true;
			error = null;
			const allContainers = await listContainers(budgetId);
			// Filter to only piggybank containers
			containers = allContainers.filter((c) => c.type === 'piggybank');
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

	// Calculate total savings (sum of all piggybank balances)
	let totalSavings = $derived(
		containers.reduce((sum, container) => sum + container.current_balance, 0)
	);

	function handleAdd() {
		editingContainer = undefined;
		showModal = true;
	}

	function handleEdit(container: Container) {
		editingContainer = container;
		showModal = true;
	}

	function handleDeleteClick(containerId: string) {
		containerToDelete = containerId;
	}

	function handleDeleteCancel() {
		containerToDelete = null;
	}

	async function handleDeleteConfirm() {
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
			throw err; // Re-throw so modal can show error
		}
	}

	function getBankInfo(container: Container): string | null {
		const parts: string[] = [];
		if (container.bank_name) parts.push(container.bank_name);
		if (container.bank_reg_number && container.bank_account_number) {
			parts.push(`${container.bank_reg_number}-${container.bank_account_number}`);
		}
		return parts.length > 0 ? parts.join(' • ') : null;
	}
</script>

<div class="page">
	<div class="page-header">
		<h1>{$_('sparegrise.title')}</h1>
		<button class="btn-primary" onclick={handleAdd}>
			<svg
				xmlns="http://www.w3.org/2000/svg"
				width="20"
				height="20"
				viewBox="0 0 24 24"
				fill="none"
				stroke="currentColor"
				stroke-width="2"
				stroke-linecap="round"
				stroke-linejoin="round"
			>
				<path d="M5 12h14" />
				<path d="M12 5v14" />
			</svg>
			{$_('sparegrise.add')}
		</button>
	</div>

	{#if loading}
		<div class="loading">
			<p>{$_('common.loading')}</p>
		</div>
	{:else if error}
		<div class="error-message">
			<p>{error}</p>
		</div>
	{:else}
		<div class="content">
			<!-- Total Savings Summary Card -->
			<section class="card summary-card">
				<div class="summary-content">
					<h2 class="summary-label">{$_('sparegrise.totalSavings')}</h2>
					<div class="summary-amount" class:negative={totalSavings < 0}>
						{formatCurrency(totalSavings)} kr
					</div>
				</div>
			</section>

			<!-- Piggybank List -->
			{#if containers.length === 0}
				<section class="card empty-state">
					<p>{$_('sparegrise.empty')}</p>
				</section>
			{:else}
				<div class="container-list">
					{#each containers as container (container.id)}
						<div class="card container-card">
							<div class="container-header">
								<div class="container-main">
									<h3 class="container-name">{container.name}</h3>
									<div class="container-balance" class:negative={container.current_balance < 0}>
										{formatCurrency(container.current_balance)} kr
									</div>
								</div>
								<div class="container-actions">
									<button
										class="btn-icon"
										onclick={() => handleEdit(container)}
										title={$_('common.edit')}
									>
										<svg
											xmlns="http://www.w3.org/2000/svg"
											width="18"
											height="18"
											viewBox="0 0 24 24"
											fill="none"
											stroke="currentColor"
											stroke-width="2"
											stroke-linecap="round"
											stroke-linejoin="round"
										>
											<path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z" />
											<path d="m15 5 4 4" />
										</svg>
									</button>
									<button
										class="btn-icon btn-delete"
										onclick={() => handleDeleteClick(container.id)}
										title={$_('common.delete')}
									>
										<svg
											xmlns="http://www.w3.org/2000/svg"
											width="18"
											height="18"
											viewBox="0 0 24 24"
											fill="none"
											stroke="currentColor"
											stroke-width="2"
											stroke-linecap="round"
											stroke-linejoin="round"
										>
											<path d="M3 6h18" />
											<path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6" />
											<path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2" />
										</svg>
									</button>
								</div>
							</div>

							{#if container.locked}
								<div class="container-locked">
									<svg
										xmlns="http://www.w3.org/2000/svg"
										width="16"
										height="16"
										viewBox="0 0 24 24"
										fill="none"
										stroke="currentColor"
										stroke-width="2"
										stroke-linecap="round"
										stroke-linejoin="round"
									>
										<rect width="18" height="11" x="3" y="11" rx="2" ry="2" />
										<path d="M7 11V7a5 5 0 0 1 10 0v4" />
									</svg>
									<span>{$_('sparegrise.locked')}</span>
								</div>
							{/if}

							{#if getBankInfo(container)}
								<div class="container-bank">
									{getBankInfo(container)}
								</div>
							{/if}
						</div>
					{/each}
				</div>
			{/if}
		</div>
	{/if}
</div>

<!-- Delete Confirmation Dialog -->
{#if containerToDelete}
	<div class="modal-backdrop" onclick={handleDeleteCancel} role="presentation">
		<div class="modal" role="dialog" aria-modal="true" onclick={(e) => e.stopPropagation()}>
			<div class="modal-header">
				<h2>{$_('sparegrise.confirmDelete')}</h2>
			</div>
			<div class="modal-body">
				<p>{$_('sparegrise.deleteWarning')}</p>
			</div>
			<div class="modal-footer">
				<button class="btn-secondary" onclick={handleDeleteCancel}>
					{$_('common.cancel')}
				</button>
				<button class="btn-danger" onclick={handleDeleteConfirm}>
					{$_('common.delete')}
				</button>
			</div>
		</div>
	</div>
{/if}

<!-- Container Modal -->
<ContainerModal
	bind:show={showModal}
	container={editingContainer}
	{budgetId}
	presetType="piggybank"
	onSave={handleSave}
/>

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
		gap: var(--spacing-sm);
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

	.content {
		display: flex;
		flex-direction: column;
		gap: var(--spacing-lg);
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
	}

	.summary-content {
		display: flex;
		flex-direction: column;
		gap: var(--spacing-md);
		align-items: center;
	}

	.summary-label {
		font-size: var(--font-size-lg);
		font-weight: 600;
		color: var(--text-secondary);
		margin: 0;
	}

	.summary-amount {
		font-size: 3rem;
		font-weight: 700;
		color: var(--positive);
	}

	.summary-amount.negative {
		color: var(--negative);
	}

	/* Empty State */
	.empty-state {
		text-align: center;
		color: var(--text-secondary);
	}

	/* Container List */
	.container-list {
		display: flex;
		flex-direction: column;
		gap: var(--spacing-md);
	}

	.container-card {
		padding: var(--spacing-lg);
	}

	.container-header {
		display: flex;
		justify-content: space-between;
		align-items: flex-start;
		gap: var(--spacing-md);
	}

	.container-main {
		flex: 1;
		min-width: 0;
	}

	.container-name {
		font-size: var(--font-size-lg);
		font-weight: 600;
		color: var(--text-primary);
		margin: 0 0 var(--spacing-xs) 0;
	}

	.container-balance {
		font-size: var(--font-size-xl);
		font-weight: 700;
		color: var(--text-primary);
	}

	.container-balance.negative {
		color: var(--negative);
	}

	.container-actions {
		display: flex;
		gap: var(--spacing-xs);
	}

	.btn-icon {
		padding: var(--spacing-xs);
		background: transparent;
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		color: var(--text-secondary);
		cursor: pointer;
		transition: all 0.2s;
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.btn-icon:hover {
		background: var(--bg-page);
		color: var(--text-primary);
		border-color: var(--accent);
	}

	.btn-icon.btn-delete:hover {
		background: rgba(239, 68, 68, 0.1);
		color: var(--negative);
		border-color: var(--negative);
	}

	.container-locked {
		display: flex;
		align-items: center;
		gap: var(--spacing-xs);
		margin-top: var(--spacing-md);
		padding: var(--spacing-xs) var(--spacing-sm);
		background: var(--bg-page);
		border-radius: var(--radius-sm);
		color: var(--text-secondary);
		font-size: var(--font-size-sm);
		width: fit-content;
	}

	.container-bank {
		margin-top: var(--spacing-sm);
		padding-top: var(--spacing-sm);
		border-top: 1px solid var(--border);
		color: var(--text-secondary);
		font-size: var(--font-size-sm);
	}

	/* Delete Confirmation Modal */
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
	}

	.modal-body p {
		color: var(--text-secondary);
		margin: 0;
	}

	.modal-footer {
		display: flex;
		gap: var(--spacing-md);
		justify-content: flex-end;
		padding: var(--spacing-lg) var(--spacing-xl);
		border-top: 1px solid var(--border);
	}

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

	.btn-secondary {
		background: transparent;
		color: var(--accent);
		border: 1px solid var(--accent);
	}

	.btn-danger {
		background: var(--negative);
		color: white;
	}

	.btn-secondary:hover,
	.btn-danger:hover {
		opacity: 0.9;
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

		.btn-primary {
			justify-content: center;
		}

		.card {
			padding: var(--spacing-lg);
		}

		.summary-amount {
			font-size: 2rem;
		}

		.container-header {
			flex-direction: column;
		}

		.container-actions {
			align-self: flex-end;
		}

		.modal {
			max-width: 100%;
		}

		.modal-footer {
			flex-direction: column-reverse;
		}

		.btn-secondary,
		.btn-danger {
			width: 100%;
		}
	}
</style>
