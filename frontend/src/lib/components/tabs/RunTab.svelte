<script lang="ts">
	import type { Test, TestResult } from '$lib/types';
	import { Card, Button, Alert } from '$lib/components/ui';
	import { TuningParameters, MetricsDisplay } from '$lib/components/tests';
	import { getTest as apiGetTest, runTest as apiRunTest } from '$lib/api';
	import { LoaderCircle, Play } from '@lucide/svelte';

	interface Props {
		testId?: string;
	}

	let { testId }: Props = $props();

	// Local state
	let selectedTest = $state<Test | null>(null);
	let selectedTestId = $state<string | null>(null);
	let loading = $state(false);
	let error = $state('');
	let result = $state<TestResult | null>(null);
	
	// Tuning parameters object
	let tuningParams = $state({
		model_name: 'gemini-2.0-flash-exp',
		temperature: 0.7,
		initial_retrieval_count: 20,
		final_top_k: 10,
		rerank_score_threshold: 0.3,
		aggregated_rule_limit: 5,
		min_sentence_length: 10,
		max_agent_iterations: 3,
		confidence_threshold: 0.6
	});

	// Load test when testId changes
	$effect(() => {
		if (testId && testId !== selectedTestId) {
			loadTest(testId);
		}
	});

	async function loadTest(id: string) {
		loading = true;
		error = '';
		result = null;

		const response = await apiGetTest(id);

		loading = false;

		if (response.error) {
			error = response.error;
		} else if (response.data) {
			selectedTest = response.data;
			selectedTestId = id;
		}
	}

	async function handleRunTest() {
		if (!selectedTestId) return;

		loading = true;
		error = '';
		result = null;

		const response = await apiRunTest(selectedTestId, tuningParams);

		loading = false;

		if (response.error) {
			error = response.error;
		} else if (response.data) {
			result = response.data;
		}
	}
</script>

<div class="space-y-6">
	{#if !selectedTest}
		<div class="text-center py-8 text-gray-500">Select a test from the Browse tab to run it</div>
	{:else}
		<!-- Test Info -->
		<Card.Root>
			<Card.Header>
				<Card.Title>{selectedTest.label}</Card.Title>
			</Card.Header>
			<Card.Content>
				<p class="text-sm text-gray-700 mb-2">{selectedTest.text}</p>
				<div class="text-xs text-muted-foreground">
					Expected violations: {selectedTest.expected_violations.length}
				</div>
			</Card.Content>
		</Card.Root>

		<!-- Tuning Parameters -->
		<div class="border-t border-gray-200 pt-6">
			<TuningParameters bind:parameters={tuningParams} disabled={loading} />
		</div>

		<!-- Run Button -->
		<Button.Root onclick={handleRunTest} disabled={loading} class="w-full">
			{#if loading}
				<LoaderCircle class="mr-2 h-4 w-4 animate-spin" />
			{:else}
				<Play class="mr-2 h-4 w-4" />
			{/if}
			Run Test
		</Button.Root>

		<!-- Error Display -->
		{#if error}
			<Alert.Root variant="destructive">
				<Alert.Description>{error}</Alert.Description>
			</Alert.Root>
		{/if}

		<!-- Results Display -->
		{#if result}
			<div class="space-y-4">
				<MetricsDisplay metrics={result.metrics} executionTime={result.execution_time_seconds} />

				{#if result.detected_violations.length > 0}
					<Card.Root>
						<Card.Header>
							<Card.Title class="text-lg">
								Detected Violations ({result.detected_violations.length})
							</Card.Title>
						</Card.Header>
						<Card.Content>
							<div class="space-y-3">
								{#each result.detected_violations as violation (violation)}
									<div class="border-l-4 border-destructive pl-4 py-1">
										<div class="font-semibold text-sm">{violation.rule}</div>
										<div class="text-sm text-gray-600 mt-1">"{violation.text}"</div>
										{#if violation.reason}
											<div class="text-xs text-gray-500 mt-1">{violation.reason}</div>
										{/if}
									</div>
								{/each}
							</div>
						</Card.Content>
					</Card.Root>
				{/if}
			</div>
		{/if}
	{/if}
</div>
