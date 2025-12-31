<script lang="ts">
	import { onMount } from 'svelte';
	import { Button, Card, Badge, Label, Slider, Tabs } from '$lib/components/ui';
	import { 
		LoaderCircle, 
		Play, 
		BarChart3, 
		ArrowLeft, 
		Zap, 
		History, 
		Trash2,
		Pause,
		LayoutGrid,
		AlertCircle,
		Settings2
	} from '@lucide/svelte';
	import { 
		runTest, 
		loadTests, 
		getTuningDefaults, 
		getModels,
		getTest
	} from '$lib/api';
	import type { Test, TestResult, TuningParameters, ModelInfo } from '$lib/types';
	import { 
		TestSelector, 
		ConfigProfileEditor, 
		BulkBenchmarkDashboard 
	} from '$lib/components/tuning';

	// Types
	interface ConfigProfile {
		id: string;
		label: string;
		params: TuningParameters;
	}

	// State
	let tests = $state<Test[]>([]);
	let models = $state<ModelInfo[]>([]);
	let selectedTestIds = $state<string[]>([]);
	let profiles = $state<ConfigProfile[]>([]);
	let iterations = $state(1);
	
	let running = $state(false);
	let paused = $state(false);
	let currentProgress = $state({ current: 0, total: 0 });
	let benchmarkResults = $state<TestResult[]>([]);
	let activeTab = $state('setup');
	let error = $state('');

	// Load initial data
	onMount(async () => {
		const [testsRes, defaultsRes, modelsRes] = await Promise.all([
			loadTests({ page_size: 100 }),
			getTuningDefaults(),
			getModels()
		]);

		if (testsRes.data) tests = testsRes.data.tests;
		if (modelsRes.data) models = modelsRes.data;
		
		if (defaultsRes.data) {
			profiles = [{
				id: 'default',
				label: 'Baseline Config',
				params: defaultsRes.data
			}];
		}
	});

	async function startBenchmark() {
		if (selectedTestIds.length === 0 || profiles.length === 0) return;
		
		running = true;
		paused = false;
		activeTab = 'results';
		benchmarkResults = [];
		error = '';

		const totalUnits = selectedTestIds.length * profiles.length * iterations;
		currentProgress = { current: 0, total: totalUnits };

		try {
			for (let i = 0; i < iterations; i++) {
				for (const profile of profiles) {
					for (const testId of selectedTestIds) {
						if (!running) break;
						while (paused) {
							await new Promise(r => setTimeout(r, 500));
						}

						const { data, error: apiError } = await runTest(testId, profile.params, profile.id);
						
						if (data) {
							// The backend returns profile_id, but we ensure it's set for safety
							const resultWithProfile = { ...data, profile_id: data.profile_id || profile.id }; 
							benchmarkResults = [...benchmarkResults, resultWithProfile];
						} else {
							error = apiError || 'Unknown error occurred during test run.';
							console.error(`Run failed for test ${testId} with profile ${profile.label}: ${apiError}`);
							running = false;
							return;
						}

						currentProgress.current++;
					}
					if (!running) break;
				}
				if (!running) break;
			}
		} catch (err) {
			error = 'Benchmark interrupted by an unexpected error.';
			console.error(err);
		} finally {
			running = false;
		}
	}

	function stopBenchmark() {
		running = false;
		paused = false;
	}

	function togglePause() {
		paused = !paused;
	}

	function handleSelectionChange(ids: string[]) {
		selectedTestIds = ids;
	}

	function handleProfilesChange(newProfiles: ConfigProfile[]) {
		profiles = newProfiles;
	}

	let selectedTests = $derived(tests.filter(t => selectedTestIds.includes(t.id)));
	let progressPercent = $derived((currentProgress.current / (currentProgress.total || 1)) * 100);

</script>

<div class="min-h-screen bg-background text-foreground pb-20">
	<!-- Header -->
	<header
		class="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60"
	>
		<div class="flex h-14 items-center justify-between px-8">
			<div class="flex items-center gap-4">
				<a href="/" class="p-2 hover:bg-muted rounded-full transition-colors">
					<ArrowLeft class="h-5 w-5" />
				</a>
				<div class="flex items-center gap-2">
					<Zap class="h-6 w-6 text-primary fill-primary" />
					<span class="font-bold">Style Auditor Benchmark</span>
				</div>
			</div>

			<div class="flex items-center gap-4">
				<Badge.Root variant="secondary">
					{selectedTestIds.length} Tests • {profiles.length} Configs • {iterations} Runs
				</Badge.Root>
				{#if !running}
					<Button.Root
						variant="default"
						size="sm"
						class="gap-2 font-bold"
						disabled={selectedTestIds.length === 0 || profiles.length === 0}
						onclick={startBenchmark}
					>
						<Play class="h-4 w-4 fill-current" /> Start Benchmark
					</Button.Root>
				{:else}
					<div class="flex gap-2">
						<Button.Root variant="outline" size="sm" onclick={togglePause}>
							{#if paused}
								<Play class="h-4 w-4 fill-current" /> Resume
							{:else}
								<Pause class="h-4 w-4 fill-current" /> Pause
							{/if}
						</Button.Root>
						<Button.Root variant="destructive" size="sm" onclick={stopBenchmark}>Stop</Button.Root>
					</div>
				{/if}
			</div>
		</div>

		<!-- Progress Bar -->
		{#if running || progressPercent === 100}
			<div class="h-1 w-full bg-muted overflow-hidden">
				<div
					class="h-full bg-primary transition-all duration-500 ease-out"
					style="width: {progressPercent}%"
				></div>
			</div>
		{/if}
	</header>

	<main class="container max-w-7xl py-8 space-y-8 mx-auto px-4 sm:px-6 lg:px-8">
		<Tabs.Root bind:value={activeTab} class="w-full">
			<Tabs.List class="grid w-full max-w-2xl grid-cols-2 mb-12 mx-auto h-12 p-1 bg-muted/20">
				<Tabs.Trigger value="setup" class="flex items-center gap-2 py-2 text-base font-bold">
					<Settings2 class="h-4 w-4" /> Benchmark Setup
				</Tabs.Trigger>
				<Tabs.Trigger value="results" class="flex items-center gap-2 py-2 text-base font-bold">
					<BarChart3 class="h-4 w-4" /> Benchmark Results
					{#if benchmarkResults.length > 0}
						<Badge.Root variant="secondary" class="ml-2 font-mono">
							{benchmarkResults.length}
						</Badge.Root>
					{/if}
				</Tabs.Trigger>
			</Tabs.List>

			<Tabs.Content
				value="setup"
				class="space-y-12 outline-none animate-in fade-in slide-in-from-top-2 duration-300"
			>
				<div class="grid grid-cols-1 lg:grid-cols-12 gap-10">
					<!-- Left: Search & Select -->
					<div class="lg:col-span-5 space-y-6">
						<div class="space-y-4">
							<div class="flex items-center gap-2 px-1 text-muted-foreground">
								<LayoutGrid class="h-4 w-4" />
								<h2 class="text-xs font-bold uppercase tracking-widest">Test Selection</h2>
							</div>

							<Card.Root>
								<Card.Content class="pt-6 space-y-4">
									<div class="flex justify-between items-center">
										<Label.Root class="font-bold">Runs per Test/Config</Label.Root>
										<Badge.Root variant="outline">{iterations}x</Badge.Root>
									</div>
									<Slider.Root
										type="multiple"
										value={[iterations]}
										onValueChange={(v) => (iterations = v[0])}
										min={1}
										max={10}
										step={1}
										disabled={running}
									/>
									<p class="text-[10px] text-muted-foreground uppercase font-bold tracking-wider">
										Increase for more consistent averages
									</p>
								</Card.Content>
							</Card.Root>

							<Card.Root>
								<Card.Content class="pt-6">
									<TestSelector
										multiSelect={true}
										onSelectionChange={handleSelectionChange}
										disabled={running}
									/>
								</Card.Content>
							</Card.Root>
						</div>
					</div>

					<!-- Right: Config Profiles -->
					<div class="lg:col-span-7 space-y-6">
						<div class="space-y-4">
							<div class="flex items-center gap-2 px-1 text-muted-foreground">
								<Zap class="h-4 w-4" />
								<h2 class="text-xs font-bold uppercase tracking-widest">Configuration Profiles</h2>
							</div>
							<ConfigProfileEditor bind:profiles {models} onProfilesChange={handleProfilesChange} />
						</div>
					</div>
				</div>
			</Tabs.Content>

			<Tabs.Content value="results" class="space-y-12 outline-none">
				<div class="space-y-12">
					{#if error}
						<div
							class="bg-destructive/10 border border-destructive text-destructive px-4 py-3 rounded-md flex items-center gap-2 animate-in fade-in slide-in-from-top-4"
						>
							<AlertCircle class="h-5 w-5" />
							<div class="flex-1">
								<p class="text-sm font-bold">Benchmark Failed</p>
								<p class="text-xs opacity-90">{error}</p>
							</div>
							<Button.Root variant="ghost" size="sm" onclick={() => (error = '')}
								>Dismiss</Button.Root
							>
						</div>
					{/if}

					{#if benchmarkResults.length > 0 || running}
						<section class="animate-in fade-in slide-in-from-bottom-4 duration-500">
							<div class="flex items-center justify-between mb-6">
								<div class="flex items-center gap-2">
									<BarChart3 class="h-6 w-6 text-primary" />
									<h2 class="text-2xl font-bold tracking-tight">Active Benchmark</h2>
								</div>
								{#if running}
									<div class="flex items-center gap-2 text-sm text-muted-foreground">
										<LoaderCircle class="h-4 w-4 animate-spin" />
										Running: {currentProgress.current} / {currentProgress.total}
									</div>
								{/if}
							</div>

							<BulkBenchmarkDashboard tests={selectedTests} {profiles} results={benchmarkResults} />
						</section>
					{:else}
						<div
							class="flex flex-col items-center justify-center py-24 text-center space-y-4 bg-muted/20 rounded-2xl border-2 border-dashed border-muted"
						>
							<div class="bg-muted p-4 rounded-full">
								<BarChart3 class="h-12 w-12 text-muted-foreground/50" />
							</div>
							<div class="space-y-1">
								<h3 class="text-xl font-bold">No Results Yet</h3>
								<p class="text-muted-foreground max-w-xs mx-auto text-sm">
									Configure your benchmark and click "Start Benchmark" to see results here.
								</p>
							</div>
							<Button.Root variant="outline" onclick={() => (activeTab = 'setup')}>
								Go to Setup
							</Button.Root>
						</div>
					{/if}
				</div>
			</Tabs.Content>
		</Tabs.Root>
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
