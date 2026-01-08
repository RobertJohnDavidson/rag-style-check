// API client with fetch wrappers for all endpoints
import type { Test, TestResult, TuningParameters, PaginatedResponse, GenerateTestsRequest, GenerateTestsResponse, Violation, ModelInfo, ModelListResponse } from './types';
import { TestInputSchema, TuningParametersSchema } from './schemas';

// Generic API response wrapper
interface ApiResponse<T> {
	data?: T;
	error?: string;
}

// Get the API base URL from the current origin
export function getApiBase(baseUrl?: string | URL): string {
	if (baseUrl) {
		return baseUrl instanceof URL ? baseUrl.origin : new URL(baseUrl).origin;
	}
	// In browser context, use current origin
	if (typeof window !== 'undefined') {
		return window.location.origin;
	}
	// Fallback for SSR or server context
	return 'http://localhost:8000';
}

// Create a new test
export async function createTest(input: {
	label: string;
	text: string;
	expected_violations: Array<{ rule: string; text: string; reason?: string; link: string }>;
	generation_method: 'manual' | 'article' | 'synthetic';
	notes?: string;
}): Promise<ApiResponse<Test>> {
	try {
		// Validate input
		const validated = TestInputSchema.parse(input);

		const response = await fetch(`${getApiBase()}/api/tests`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(validated)
		});

		if (!response.ok) {
			const error = await response.json().catch(() => ({ detail: 'Failed to create test' }));
			throw new Error(error.detail || 'Failed to create test');
		}

		const data = await response.json();
		return { data };
	} catch (err) {
		return { error: err instanceof Error ? err.message : 'Unknown error occurred' };
	}
}

// Perform a standard audit
export async function auditText(
	text: string,
	testId?: string,
	tuningParameters?: TuningParameters
): Promise<ApiResponse<{ violations: Violation[], metadata: any }>> {
	try {
		const response = await fetch(`${getApiBase()}/audit`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({
				text,
				test_id: testId,
				tuning_parameters: tuningParameters
			})
		});

		if (!response.ok) {
			const error = await response.json().catch(() => ({ detail: 'Audit failed' }));
			throw new Error(error.detail || 'Audit failed');
		}

		const data = await response.json();
		return { data };
	} catch (err) {
		return { error: err instanceof Error ? err.message : 'Failed to connect to API' };
	}
}

// Load tests with pagination and filtering
export async function loadTests(params: {
	page?: number;
	page_size?: number;
	search?: string;
	generation_method?: string;
} = {}): Promise<ApiResponse<PaginatedResponse<Test>>> {
	try {
		const searchParams = new URLSearchParams({
			page: (params.page || 1).toString(),
			page_size: (params.page_size || 20).toString()
		});

		if (params.search) searchParams.append('search', params.search);
		if (params.generation_method) searchParams.append('generation_method', params.generation_method);

		const response = await fetch(`${getApiBase()}/api/tests?${searchParams}`);

		if (!response.ok) {
			throw new Error('Failed to load tests');
		}

		const data = await response.json();
		return { data };
	} catch (err) {
		return { error: err instanceof Error ? err.message : 'Failed to load tests' };
	}
}

// Get a single test by ID
export async function getTest(id: string): Promise<ApiResponse<Test>> {
	try {
		const response = await fetch(`${getApiBase()}/api/tests/${id}`);

		if (!response.ok) {
			throw new Error('Failed to load test');
		}

		const data = await response.json();
		return { data };
	} catch (err) {
		return { error: err instanceof Error ? err.message : 'Failed to load test' };
	}
}

// Delete a test
export async function deleteTest(id: string): Promise<ApiResponse<void>> {
	try {
		const response = await fetch(`${getApiBase()}/api/tests/${id}`, {
			method: 'DELETE'
		});

		if (!response.ok) {
			throw new Error('Failed to delete test');
		}

		return { data: undefined };
	} catch (err) {
		return { error: err instanceof Error ? err.message : 'Failed to delete test' };
	}
}

// Run a test with tuning parameters
export async function runTest(testId: string, tuningParameters?: TuningParameters, profileId?: string): Promise<ApiResponse<TestResult>> {
	try {
		// Validate tuning parameters
		const validated = tuningParameters ? TuningParametersSchema.parse(tuningParameters) : undefined;

		const url = new URL(`${getApiBase()}/api/tests/${testId}/run`);
		if (profileId) url.searchParams.append('profile_id', profileId);

		const response = await fetch(url.toString(), {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(validated || {})
		});

		if (!response.ok) {
			const error = await response.json().catch(() => ({ detail: 'Failed to run test' }));
			throw new Error(error.detail || 'Failed to run test');
		}

		const data = await response.json();
		return { data };
	} catch (err) {
		return { error: err instanceof Error ? err.message : 'Failed to run test' };
	}
}

// Get default tuning parameters
export async function getTuningDefaults(): Promise<ApiResponse<TuningParameters>> {
	try {
		const response = await fetch(`${getApiBase()}/api/tuning-defaults`);

		if (!response.ok) {
			throw new Error('Failed to load tuning defaults');
		}

		const data = await response.json();
		return { data };
	} catch (err) {
		return { error: err instanceof Error ? err.message : 'Failed to load tuning defaults' };
	}
}

// Get available models
export async function getModels(): Promise<ApiResponse<ModelInfo[]>> {
	try {
		const response = await fetch(`${getApiBase()}/api/models`);

		if (!response.ok) {
			throw new Error('Failed to load models');
		}

		const data: ModelListResponse = await response.json();
		return { data: data.models };
	} catch (err) {
		return { error: err instanceof Error ? err.message : 'Failed to load models' };
	}
}

// Generate high-quality news text
export async function generateText(): Promise<ApiResponse<{ text: string }>> {
	try {
		const response = await fetch(`${getApiBase()}/api/generate-text`);

		if (!response.ok) {
			const error = await response.json().catch(() => ({ detail: 'Failed to generate text' }));
			throw new Error(error.detail || 'Failed to generate text');
		}

		const data = await response.json();
		return { data };
	} catch (err) {
		return { error: err instanceof Error ? err.message : 'Failed to generate text' };
	}
}
