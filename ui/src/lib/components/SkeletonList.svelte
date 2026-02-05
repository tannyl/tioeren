<script lang="ts">
	let {
		items = 3,
		height = '80px'
	}: {
		items?: number;
		height?: string;
	} = $props();
</script>

<div class="skeleton-list">
	{#each Array(items) as _, i (i)}
		<div class="skeleton-item" style="height: {height}">
			<div class="skeleton-content">
				<div class="skeleton-main">
					<div class="skeleton-line" style="width: 60%"></div>
					<div class="skeleton-line small" style="width: 40%"></div>
				</div>
				<div class="skeleton-side">
					<div class="skeleton-line" style="width: 80px"></div>
				</div>
			</div>
		</div>
	{/each}
</div>

<style>
	.skeleton-list {
		display: flex;
		flex-direction: column;
		gap: var(--spacing-sm);
	}

	.skeleton-item {
		background: var(--bg-card);
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		padding: var(--spacing-md);
		display: flex;
		align-items: center;
	}

	.skeleton-content {
		display: flex;
		justify-content: space-between;
		align-items: center;
		width: 100%;
		gap: var(--spacing-md);
	}

	.skeleton-main {
		flex: 1;
		display: flex;
		flex-direction: column;
		gap: var(--spacing-xs);
	}

	.skeleton-side {
		flex-shrink: 0;
	}

	.skeleton-line {
		height: 1rem;
		background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%);
		background-size: 400px 100%;
		animation: shimmer 1.5s ease-in-out infinite;
		border-radius: var(--radius-sm);
	}

	.skeleton-line.small {
		height: 0.75rem;
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
