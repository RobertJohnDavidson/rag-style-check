<script lang="ts">
	import { onMount } from 'svelte';
	import { Button, Textarea, Badge, Card, Tabs } from '$lib/components/ui';
	import { LoaderCircle, Search, Zap, CircleCheckBig, CircleAlert, Sparkles, Wand2, Play, BarChart3, Settings2 } from '@lucide/svelte';
	
	import { 
		AuditResultsEditor, 
		TestSelector, 
		TestRunCompare,
		BulkResults,
		TuningDrawer
	} from '$lib/components/tuning';
	import { 
		auditText, 
		runTest, 
		createTest, 
		generateText, 
		getTest,
		getTuningDefaults,
		getModels
	} from '$lib/api';
	import type { Violation, Test, TestResult, TuningParameters, ModelInfo } from '$lib/types';

	// Main State
	let text = $state('');
	let loading = $state(false);
	let generating = $state(false);
	let error = $state('');
	let success = $state('');
	
	// Results State
	let violations = $state<Violation[]>([]);
	let testResult = $state<TestResult | null>(null);
	let selectedTest = $state<Test | null>(null);
	let processingTime = $state(0);

	// Bulk Test State
	let selectedTestIds = $state<string[]>([]);
	let runningBulk = $state(false);
	let bulkResults = $state<Array<{ testLabel: string, result: TestResult | null, error?: string }>>([]);
	
	// Tuning State
	let showTuning = $state(false);
	let models = $state<ModelInfo[]>([]);
	let tuningParams = $state<TuningParameters>({
		model_name: 'gemini-2.5-flash',
		temperature: 0.1,
		initial_retrieval_count: 75,
		final_top_k: 25,
		rerank_score_threshold: 0.1,
		aggregated_rule_limit: 40,
		min_sentence_length: 5,
		max_agent_iterations: 3,
		confidence_threshold: 10.0,
		include_thinking: false
	});

	async function handleAudit() {
		if (!text.trim()) {
			error = 'Please enter or generate some text first.';
			return;
		}

		loading = true;
		error = '';
		success = '';
		testResult = null;
		violations = [];

		try {
			// If we have a selected test and the text matches its original text, run as a test case
			if (selectedTest && text === selectedTest.text) {
				const { data, error: apiError } = await runTest(selectedTest.id, tuningParams);
				
				if (data) {
					testResult = data;
					violations = data.detected_violations;
					processingTime = data.execution_time_seconds;
				} else {
					error = apiError || 'Failed to run test';
				}
			} else {
				const { data, error: apiError } = await auditText(text, selectedTest?.id, tuningParams);
				if (data) {
					violations = data.violations;
					processingTime = data.metadata?.processing_time_seconds || 0;
				} else {
					error = apiError || 'Audit failed';
				}
			}
		} catch (err) {
			error = 'An unexpected error occurred.';
		} finally {
			loading = false;
		}
	}

	async function handleGenerateText() {
		generating = true;
		error = '';
		const { data, error: apiError } = await generateText();
		if (data) {
			text = data.text;
			selectedTest = null;
			violations = [];
			testResult = null;
		} else {
			error = apiError || 'Failed to generate text';
		}
		generating = false;
	}

	function handleTestSelect(test: Test) {
		selectedTest = test;
		text = test.text;
		violations = [];
		testResult = null;
	}

	function handleSelectionChange(ids: string[]) {
		selectedTestIds = ids;
	}

	async function handleRunBulkTests() {
		if (selectedTestIds.length === 0) return;
		
		runningBulk = true;
		error = '';
		bulkResults = [];

		try {
			for (const id of selectedTestIds) {
				// We need the label, we can either pass it from TestSelector or fetch it
				// For now, let's fetch the test details
				const { data: testData } = await getTest(id);
				if (!testData) continue;

				const { data, error: apiError } = await runTest(id, tuningParams);

				bulkResults = [...bulkResults, {
					testLabel: testData.label,
					result: data || null,
					error: apiError
				}];
			}
		} catch (err) {
			error = 'An error occurred during bulk test execution.';
		} finally {
			runningBulk = false;
		}
	}

	async function handleSaveAsTest(finalViolations: Violation[]) {
		loading = true;
		const { data, error: apiError } = await createTest({
			label: `Tuned Test - ${new Date().toLocaleTimeString()}`,
			text,
			expected_violations: finalViolations.map(v => ({
				rule: v.rule,
				text: v.text,
				reason: v.reason,
				link: v.source_url || ''
			})),
			generation_method: 'manual'
		});

		if (data) {
			success = 'Test case saved successfully!';
			setTimeout(() => success = '', 3000);
		} else {
			error = apiError || 'Failed to save test case';
		}
		loading = false;
	}

	// Theme persistence logic
	let isDark = $state(false);
	function toggleTheme() {
		isDark = !isDark;
		if (isDark) {
			document.documentElement.classList.add('dark');
			localStorage.setItem('theme', 'dark');
		} else {
			document.documentElement.classList.remove('dark');
			localStorage.setItem('theme', 'light');
		}
	}

	onMount(async () => {
		isDark = document.documentElement.classList.contains('dark');
		
		const [defaultsRes, modelsRes] = await Promise.all([
			getTuningDefaults(),
			getModels()
		]);

		if (defaultsRes.data) {
			tuningParams = defaultsRes.data;
		}
		if (modelsRes.data) {
			models = modelsRes.data;
		}
	});
</script>

<div class="min-h-screen bg-background text-foreground pb-20 transition-colors duration-300">
	<!-- Header -->
	<header
		class="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60"
	>
		<div class=" flex h-14 items-center justify-between px-8">
			<div class="flex items-center gap-2">
				<Zap class="h-6 w-6 text-primary fill-primary" />
				<span class="font-bold inline-block"
					>Style Auditor <span
						class="text-muted-foreground font-normal ml-1 text-xs uppercase tracking-widest"
						>Tuning</span
					></span
				>
			</div>

			<div class="flex items-center gap-4">
				<Button.Root
					variant="ghost"
					size="icon"
					onclick={() => (showTuning = true)}
					class="rounded-full"
				>
					<Settings2 class="h-5 w-5" />
				</Button.Root>
				<Button.Root variant="ghost" size="sm" onclick={toggleTheme}>
					{isDark ? 'Light Mode' : 'Dark Mode'}
				</Button.Root>
			</div>
		</div>
	</header>

	<main class="container max-w-4xl py-6 space-y-10 mx-auto">
		<Tabs.Root value="audit" class="w-full">
			<Tabs.List class="grid w-full grid-cols-2 mb-8 h-12">
				<Tabs.Trigger value="audit" class="text-sm font-bold uppercase tracking-widest gap-2">
					<Wand2 class="h-4 w-4" /> Audit Style
				</Tabs.Trigger>
				<Tabs.Trigger value="tests" class="text-sm font-bold uppercase tracking-widest gap-2">
					<Play class="h-4 w-4" /> Bulk Test Runner
				</Tabs.Trigger>
			</Tabs.List>

			<Tabs.Content value="audit" class="space-y-6 animate-in fade-in duration-300">
				<div class="space-y-1">
					<h2 class="text-3xl font-bold tracking-tight">Style Audit</h2>
					<p class="text-muted-foreground">
						Enter text to check for CBC News style guide violations.
					</p>
				</div>

				<Card.Root>
					<Card.Content class="py-4 space-y-6">
						<div class="flex justify-end pr-1">
							<Button.Root
								variant="outline"
								size="sm"
								onclick={handleGenerateText}
								disabled={generating}
								class="gap-2"
							>
								{#if generating}
									<LoaderCircle class="h-4 w-4 animate-spin" /> Generating...
								{:else}
									<Sparkles class="h-4 w-4 text-primary" /> Generate Text
								{/if}
							</Button.Root>
						</div>

						<div class="space-y-4">
							<div class="flex justify-between items-center px-1">
								<div class="flex gap-2">
									{#if selectedTest}
										<Badge.Root variant="secondary" class="font-semibold">
											Linked: {selectedTest.label}
										</Badge.Root>
									{/if}
								</div>
							</div>

							<Textarea.Root
								bind:value={text}
								placeholder="Paste text here to audit..."
								class="min-h-[250px] text-lg resize-none focus-visible:ring-1"
							/>

							<Button.Root
								variant="default"
								class="w-full h-12 text-lg font-bold transition-all hover:scale-[1.01] active:scale-[0.99]"
								disabled={loading || !text.trim()}
								onclick={handleAudit}
							>
								{#if loading}
									<LoaderCircle class="mr-2 h-5 w-5 animate-spin" /> Auditing Style...
								{:else}
									Start Style Audit
								{/if}
							</Button.Root>
						</div>
					</Card.Content>
				</Card.Root>

				<!-- Results Section -->
				{#if violations.length > 0 || testResult || error || success}
					<section class="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
						{#if error && !runningBulk}
							<div
								class="flex items-center gap-2 p-4 rounded-lg bg-destructive/10 text-destructive text-sm font-medium border border-destructive/20"
							>
								<CircleAlert class="h-4 w-4" />
								{error}
							</div>
						{/if}
						{#if success}
							<div
								class="flex items-center gap-2 p-4 rounded-lg bg-green-500/10 text-green-600 dark:text-green-400 text-sm font-medium border border-green-500/20"
							>
								<CircleCheckBig class="h-4 w-4" />
								{success}
							</div>
						{/if}

						{#if testResult}
							<div class="space-y-4">
								<div class="flex items-center gap-4">
									<div class="h-px flex-1 bg-border"></div>
									<h3 class="text-xs font-bold uppercase tracking-[0.2em] text-muted-foreground">
										Performance Metrics
									</h3>
									<div class="h-px flex-1 bg-border"></div>
								</div>
								<TestRunCompare
									metrics={testResult.metrics}
									expectedCount={selectedTest?.expected_violations.length || 0}
									detectedCount={violations.length}
								/>
							</div>
						{/if}

						<AuditResultsEditor {violations} onSaveAsTest={handleSaveAsTest} />
					</section>
				{/if}
			</Tabs.Content>

			<Tabs.Content value="tests" class="space-y-6 animate-in fade-in duration-300">
				<div class="space-y-1">
					<h2 class="text-3xl font-bold tracking-tight">Bulk Test Runner</h2>
					<p class="text-muted-foreground">
						Select multiple test cases to run against the style checker in bulk.
					</p>
				</div>

				<div class="grid grid-cols-1 md:grid-cols-3 gap-8">
					<div class="md:col-span-1 space-y-4">
						<Card.Root>
							<Card.Content class="pt-6">
								<TestSelector multiSelect={true} onSelectionChange={handleSelectionChange} />
								<div class="mt-6">
									<Button.Root
										variant="default"
										class="w-full gap-2 h-11"
										disabled={selectedTestIds.length === 0 || runningBulk}
										onclick={handleRunBulkTests}
									>
										{#if runningBulk}
											<LoaderCircle class="h-4 w-4 animate-spin" /> Running...
										{:else}
											<Play class="h-4 w-4" /> Run {selectedTestIds.length} Selected
										{/if}
									</Button.Root>
								</div>
							</Card.Content>
						</Card.Root>
					</div>

					<div class="md:col-span-2">
						{#if bulkResults.length > 0}
							<section class="animate-in fade-in slide-in-from-right-4 duration-500">
								<BulkResults results={bulkResults} />
							</section>
						{:else if runningBulk}
							<div
								class="flex flex-col items-center justify-center h-64 border border-dashed rounded-lg bg-muted/30 text-center px-8"
							>
								<LoaderCircle class="h-8 w-8 animate-spin text-primary mb-4" />
								<p class="text-muted-foreground font-medium">
									Executing {selectedTestIds.length} tests...
								</p>
							</div>
						{:else}
							<div
								class="flex flex-col items-center justify-center h-64 border border-dashed rounded-lg bg-muted/30 text-center px-8"
							>
								<BarChart3 class="h-10 w-10 text-muted-foreground mb-4 opacity-20" />
								<p class="text-muted-foreground">
									Select tests from the left and click run to see results.
								</p>
							</div>
						{/if}
					</div>
				</div>
			</Tabs.Content>
		</Tabs.Root>
	</main>

	<TuningDrawer bind:isOpen={showTuning} bind:parameters={tuningParams} {models} />
</div>

<style>
	.animate-in {
		animation-duration: 0.5s;
		animation-fill-mode: both;
	}
	
	@keyframes fadeIn {
		from { opacity: 0; }
		to { opacity: 1; }
	}
	
	@keyframes slideInFromBottom {
		from { transform: translateY(1rem); opacity: 0; }
		to { transform: translateY(0); opacity: 1; }
	}
	
	.fade-in { animation-name: fadeIn; }
	.slide-in-from-bottom-4 { animation-name: slideInFromBottom; }
</style>
