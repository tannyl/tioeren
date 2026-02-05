<script lang="ts">
	let {
		height = '200px',
		variant = 'default'
	}: {
		height?: string;
		variant?: 'default' | 'compact';
	} = $props();
</script>

<div class="skeleton-card" class:compact={variant === 'compact'} style="height: {height}">
	<div class="skeleton-header">
		<div class="skeleton-line" style="width: 40%"></div>
	</div>
	<div class="skeleton-body">
		<div class="skeleton-line" style="width: 60%"></div>
		<div class="skeleton-line" style="width: 80%"></div>
		{#if variant === 'default'}
			<div class="skeleton-line" style="width: 50%"></div>
		{/if}
	</div>
</div>

<style>
	.skeleton-card {
		background: var(--bg-card);
		border: 1px solid var(--border);
		border-radius: var(--radius-lg);
		padding: var(--spacing-xl);
		display: flex;
		flex-direction: column;
		gap: var(--spacing-lg);
	}

	.skeleton-card.compact {
		padding: var(--spacing-lg);
		gap: var(--spacing-md);
	}

	.skeleton-header {
		display: flex;
		align-items: center;
	}

	.skeleton-body {
		display: flex;
		flex-direction: column;
		gap: var(--spacing-sm);
		flex: 1;
	}

	.skeleton-line {
		height: 1rem;
		background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
		background-size: 400px 100%;
		animation: shimmer 1.5s ease-in-out infinite;
		border-radius: var(--radius-sm);
	}

	@keyframes shimmer {
		0% {
			background-position: -200px 0;
		}
		100% {
			background-position: 200px 0;
		}
	}
</style>
