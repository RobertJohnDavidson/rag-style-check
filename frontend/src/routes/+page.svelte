<script lang="ts">
	import { onMount } from 'svelte';
	import { Button, Textarea, Badge, Card } from '$lib/components/ui';
	import { LoaderCircle, Search, Zap, CircleCheckBig, CircleAlert } from '@lucide/svelte';
	
	import { 
		InputModeSelector, 
		AuditResultsEditor, 
		TestSelector, 
		TextGenerator,
		TestRunCompare
	} from '$lib/components/tuning';
	import { auditText, runTest, createTest } from '$lib/api';
	import type { Violation, Test, TestResult } from '$lib/types';

	// Main State
	let text = $state('');
	let currentMode = $state<'manual' | 'generate' | 'test'>('manual');
	let loading = $state(false);
	let error = $state('');
	let success = $state('');
	
	// Results State
	let violations = $state<Violation[]>([]);
	let testResult = $state<TestResult | null>(null);
	let selectedTest = $state<Test | null>(null);
	let processingTime = $state(0);

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
			if (currentMode === 'test' && selectedTest) {
				const { data, error: apiError } = await runTest(selectedTest.id, {
					model_name: 'models/gemini-1.5-pro'
				} as any);
				
				if (data) {
					testResult = data;
					violations = data.detected_violations;
					processingTime = data.execution_time_seconds;
				} else {
					error = apiError || 'Failed to run test';
				}
			} else {
				const { data, error: apiError } = await auditText(text, selectedTest?.id);
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

	function handleModeChange(mode: 'manual' | 'generate' | 'test') {
		currentMode = mode;
		if (mode !== 'test') {
			selectedTest = null;
			testResult = null;
		}
	}

	function handleTestSelect(test: Test) {
		selectedTest = test;
		text = test.text;
		violations = [];
		testResult = null;
	}

	function handleGenerated(generatedText: string) {
		text = generatedText;
		currentMode = 'manual';
		violations = [];
		testResult = null;
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

	onMount(() => {
		isDark = document.documentElement.classList.contains('dark');
	});
</script>

<div class="min-h-screen bg-background text-foreground pb-20 transition-colors duration-300">
	<!-- Header -->
	<header
		class="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60"
	>
		<div class="container flex h-14 items-center justify-between">
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
				<Button.Root variant="ghost" size="sm" onclick={toggleTheme}>
					{isDark ? 'Light Mode' : 'Dark Mode'}
				</Button.Root>
			</div>
		</div>
	</header>

	<main class="container max-w-4xl py-10 space-y-10 mx-auto">
		<!-- Main Tuning Interface -->
		<section class="space-y-6">
			<div class="flex flex-col md:flex-row md:justify-between md:items-end gap-6">
				<div class="space-y-1">
					<h2 class="text-3xl font-bold tracking-tight">Efficiency Tuning</h2>
					<p class="text-muted-foreground">
						Refine model performance and create ground truth test cases.
					</p>
				</div>
				<InputModeSelector {currentMode} onModeChange={handleModeChange} />
			</div>

			<Card.Root>
				<Card.Content class="pt-6 space-y-6">
					{#if currentMode === 'generate'}
						<TextGenerator onGenerated={handleGenerated} />
					{:else if currentMode === 'test'}
						<TestSelector onSelect={handleTestSelect} />
					{/if}

					<div class="space-y-4">
						<div class="flex justify-between items-center px-1">
							<div class="flex gap-2">
								<Badge.Root variant="outline" class="font-normal text-muted-foreground">
									{text.length > 0 ? `${text.split(' ').length} words` : 'Empty text'}
								</Badge.Root>
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
		</section>

		<!-- Results Section -->
		{#if violations.length > 0 || testResult || error || success}
			<section class="space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
				{#if error}
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
	</main>
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
