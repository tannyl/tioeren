<script lang="ts">
	import { removeToast } from '$lib/stores/toast.svelte';
	import type { Toast } from '$lib/stores/toast.svelte';

	let { toast }: { toast: Toast } = $props();

	function getIcon(type: Toast['type']): string {
		switch (type) {
			case 'success':
				return 'M20 6 9 17l-5-5'; // Check icon
			case 'error':
				return 'M18 6 6 18 M6 6l12 12'; // X icon
			case 'warning':
				return 'M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z M12 9v4 M12 17h.01'; // Alert triangle
			case 'info':
				return 'M12 16v-4 M12 8h.01'; // Info icon
			default:
				return '';
		}
	}

	function handleClose() {
		removeToast(toast.id);
	}
</script>

<div class="toast" data-type={toast.type} role="alert">
	<div class="toast-icon">
		<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
			<path d={getIcon(toast.type)} />
		</svg>
	</div>
	<div class="toast-message">{toast.message}</div>
	<button class="toast-close" onclick={handleClose} aria-label="Close">
		<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
			<line x1="18" y1="6" x2="6" y2="18" />
			<line x1="6" y1="6" x2="18" y2="18" />
		</svg>
	</button>
</div>

<style>
	.toast {
		display: flex;
		align-items: center;
		gap: var(--spacing-sm);
		padding: var(--spacing-sm) var(--spacing-md);
		background: var(--bg-card);
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
		min-width: 300px;
		max-width: 400px;
		animation: slideIn 0.3s ease-out;
	}

	@keyframes slideIn {
		from {
			transform: translateX(100%);
			opacity: 0;
		}
		to {
			transform: translateX(0);
			opacity: 1;
		}
	}

	.toast[data-type='success'] {
		border-left: 3px solid var(--positive);
	}

	.toast[data-type='success'] .toast-icon {
		color: var(--positive);
	}

	.toast[data-type='error'] {
		border-left: 3px solid var(--negative);
	}

	.toast[data-type='error'] .toast-icon {
		color: var(--negative);
	}

	.toast[data-type='warning'] {
		border-left: 3px solid var(--warning);
	}

	.toast[data-type='warning'] .toast-icon {
		color: var(--warning);
	}

	.toast[data-type='info'] {
		border-left: 3px solid var(--accent);
	}

	.toast[data-type='info'] .toast-icon {
		color: var(--accent);
	}

	.toast-icon {
		flex-shrink: 0;
		display: flex;
		align-items: center;
	}

	.toast-message {
		flex: 1;
		color: var(--text-primary);
		font-size: var(--font-size-sm);
	}

	.toast-close {
		flex-shrink: 0;
		background: none;
		border: none;
		padding: var(--spacing-xs);
		cursor: pointer;
		color: var(--text-secondary);
		display: flex;
		align-items: center;
		border-radius: var(--radius-sm);
		transition: background 0.2s;
	}

	.toast-close:hover {
		background: var(--bg-page);
	}

	.toast-close:focus-visible {
		outline: 2px solid var(--accent);
		outline-offset: 2px;
	}

	@media (max-width: 768px) {
		.toast {
			min-width: auto;
			max-width: calc(100vw - 2rem);
		}
	}
</style>
