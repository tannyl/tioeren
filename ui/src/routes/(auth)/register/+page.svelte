<script lang="ts">
	import { goto } from '$app/navigation';
	import { get } from 'svelte/store';
	import { _ } from '$lib/i18n';
	import { register } from '$lib/api/auth';
	import { auth } from '$lib/stores/auth';
	import { addToast } from '$lib/stores/toast.svelte';

	let email = $state('');
	let password = $state('');
	let passwordConfirm = $state('');
	let error = $state('');
	let loading = $state(false);

	async function handleSubmit(e: Event) {
		e.preventDefault();
		error = '';

		// Validate password confirmation
		if (password !== passwordConfirm) {
			error = get(_)('auth.passwordMismatch');
			addToast(error, 'error');
			return;
		}

		// Validate password length
		if (password.length < 12) {
			error = get(_)('auth.passwordHint');
			addToast(error, 'error');
			return;
		}

		loading = true;

		try {
			const user = await register(email, password);
			auth.setUser({ id: user.id, email: user.email });
			addToast(get(_)('auth.registrationSuccess'), 'success');
			goto('/budgets');
		} catch (err) {
			error = err instanceof Error ? get(_)(err.message) : get(_)('auth.registrationFailed');
			addToast(error, 'error');
		} finally {
			loading = false;
		}
	}
</script>

<main class="auth-page">
	<div class="auth-card">
		<h1>{$_('auth.register')}</h1>

		<form onsubmit={handleSubmit}>
			{#if error}
				<div class="error-message">{error}</div>
			{/if}

			<div class="form-group">
				<label for="email">{$_('auth.email')}</label>
				<input
					type="email"
					id="email"
					bind:value={email}
					required
					autocomplete="email"
				/>
			</div>

			<div class="form-group">
				<label for="password">{$_('auth.password')}</label>
				<input
					type="password"
					id="password"
					bind:value={password}
					required
					autocomplete="new-password"
					minlength="12"
				/>
				<p class="hint">{$_('auth.passwordHint')}</p>
			</div>

			<div class="form-group">
				<label for="password-confirm">{$_('auth.passwordConfirm')}</label>
				<input
					type="password"
					id="password-confirm"
					bind:value={passwordConfirm}
					required
					autocomplete="new-password"
					minlength="12"
				/>
			</div>

			<button type="submit" class="btn-primary" disabled={loading}>
				{loading ? $_('common.loading') : $_('auth.register')}
			</button>
		</form>

		<p class="auth-link">
			{$_('auth.hasAccount')} <a href="/login">{$_('auth.login')}</a>
		</p>
	</div>
</main>

<style>
	.auth-page {
		display: flex;
		justify-content: center;
		align-items: center;
		min-height: 100vh;
		padding: var(--spacing-md);
	}

	.auth-card {
		background: var(--bg-card);
		border-radius: var(--radius-lg);
		padding: var(--spacing-xl);
		width: 100%;
		max-width: 400px;
		box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
	}

	h1 {
		text-align: center;
		margin-bottom: var(--spacing-lg);
		color: var(--text-primary);
	}

	.form-group {
		margin-bottom: var(--spacing-md);
	}

	label {
		display: block;
		margin-bottom: var(--spacing-xs);
		color: var(--text-secondary);
		font-size: var(--font-size-sm);
	}

	input {
		width: 100%;
		padding: var(--spacing-sm) var(--spacing-md);
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		font-size: var(--font-size-base);
		background: var(--bg-page);
		color: var(--text-primary);
	}

	input:focus {
		outline: none;
		border-color: var(--accent);
	}

	.hint {
		margin-top: var(--spacing-xs);
		color: var(--text-secondary);
		font-size: var(--font-size-xs);
	}

	.btn-primary {
		width: 100%;
		padding: var(--spacing-sm) var(--spacing-md);
		background: var(--accent);
		color: white;
		border: none;
		border-radius: var(--radius-md);
		font-size: var(--font-size-base);
		cursor: pointer;
		margin-top: var(--spacing-md);
	}

	.btn-primary:hover:not(:disabled) {
		opacity: 0.9;
	}

	.btn-primary:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}

	.error-message {
		background: color-mix(in srgb, var(--negative) 10%, transparent);
		color: var(--negative);
		padding: var(--spacing-sm) var(--spacing-md);
		border-radius: var(--radius-md);
		margin-bottom: var(--spacing-md);
		font-size: var(--font-size-sm);
	}

	.auth-link {
		text-align: center;
		margin-top: var(--spacing-lg);
		color: var(--text-secondary);
		font-size: var(--font-size-sm);
	}

	.auth-link a {
		color: var(--accent);
		text-decoration: none;
	}

	.auth-link a:hover {
		text-decoration: underline;
	}
</style>
