<script lang="ts">
	import { Card, Badge, Button } from '$lib/components/ui';
	import { BarChart3, TrendingUp, AlertCircle, ChevronRight, Info } from '@lucide/svelte';
	import type { TestResult, Test, TestMetrics } from '$lib/types';
	import TestRunDetail from './TestRunDetail.svelte';

	interface ConfigProfile {
		id: string;
		label: string;
	}

	interface Props {
		tests: Test[];
		profiles: ConfigProfile[];
		results: TestResult[]; // Flattened list of all runs
	}

	let { tests, profiles, results }: Props = $props();

	let selectedRun = $state<TestResult | null>(null);
	let selectedTest = $state<Test | null>(null);

	function openDetails(test: Test, result: TestResult) {
		selectedTest = test;
		selectedRun = result;
	}

	function closeDetails() {
		selectedRun = null;
		selectedTest = null;
	}

	// Group results by Test and Profile
	let processedResults = $derived.by(() => {
		const grid = new Map<string, Map<string, { runs: TestResult[], avg: TestMetrics }>>();

		for (const test of tests) {
			const profileMap = new Map<string, { runs: TestResult[], avg: TestMetrics }>();
			for (const profile of profiles) {
				// We need a way to link TestResult to Profile. 
				// For now, let's assume the run logic tags them.
				// For the dashboard, we'll look for results where tuning_parameters match.
				// Better: The runner should provide the mapping.
				// For now, let's assume results are filtered/linked by the parent.
				profileMap.set(profile.id, { runs: [], avg: {} as any });
			}
			grid.set(test.id, profileMap);
		}

		// Fill the grid (mock logic for now, depends on how results are passed)
		// ...
		
		return grid;
	});

	function getStatus(metrics: TestMetrics) {
		const expected = metrics.true_positives + metrics.false_negatives;
		const hits = metrics.true_positives;
		const missed = metrics.false_negatives;
		const noise = metrics.false_positives;

		if (expected === 0) {
			return noise === 0 ? 'CLEAN' : 'NOISY';
		}
		if (missed === 0 && noise === 0) return 'PERFECT';
		if (hits > 0) return 'IMPERFECT';
		return 'FAILED';
	}

	function getStatusColor(status: string) {
		switch (status) {
			case 'PERFECT':
			case 'CLEAN':
				return 'text-green-500';
			case 'IMPERFECT':
			case 'NOISY':
				return 'text-yellow-500';
			case 'FAILED':
				return 'text-red-500';
			default:
				return 'text-muted-foreground';
		}
	}

	function calculateAvgMetrics(runs: TestResult[]): TestMetrics {
		if (runs.length === 0) return {} as any;
		const count = runs.length;
		return {
			precision: runs.reduce((acc, r) => acc + (r.metrics.precision || 0), 0) / count,
			recall: runs.reduce((acc, r) => acc + (r.metrics.recall || 0), 0) / count,
			f1_score: runs.reduce((acc, r) => acc + (r.metrics.f1_score || 0), 0) / count,
			true_positives: runs.reduce((acc, r) => acc + r.metrics.true_positives, 0) / count,
			false_positives: runs.reduce((acc, r) => acc + r.metrics.false_positives, 0) / count,
			false_negatives: runs.reduce((acc, r) => acc + r.metrics.false_negatives, 0) / count,
			true_negatives: runs.reduce((acc, r) => acc + r.metrics.true_negatives, 0) / count,
		};
	}

	// This is better calculated in the parent and passed down or managed here.
	// Let's assume the parent passes a structured object:
	// benchmarkData: Map<testId, Map<profileId, { runs, avg }>>
	
	// For now, let's use a simpler approach for the UI:
</script>

<div class="space-y-8">
	<!-- Overall Progress/Summary -->
	<div class="grid grid-cols-1 md:grid-cols-3 gap-4">
		<Card.Root class="p-4 flex flex-col items-center justify-center text-center">
			<div class="text-3xl font-bold text-primary">{results.length}</div>
			<div class="text-xs text-muted-foreground uppercase tracking-wider font-semibold">
				Total Executions
			</div>
		</Card.Root>
		<Card.Root class="p-4 flex flex-col items-center justify-center text-center">
			<div class="text-3xl font-bold text-primary">
				{#each [results.filter( (r) => ['PERFECT', 'CLEAN'].includes(getStatus(r.metrics)) ).length] as perfectCount}
					{((perfectCount / (results.length || 1)) * 100).toFixed(0)}%
				{/each}
			</div>
			<div class="text-xs text-muted-foreground uppercase tracking-wider font-semibold">
				Perfect Pass Rate
			</div>
		</Card.Root>
		<Card.Root class="p-4 flex flex-col items-center justify-center text-center">
			<div class="text-3xl font-bold text-primary">
				{(
					results.reduce((acc, r) => acc + r.execution_time_seconds, 0) / (results.length || 1)
				).toFixed(2)}s
			</div>
			<div class="text-xs text-muted-foreground uppercase tracking-wider font-semibold">
				Avg Latency
			</div>
		</Card.Root>
	</div>

	<!-- Comparison Table -->
	<Card.Root class="overflow-hidden">
		<div class="overflow-x-auto">
			<table class="w-full text-sm border-collapse">
				<thead>
					<tr class="bg-muted/50 border-b">
						<th class="p-4 text-left font-bold border-r w-64">Test Case</th>
						{#each profiles as profile}
							<th class="p-4 text-center font-bold border-r min-w-[120px]">
								{profile.label}
							</th>
						{/each}
					</tr>
				</thead>
				<tbody class="divide-y">
					{#each tests as test}
						<tr>
							<td class="p-4 font-medium border-r bg-muted/10">
								<div class="flex flex-col">
									<span class="line-clamp-2">{test.label}</span>
									<span class="text-[10px] text-muted-foreground uppercase"
										>{test.generation_method}</span
									>
								</div>
							</td>
							{#each profiles as profile}
								{@const cellResults = results.filter(
									(r) =>
										r.test_id === test.id && (r.profile_id === profile.id || r.id === profile.id)
								)}
								{@const avg = calculateAvgMetrics(cellResults)}
								{@const status = getStatus(avg)}
								<td
									class="p-4 border-r text-center transition-all hover:bg-muted/10 cursor-pointer group/cell"
									onclick={() =>
										cellResults.length > 0 &&
										openDetails(test, cellResults[cellResults.length - 1])}
									onkeydown={(e) => {
										if ((e.key === 'Enter' || e.key === ' ') && cellResults.length > 0) {
											e.preventDefault();
											openDetails(test, cellResults[cellResults.length - 1]);
										}
									}}
									role="button"
									tabindex="0"
								>
									{#if cellResults.length > 0}
										<div class="flex flex-col items-center gap-1">
											<div class="text-base font-black {getStatusColor(status)}">
												{status}
											</div>
											<div class="flex flex-wrap justify-center gap-1 max-w-[120px]">
												<Badge.Root
													variant="outline"
													class="text-[10px] px-1 py-0 h-4 border-green-500/20 text-green-600 bg-green-500/5"
												>
													H: {avg.true_positives.toFixed(0)}
												</Badge.Root>
												<Badge.Root
													variant="outline"
													class="text-[10px] px-1 py-0 h-4 border-red-500/20 text-red-600 bg-red-500/5"
												>
													M: {avg.false_negatives.toFixed(0)}
												</Badge.Root>
												<Badge.Root
													variant="outline"
													class="text-[10px] px-1 py-0 h-4 border-amber-500/20 text-amber-600 bg-amber-500/5"
												>
													N: {avg.false_positives.toFixed(0)}
												</Badge.Root>
											</div>
											<span
												class="text-[9px] text-muted-foreground mt-1 opacity-0 group-hover/cell:opacity-100 transition-opacity"
											>
												Click for Details
											</span>
										</div>
									{:else}
										<span class="text-muted-foreground/30">—</span>
									{/if}
								</td>
							{/each}
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	</Card.Root>

	<!-- Detailed Log (Optional list view of latest runs) -->
	<div class="space-y-4">
		<div class="flex items-center gap-2 px-1">
			<TrendingUp class="h-4 w-4 text-primary" />
			<h3 class="text-sm font-bold uppercase tracking-wider">Latest Benchmarked Runs</h3>
		</div>
		<div class="space-y-2">
			{#each results.slice(-10).reverse() as run}
				{@const testCase = tests.find((t) => t.id === run.test_id)}
				{@const status = getStatus(run.metrics)}
				<div
					class="flex items-center justify-between p-3 rounded-lg border bg-card/50 hover:bg-card transition-colors group"
				>
					<div class="flex items-center gap-4">
						<div class="flex flex-col">
							<span class="text-sm font-semibold">{testCase?.label || 'Unknown Test'}</span>
							<span class="text-[10px] text-muted-foreground flex items-center gap-1">
								Ran at {new Date(run.executed_at).toLocaleTimeString()} • {run.execution_time_seconds.toFixed(
									2
								)}s
							</span>
						</div>
					</div>
					<div
						class="flex items-center gap-4 cursor-pointer"
						onclick={() => testCase && openDetails(testCase, run)}
						onkeydown={(e) => {
							if ((e.key === 'Enter' || e.key === ' ') && testCase) {
								e.preventDefault();
								openDetails(testCase, run);
							}
						}}
						role="button"
						tabindex="0"
					>
						<div class="flex flex-col items-end">
							<span class="text-sm font-bold {getStatusColor(status)}">
								{status}
							</span>
							<div class="flex gap-1 mt-0.5">
								<span class="text-[9px] text-green-600 font-bold"
									>H:{run.metrics.true_positives}</span
								>
								<span class="text-[9px] text-red-600 font-bold"
									>M:{run.metrics.false_negatives}</span
								>
								<span class="text-[9px] text-amber-600 font-bold"
									>N:{run.metrics.false_positives}</span
								>
							</div>
						</div>
						<ChevronRight
							class="h-4 w-4 text-muted-foreground group-hover:text-primary transition-colors"
						/>
					</div>
				</div>
			{/each}
		</div>
	</div>

	{#if selectedRun && selectedTest}
		<TestRunDetail test={selectedTest} result={selectedRun} onClose={closeDetails} />
	{/if}
</div>
