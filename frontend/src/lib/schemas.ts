// Zod validation schemas for the test management system
import { z } from 'zod';

// Validation schema for expected violations
export const ExpectedViolationSchema = z.object({
	rule: z.string().min(1, 'Rule name is required'),
	text: z.string().min(1, 'Violating text is required'),
	reason: z.string().optional(),
	link: z.string().url('Must be a valid URL')
});

// Validation schema for test input
export const TestInputSchema = z.object({
	label: z.string().min(1, 'Test label is required'),
	text: z.string().min(1, 'Test text is required'),
	expected_violations: z.array(ExpectedViolationSchema),
	generation_method: z.enum(['manual', 'article', 'synthetic']),
	notes: z.string().optional()
});

// Validation schema for tuning parameters
export const TuningParametersSchema = z.object({
	model_name: z.string().min(1, 'Model name is required'),
	temperature: z.number().min(0).max(2),
	initial_retrieval_count: z.number().int().min(10).max(200),
	final_top_k: z.number().int().min(5).max(100),
	rerank_score_threshold: z.number().min(0).max(1),
	aggregated_rule_limit: z.number().int().min(10).max(100),
	min_sentence_length: z.number().int().min(1).max(50),
	max_agent_iterations: z.number().int().min(1).max(10),
	confidence_threshold: z.number().min(0),
	include_thinking: z.boolean().default(false)
});

// Validation schema for CBC article URLs
export const CBCArticleUrlSchema = z
	.string()
	.url('Must be a valid URL')
	.regex(/^https?:\/\/(www\.)?cbc\.ca\/.+/, 'Must be a CBC article URL (https://www.cbc.ca/...)');

// Validation schema for synthetic test count
export const SyntheticCountSchema = z.number().int().min(1).max(20);

// Type exports inferred from schemas
export type ExpectedViolationInput = z.infer<typeof ExpectedViolationSchema>;
export type TestInput = z.infer<typeof TestInputSchema>;
export type TuningParametersInput = z.infer<typeof TuningParametersSchema>;
export type CBCArticleUrl = z.infer<typeof CBCArticleUrlSchema>;
export type SyntheticCount = z.infer<typeof SyntheticCountSchema>;
