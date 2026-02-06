<script lang="ts">
	import type { Snippet } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import { onMount } from 'svelte';
	import { getBudget } from '$lib/api/budgets';
	import { _ } from '$lib/i18n';
	import { addToast } from '$lib/stores/toast.svelte';

	let { children }: { children: Snippet } = $props();

	let budgetId = $derived($page.params.id);
	let loading = $state(true);
	let budgetValid = $state(false);

	onMount(async () => {
		if (!budgetId) {
			addToast($_('budget.messages.noBudgetSelected'), 'warning');
			goto('/budgets');
			return;
		}

		try {
			await getBudget(budgetId);
			budgetValid = true;
		} catch {
			addToast($_('budget.messages.notFound'), 'error');
			goto('/budgets');
		} finally {
			loading = false;
		}
	});
</script>

{#if loading}
	<div class="loading-container">
		<p>Indlæser...</p>
	</div>
{:else if budgetValid}
	{@render children()}
{/if}

<style>
	.loading-container {
		display: flex;
		justify-content: center;
		align-items: center;
		min-height: 400px;
		padding: var(--spacing-xl);
	}

	.loading-container p {
		font-size: var(--font-size-lg);
		color: var(--text-secondary);
	}
</style>
