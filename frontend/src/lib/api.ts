// API client with fetch wrappers for all endpoints
import type { Test, TestResult, TuningParameters, PaginatedResponse, GenerateTestsRequest, GenerateTestsResponse } from './types';
import { TestInputSchema, TuningParametersSchema } from './schemas';

const API_BASE = 'http://localhost:8000';

// Generic API response wrapper
interface ApiResponse<T> {
	data?: T;
	error?: string;
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

		const response = await fetch(`${API_BASE}/api/tests`, {
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

		const response = await fetch(`${API_BASE}/api/tests?${searchParams}`);

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
		const response = await fetch(`${API_BASE}/api/tests/${id}`);

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
		const response = await fetch(`${API_BASE}/api/tests/${id}`, {
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
export async function runTest(testId: string, tuning: TuningParameters): Promise<ApiResponse<TestResult>> {
	try {
		// Validate tuning parameters
		const validated = TuningParametersSchema.parse(tuning);

		const response = await fetch(`${API_BASE}/api/tests/${testId}/run`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(validated)
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

// Generate tests from article or synthetically
export async function generateTests(request: GenerateTestsRequest): Promise<ApiResponse<GenerateTestsResponse>> {
	try {
		const response = await fetch(`${API_BASE}/api/generate-tests`, {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(request)
		});

		if (!response.ok) {
			const error = await response.json().catch(() => ({ detail: 'Failed to generate tests' }));
			throw new Error(error.detail || 'Failed to generate tests');
		}

		const data = await response.json();
		return { data };
	} catch (err) {
		return { error: err instanceof Error ? err.message : 'Failed to generate tests' };
	}
}

// Get available models
export async function getModels(): Promise<ApiResponse<string[]>> {
	try {
		const response = await fetch(`${API_BASE}/api/models`);

		if (!response.ok) {
			throw new Error('Failed to load models');
		}

		const data = await response.json();
		return { data };
	} catch (err) {
		return { error: err instanceof Error ? err.message : 'Failed to load models' };
	}
}

// Get default tuning parameters
export async function getTuningDefaults(): Promise<ApiResponse<TuningParameters>> {
	try {
		const response = await fetch(`${API_BASE}/api/tuning-defaults`);

		if (!response.ok) {
			throw new Error('Failed to load tuning defaults');
		}

		const data = await response.json();
		return { data };
	} catch (err) {
		return { error: err instanceof Error ? err.message : 'Failed to load tuning defaults' };
	}
}
