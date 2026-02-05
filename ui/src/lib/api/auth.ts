/**
 * Authentication API client
 */

import { extractErrorMessage } from './errors';

export interface AuthResponse {
	id: string;
	email: string;
	message?: string;
}

export async function register(email: string, password: string): Promise<AuthResponse> {
	const response = await fetch('/api/auth/register', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ email, password }),
		credentials: 'include'
	});

	if (!response.ok) {
		const errorMessage = await extractErrorMessage(response);
		throw new Error(errorMessage);
	}

	return response.json();
}

export async function login(email: string, password: string): Promise<AuthResponse> {
	const response = await fetch('/api/auth/login', {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ email, password }),
		credentials: 'include'
	});

	if (!response.ok) {
		const errorMessage = await extractErrorMessage(response);
		throw new Error(errorMessage);
	}

	return response.json();
}

export async function logout(): Promise<void> {
	await fetch('/api/auth/logout', {
		method: 'POST',
		credentials: 'include'
	});
}

export async function getCurrentUser(): Promise<AuthResponse | null> {
	const response = await fetch('/api/auth/me', {
		credentials: 'include'
	});

	if (!response.ok) {
		return null;
	}

	return response.json();
}
