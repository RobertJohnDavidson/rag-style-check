<script lang="ts">
	import type { TestMetrics } from '$lib/types';
	import { Card } from '$lib/components/ui';

	interface Props {
		metrics: TestMetrics;
		executionTime?: number;
		class?: string;
	}

	let { metrics, executionTime, class: className = '' }: Props = $props();

	// Format numbers with 3 decimal places, or N/A if undefined/null
	const formatMetric = (value: number | null | undefined) => {
		return value != null ? value.toFixed(3) : 'N/A';
	};
</script>

<Card.Root class={className}>
	<Card.Header>
		<Card.Title class="text-lg">Test Results</Card.Title>
	</Card.Header>
	<Card.Content>
		<!-- Confusion Matrix -->
		<div class="grid grid-cols-4 gap-4 mb-6">
			<div class="text-center">
				<div class="text-3xl font-bold text-green-600">{metrics.true_positives}</div>
				<div class="text-sm text-gray-600">True Positives</div>
			</div>
			<div class="text-center">
				<div class="text-3xl font-bold text-red-600">{metrics.false_positives}</div>
				<div class="text-sm text-gray-600">False Positives</div>
			</div>
			<div class="text-center">
				<div class="text-3xl font-bold text-orange-600">{metrics.false_negatives}</div>
				<div class="text-sm text-gray-600">False Negatives</div>
			</div>
			<div class="text-center">
				<div class="text-3xl font-bold text-blue-600">{metrics.true_negatives}</div>
				<div class="text-sm text-gray-600">True Negatives</div>
			</div>
		</div>

		<!-- Performance Metrics -->
		<div class="grid grid-cols-3 gap-4 border-t border-gray-200 pt-4">
			<div class="text-center">
				<div class="text-2xl font-bold text-primary">{formatMetric(metrics.precision)}</div>
				<div class="text-sm text-gray-600">Precision</div>
			</div>
			<div class="text-center">
				<div class="text-2xl font-bold text-primary">{formatMetric(metrics.recall)}</div>
				<div class="text-sm text-gray-600">Recall</div>
			</div>
			<div class="text-center">
				<div class="text-2xl font-bold text-primary">{formatMetric(metrics.f1_score)}</div>
				<div class="text-sm text-gray-600">F1 Score</div>
			</div>
		</div>

		<!-- Execution Time -->
		{#if executionTime !== undefined}
			<div class="mt-4 text-xs text-muted-foreground text-center">
				Execution time: {executionTime.toFixed(2)}s
			</div>
		{/if}
	</Card.Content>
</Card.Root>
