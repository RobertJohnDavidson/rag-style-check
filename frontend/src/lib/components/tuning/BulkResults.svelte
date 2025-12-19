<script lang="ts">
	import { Card, Badge } from "$lib/components/ui";
	import { CheckCircle2, XCircle, AlertCircle, BarChart3 } from "@lucide/svelte";
	import type { TestResult } from "$lib/types";

	interface Props {
		results: Array<{ testLabel: string, result: TestResult | null, error?: string }>;
	}

	let { results }: Props = $props();

	let stats = $derived.by(() => {
		const total = results.length;
		const successful = results.filter(r => r.result !== null).length;
		const totalViolations = results.reduce((acc, r) => acc + (r.result?.detected_violations.length || 0), 0);
		
		// Average metrics for successful runs
		const successfulRuns = results.filter(r => r.result !== null).map(r => r.result!);
		const avgPrecision = successfulRuns.length ? successfulRuns.reduce((acc, r) => acc + (r.metrics?.precision ?? 0), 0) / successfulRuns.length : 0;
		const avgRecall = successfulRuns.length ? successfulRuns.reduce((acc, r) => acc + (r.metrics?.recall ?? 0), 0) / successfulRuns.length : 0;
		const avgF1 = successfulRuns.length ? successfulRuns.reduce((acc, r) => acc + (r.metrics?.f1_score ?? 0), 0) / successfulRuns.length : 0;

		return {
			total,
			successful,
			failed: total - successful,
			totalViolations,
			avgPrecision: (avgPrecision * 100).toFixed(1),
			avgRecall: (avgRecall * 100).toFixed(1),
			avgF1: (avgF1 * 100).toFixed(1)
		};
	});
</script>

<div class="space-y-6">
	<!-- Summary Stats -->
	<div class="grid grid-cols-2 md:grid-cols-4 gap-4">
		<Card.Root class="p-4 flex flex-col items-center justify-center text-center">
			<div class="text-2xl font-bold text-primary">{stats.successful}/{stats.total}</div>
			<div class="text-xs text-muted-foreground uppercase tracking-wider">Passed</div>
		</Card.Root>
		<Card.Root class="p-4 flex flex-col items-center justify-center text-center">
			<div class="text-2xl font-bold text-primary">{stats.avgPrecision}%</div>
			<div class="text-xs text-muted-foreground uppercase tracking-wider">Avg Precision</div>
		</Card.Root>
		<Card.Root class="p-4 flex flex-col items-center justify-center text-center">
			<div class="text-2xl font-bold text-primary">{stats.avgRecall}%</div>
			<div class="text-xs text-muted-foreground uppercase tracking-wider">Avg Recall</div>
		</Card.Root>
		<Card.Root class="p-4 flex flex-col items-center justify-center text-center">
			<div class="text-2xl font-bold text-primary">{stats.avgF1}%</div>
			<div class="text-xs text-muted-foreground uppercase tracking-wider">Avg F1 Score</div>
		</Card.Root>
	</div>

	<!-- Individual Results List -->
	<div class="space-y-2">
		<div class="flex items-center gap-2 mb-2 px-1">
			<BarChart3 class="h-4 w-4 text-muted-foreground" />
			<h3 class="text-sm font-semibold uppercase tracking-wider text-muted-foreground">
				Test Execution Log
			</h3>
		</div>

		<div class="space-y-2 max-h-96 overflow-y-auto pr-2 custom-scrollbar">
			{#each results as item}
				<div
					class="flex items-center justify-between p-3 rounded-lg border border-border bg-card/50"
				>
					<div class="flex flex-col gap-0.5">
						<div class="text-sm font-medium">{item.testLabel}</div>
						{#if item.error}
							<div class="text-xs text-destructive">{item.error}</div>
						{:else if item.result}
							<div class="flex gap-2">
								<Badge.Root variant="secondary" class="text-[10px] py-0"
									>{item.result.detected_violations.length} violations</Badge.Root
								>
								<Badge.Root variant="outline" class="text-[10px] py-0"
									>F1: {((item.result.metrics?.f1_score ?? 0) * 100).toFixed(0)}%</Badge.Root
								>
							</div>
						{/if}
					</div>

					<div>
						{#if item.error}
							<XCircle class="h-5 w-5 text-destructive" />
						{:else if item.result}
							<CheckCircle2 class="h-5 w-5 text-green-500" />
						{/if}
					</div>
				</div>
			{/each}
		</div>
	</div>
</div>

<style>
	.custom-scrollbar::-webkit-scrollbar {
		width: 4px;
	}
	.custom-scrollbar::-webkit-scrollbar-track {
		background: transparent;
	}
	.custom-scrollbar::-webkit-scrollbar-thumb {
		background: hsl(var(--muted-foreground) / 0.3);
		border-radius: 10px;
	}
</style>
