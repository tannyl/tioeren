import { redirect } from '@sveltejs/kit';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch }) => {
	const response = await fetch('/api/auth/me', {
		credentials: 'include'
	});

	if (response.ok) {
		// User is authenticated, redirect to budgets
		redirect(303, '/budgets');
	}

	// User is not authenticated, stay on landing page
	return {};
};
