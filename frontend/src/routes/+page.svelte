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
	let tuningParams = $state<TuningParameters>({} as any);

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
		processingTime = 0;

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
				link: v.url || ''
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
				<span class="font-bold inline-block">Style Auditor </span>
			</div>

			<div class="flex items-center gap-4">
				<Button.Root variant="ghost" size="sm" class="gap-2 font-bold text-primary" href="/tests">
					<BarChart3 class="h-4 w-4" /> Benchmarking
				</Button.Root>
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
		<div class="space-y-6 animate-in fade-in duration-300">
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
			{#if !loading && (processingTime > 0 || violations.length > 0 || testResult || error || success)}
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

					{#if processingTime > 0 && violations.length === 0 && !error}
						<div
							class="flex items-center gap-2 p-4 rounded-lg bg-green-500/10 text-green-600 dark:text-green-400 text-sm font-medium border border-green-500/20"
						>
							<CircleCheckBig class="h-4 w-4" />
							No violations found. You can still add custom violations or save as a test case.
						</div>
					{/if}

					<AuditResultsEditor {violations} onSaveAsTest={handleSaveAsTest} />
				</section>
			{/if}
		</div>
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
