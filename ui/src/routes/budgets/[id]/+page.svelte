<script lang="ts">
	import { page } from '$app/stores';
	import { _ } from '$lib/i18n';

	let budgetId = $derived($page.params.id);
</script>

<div class="page">
	<div class="placeholder">
		<h1>{$_('dashboard.title')}</h1>
		<p>{$_('dashboard.placeholder.budgetId')}: {budgetId}</p>
		<p>{$_('dashboard.placeholder.futureImplementation')}</p>
		<a href="/budgets/{budgetId}/settings" class="link">{$_('dashboard.placeholder.goToSettings')}</a>
	</div>
</div>

<style>
	.page {
		max-width: 1200px;
		margin: 0 auto;
		padding: var(--spacing-xl);
	}

	.placeholder {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		min-height: 60vh;
		text-align: center;
		gap: var(--spacing-md);
	}

	h1 {
		font-size: var(--font-size-3xl);
		font-weight: 700;
		color: var(--text-primary);
	}

	p {
		color: var(--text-secondary);
	}

	.link {
		color: var(--accent);
		text-decoration: none;
		margin-top: var(--spacing-md);
	}

	.link:hover {
		text-decoration: underline;
	}
</style>
