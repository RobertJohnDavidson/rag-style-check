// TypeScript type definitions for the test management system

export type GenerationMethod = 'manual' | 'article' | 'synthetic';

export interface ExpectedViolation {
	rule: string;
	text: string;
	reason?: string;
	link: string;
}

export interface Test {
	id: string;
	label: string;
	text: string;
	expected_violations: ExpectedViolation[];
	generation_method: GenerationMethod;
	notes?: string;
	created_at: string;
	updated_at?: string;
}

export interface TuningParameters {
	model_name: string;
	temperature: number;
	initial_retrieval_count: number;
	final_top_k: number;
	rerank_score_threshold: number;
	aggregated_rule_limit: number;
	max_agent_iterations: number;
	confidence_threshold: number;
	include_thinking: boolean;
}

export interface ModelInfo {
	name: string;
	display_name: string;
	supports_thinking: boolean;
}

export interface ModelListResponse {
	models: ModelInfo[];
}

export interface TestMetrics {
	true_positives: number;
	false_positives: number;
	false_negatives: number;
	true_negatives: number;
	precision: number | null;
	recall: number | null;
	f1_score: number | null;
}

export interface Violation {
	rule: string;
	text: string;
	reason: string;
	url?: string;
}

export interface TestResult {
	id: string;
	test_id: string;
	metrics: TestMetrics;
	detected_violations: Violation[];
	tuning_parameters: TuningParameters;
	execution_time_seconds: number;
	executed_at: string;
}

export interface PaginatedResponse<T> {
	tests: T[];
	total: number;
	page: number;
	page_size: number;
}

export interface GenerateTestsRequest {
	article_url?: string;
	count?: number;
	method?: 'synthetic';
}

export interface GenerateTestsResponse {
	tests: Array<{
		label: string;
		text: string;
		expected_violations: ExpectedViolation[];
	}>;
}
