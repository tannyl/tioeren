/**
 * API error handling utilities
 */

export interface ApiError {
	detail: string;
	status?: number;
}

/**
 * Extract user-friendly error message from API response
 */
export async function extractErrorMessage(response: Response): Promise<string> {
	// Check Content-Type before attempting to parse as JSON
	const contentType = response.headers.get('Content-Type');

	if (contentType && contentType.includes('application/json')) {
		try {
			const data = await response.json();
			// Handle Pydantic 422 validation errors (array format)
			if (Array.isArray(data.detail)) {
				const messages = data.detail.map((err: any) => err.msg || String(err));
				return messages.join('; ') || getErrorMessageForStatus(response.status);
			}
			return data.detail || data.message || getErrorMessageForStatus(response.status);
		} catch {
			// JSON parsing failed even though Content-Type said it was JSON
			return getErrorMessageForStatus(response.status);
		}
	}

	// Non-JSON response (plain text, HTML, etc.)
	// For 500 errors, use specific translation key for unexpected errors
	if (response.status === 500) {
		return 'error.unexpectedServerError';
	}

	// For other status codes, use generic message
	return getErrorMessageForStatus(response.status);
}

/**
 * Map HTTP status codes to translation keys
 */
export function getErrorMessageForStatus(status: number): string {
	switch (status) {
		case 400:
			return 'error.badRequest';
		case 401:
			return 'error.unauthorized';
		case 403:
			return 'error.forbidden';
		case 404:
			return 'error.notFound';
		case 409:
			return 'error.conflict';
		case 422:
			return 'error.validationError';
		case 429:
			return 'error.tooManyRequests';
		case 500:
			return 'error.serverError';
		case 503:
			return 'error.serviceUnavailable';
		default:
			return 'error.generic';
	}
}

/**
 * Handle network errors (no response from server)
 */
export function handleNetworkError(error: Error): string {
	if (error.name === 'AbortError') {
		return 'error.requestCancelled';
	}
	if (error.message.includes('fetch') || error.message.includes('network')) {
		return 'error.networkError';
	}
	return 'error.generic';
}

/**
 * Generic API error handler
 * Returns a user-friendly error message
 */
export async function handleApiError(error: unknown): Promise<string> {
	// Network error (no response)
	if (error instanceof TypeError) {
		return handleNetworkError(error);
	}

	// HTTP error response
	if (error instanceof Response) {
		return await extractErrorMessage(error);
	}

	// Error object with message
	if (error instanceof Error) {
		return error.message;
	}

	// Unknown error type
	return 'error.generic';
}

/**
 * Wrapper for fetch with error handling
 */
export async function apiFetch<T>(
	url: string,
	options?: RequestInit
): Promise<T> {
	try {
		const response = await fetch(url, {
			...options,
			credentials: options?.credentials || 'include',
			headers: {
				'Content-Type': 'application/json',
				...options?.headers
			}
		});

		if (!response.ok) {
			const errorMessage = await extractErrorMessage(response);
			throw new Error(errorMessage);
		}

		return await response.json();
	} catch (error) {
		// Re-throw with handled message
		const message = await handleApiError(error);
		throw new Error(message);
	}
}
