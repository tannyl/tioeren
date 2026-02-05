/**
 * Toast notification system using Svelte 5 runes
 */

export type ToastType = 'success' | 'error' | 'warning' | 'info';

export interface Toast {
	id: string;
	message: string;
	type: ToastType;
	duration: number;
}

// Module-level state using runes
let toasts = $state<Toast[]>([]);

// Counter for unique IDs
let nextId = 0;

/**
 * Add a toast notification
 */
export function addToast(message: string, type: ToastType = 'info', duration = 5000): string {
	const id = `toast-${nextId++}`;
	const toast: Toast = { id, message, type, duration };

	toasts = [...toasts, toast];

	// Auto-dismiss after duration
	if (duration > 0) {
		setTimeout(() => {
			removeToast(id);
		}, duration);
	}

	return id;
}

/**
 * Remove a toast by ID
 */
export function removeToast(id: string): void {
	toasts = toasts.filter(t => t.id !== id);
}

/**
 * Get all toasts (reactive)
 */
export function getToasts(): Toast[] {
	return toasts;
}

/**
 * Clear all toasts
 */
export function clearToasts(): void {
	toasts = [];
}
