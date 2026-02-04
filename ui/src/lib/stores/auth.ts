/**
 * Authentication state store
 */

import { writable } from 'svelte/store';
import { getCurrentUser, logout as apiLogout } from '$lib/api/auth';

export interface User {
	id: string;
	email: string;
}

interface AuthState {
	user: User | null;
	loading: boolean;
	initialized: boolean;
}

function createAuthStore() {
	const { subscribe, set, update } = writable<AuthState>({
		user: null,
		loading: true,
		initialized: false
	});

	return {
		subscribe,

		async initialize() {
			update((state) => ({ ...state, loading: true }));
			try {
				const user = await getCurrentUser();
				set({ user, loading: false, initialized: true });
			} catch {
				set({ user: null, loading: false, initialized: true });
			}
		},

		setUser(user: User) {
			update((state) => ({ ...state, user, loading: false }));
		},

		async logout() {
			await apiLogout();
			set({ user: null, loading: false, initialized: true });
		},

		clear() {
			set({ user: null, loading: false, initialized: true });
		}
	};
}

export const auth = createAuthStore();
