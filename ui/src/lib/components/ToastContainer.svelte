<script lang="ts">
	import { getToasts } from '$lib/stores/toast.svelte';
	import Toast from './Toast.svelte';

	let toasts = $derived(getToasts());
</script>

<div class="toast-container">
	{#each toasts as toast (toast.id)}
		<Toast {toast} />
	{/each}
</div>

<style>
	.toast-container {
		position: fixed;
		top: var(--spacing-lg);
		right: var(--spacing-lg);
		z-index: 9999;
		display: flex;
		flex-direction: column;
		gap: var(--spacing-sm);
		pointer-events: none;
	}

	.toast-container > :global(*) {
		pointer-events: auto;
	}

	@media (max-width: 768px) {
		.toast-container {
			top: var(--spacing-md);
			right: var(--spacing-md);
			left: var(--spacing-md);
		}
	}
</style>
