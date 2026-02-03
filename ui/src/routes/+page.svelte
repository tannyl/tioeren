<script lang="ts">
	import { _ } from '$lib/i18n';
</script>

<div class="home">
	<h1>{$_('app.name')}</h1>
	<p>{$_('app.tagline')}</p>
</div>

<style>
	.home {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		min-height: 100vh;
		padding: var(--spacing-xl);
		text-align: center;
	}

	h1 {
		font-size: var(--font-size-3xl);
		font-weight: 700;
		margin-bottom: var(--spacing-md);
		color: var(--text-primary);
	}

	p {
		font-size: var(--font-size-lg);
		color: var(--text-secondary);
	}
</style>
