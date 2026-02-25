import { redirect } from '@sveltejs/kit';
import type { LayoutLoad } from './$types';

export const prerender = false;

export const load: LayoutLoad = async ({ fetch }) => {
	try {
		const response = await fetch('/api/auth/me', {
			credentials: 'include'
		});

		if (!response.ok) {
			throw redirect(303, '/login');
		}

		const user = await response.json();
		return { user };
	} catch (error) {
		if (error instanceof Response && error.status === 303) {
			throw error; // Re-throw redirect
		}
		throw redirect(303, '/login');
	}
};
