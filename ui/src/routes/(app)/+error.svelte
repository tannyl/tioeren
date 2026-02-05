<script lang="ts">
	import { page } from '$app/stores';
	import { _ } from '$lib/i18n';

	let status = $derived($page.status);
	let message = $derived($page.error?.message || '');

	function getErrorTitle(status: number): string {
		switch (status) {
			case 404:
				return $_('error.notFound');
			case 401:
				return $_('error.unauthorized');
			case 500:
				return $_('error.serverError');
			default:
				return $_('error.generic');
		}
	}
</script>

<div class="error-container">
	<div class="error-card">
		<div class="error-icon">
			<svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
				<circle cx="12" cy="12" r="10" />
				<line x1="12" y1="8" x2="12" y2="12" />
				<line x1="12" y1="16" x2="12.01" y2="16" />
			</svg>
		</div>

		<h1>{status}</h1>
		<h2>{getErrorTitle(status)}</h2>

		{#if message}
			<p class="error-message">{message}</p>
		{/if}

		<div class="error-actions">
			<button class="btn-secondary" onclick={() => window.history.back()}>
				{$_('error.goBack')}
			</button>
			<a href="/budgets" class="btn-primary">
				{$_('error.goHome')}
			</a>
		</div>
	</div>
</div>

<style>
	.error-container {
		display: flex;
		align-items: center;
		justify-content: center;
		min-height: 60vh;
		padding: var(--spacing-xl);
	}

	.error-card {
		text-align: center;
		max-width: 500px;
		background: var(--bg-card);
		border: 1px solid var(--border);
		border-radius: var(--radius-lg);
		padding: var(--spacing-xl);
	}

	.error-icon {
		display: flex;
		justify-content: center;
		margin-bottom: var(--spacing-lg);
		color: var(--negative);
	}

	h1 {
		font-size: 3rem;
		font-weight: 700;
		color: var(--text-primary);
		margin-bottom: var(--spacing-sm);
	}

	h2 {
		font-size: var(--font-size-xl);
		font-weight: 600;
		color: var(--text-primary);
		margin-bottom: var(--spacing-md);
	}

	.error-message {
		color: var(--text-secondary);
		margin-bottom: var(--spacing-xl);
		font-size: var(--font-size-base);
	}

	.error-actions {
		display: flex;
		gap: var(--spacing-md);
		justify-content: center;
		flex-wrap: wrap;
	}

	.btn-primary,
	.btn-secondary {
		padding: var(--spacing-sm) var(--spacing-lg);
		border-radius: var(--radius-md);
		font-size: var(--font-size-base);
		font-weight: 500;
		cursor: pointer;
		transition: opacity 0.2s;
		text-decoration: none;
		display: inline-block;
	}

	.btn-primary {
		background: var(--accent);
		color: white;
		border: none;
	}

	.btn-secondary {
		background: transparent;
		color: var(--accent);
		border: 1px solid var(--accent);
	}

	.btn-primary:hover,
	.btn-secondary:hover {
		opacity: 0.9;
	}

	@media (max-width: 768px) {
		h1 {
			font-size: 2rem;
		}

		.error-actions {
			flex-direction: column;
			width: 100%;
		}

		.btn-primary,
		.btn-secondary {
			width: 100%;
		}
	}
</style>
