import { redirect } from '@sveltejs/kit';
import type { PageLoad } from './$types';

export const load: PageLoad = async ({ fetch }) => {
	const res = await fetch('/api/auth/me', { credentials: 'include' });
	if (res.ok) {
		redirect(303, '/budgets');
	}
	redirect(303, '/login');
};
