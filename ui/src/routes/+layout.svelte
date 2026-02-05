<script lang="ts">
	import '../app.css';
	import { _, isLoading } from '$lib/i18n';
	import ToastContainer from '$lib/components/ToastContainer.svelte';
	import type { Snippet } from 'svelte';

	let { children }: { children: Snippet } = $props();
</script>

{#if $isLoading}
	<div class="loading">{$_('common.loading')}</div>
{:else}
	<div class="app-container">
		{@render children()}
	</div>
{/if}

<ToastContainer />

<style>
	.loading {
		display: flex;
		align-items: center;
		justify-content: center;
		min-height: 100vh;
		font-size: var(--font-size-lg);
		color: var(--text-secondary);
	}

	.app-container {
		min-height: 100vh;
		width: 100%;
	}
</style>
