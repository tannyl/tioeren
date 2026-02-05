import { redirect } from '@sveltejs/kit';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch }) => {
	try {
		const response = await fetch('/api/auth/me', {
			credentials: 'include'
		});

		if (response.ok) {
			// User is authenticated, redirect to budgets
			throw redirect(303, '/budgets');
		}
	} catch (error) {
		if (error instanceof Response && error.status === 303) {
			throw error; // Re-throw redirect
		}
	}

	// User is not authenticated, stay on landing page
	return {};
};
