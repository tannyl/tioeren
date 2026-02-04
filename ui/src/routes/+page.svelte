<script lang="ts">
	import { onMount } from 'svelte';
	import { _ } from '$lib/i18n';
	import { auth } from '$lib/stores/auth';

	onMount(() => {
		auth.initialize();
	});

	async function handleLogout() {
		await auth.logout();
	}
</script>

<div class="home">
	<h1>{$_('app.name')}</h1>
	<p>{$_('app.tagline')}</p>

	{#if $auth.loading}
		<p class="loading">{$_('common.loading')}</p>
	{:else if $auth.user}
		<div class="user-info">
			<p>{$_('auth.welcome', { values: { email: $auth.user.email } })}</p>
			<button onclick={handleLogout} class="btn-secondary">
				{$_('auth.logout')}
			</button>
		</div>
	{:else}
		<div class="auth-links">
			<a href="/login" class="btn-primary">{$_('auth.login')}</a>
			<a href="/register" class="btn-secondary">{$_('auth.register')}</a>
		</div>
	{/if}
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

	.loading {
		margin-top: var(--spacing-lg);
		color: var(--text-secondary);
	}

	.user-info {
		margin-top: var(--spacing-lg);
		display: flex;
		flex-direction: column;
		gap: var(--spacing-md);
		align-items: center;
	}

	.auth-links {
		margin-top: var(--spacing-lg);
		display: flex;
		gap: var(--spacing-md);
	}

	.btn-primary,
	.btn-secondary {
		padding: var(--spacing-sm) var(--spacing-lg);
		border-radius: var(--radius-md);
		font-size: var(--font-size-base);
		text-decoration: none;
		cursor: pointer;
		border: none;
		transition: opacity 0.2s;
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

	.btn-primary:hover,
	.btn-secondary:hover {
		opacity: 0.9;
	}
</style>
