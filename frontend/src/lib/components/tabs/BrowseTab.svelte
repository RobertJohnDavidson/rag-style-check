<script lang="ts">
	import type { Test } from '$lib/types';
	import { Input, Select, Button, LoadingSpinner, Alert } from '$lib/components/ui';
	import { TestCard } from '$lib/components/tests';
	import { loadTests as apiLoadTests, deleteTest as apiDeleteTest } from '$lib/api';
	import { LoaderCircle, Search } from '@lucide/svelte';

	interface Props {
		onSelectTest?: (testId: string) => void;
	}

	let { onSelectTest }: Props = $props();

	// Local state
	let tests = $state<Test[]>([]);
	let loading = $state(false);
	let error = $state('');
	let page = $state(1);
	let total = $state(0);
	let search = $state('');
	let method = $state<string>('');

	// Load tests on mount
	$effect(() => {
		loadTests();
	});

	async function loadTests() {
		loading = true;
		error = '';

		const params: Record<string, string | number> = {
			page: page,
			page_size: 20
		};

		if (search) {
			params.search = search;
		}

		if (method) {
			params.generation_method = method;
		}

		const response = await apiLoadTests(params);

		loading = false;

		if (response.error) {
			error = response.error;
		} else if (response.data) {
			tests = response.data.tests;
			total = response.data.total;
		}
	}

	async function handleDelete(testId: string) {
		if (!confirm('Are you sure you want to delete this test?')) {
			return;
		}

		const response = await apiDeleteTest(testId);

		if (response.error) {
			error = response.error;
		} else {
			// Reload tests
			await loadTests();
		}
	}

	function handlePrevious() {
		if (page > 1) {
			page--;
			loadTests();
		}
	}

	function handleNext() {
		if (page * 20 < total) {
			page++;
			loadTests();
		}
	}

	const hasPrevious = $derived(page > 1);
	const hasNext = $derived(page * 20 < total);
</script>

<div class="space-y-4">
	<!-- Search and Filter -->
	<div class="flex gap-4">
		<Input.Root type="text" bind:value={search} placeholder="Search tests..." class="flex-1" />

		<Select.Root type="single" bind:value={method}>
			<Select.Trigger class="w-48">
				{#if method === ''}
					All Methods
				{:else if method === 'manual'}
					Manual
				{:else if method === 'article'}
					From Article
				{:else if method === 'synthetic'}
					Synthetic
				{/if}
			</Select.Trigger>
			<Select.Content>
				<Select.Item value="" label="All Methods" />
				<Select.Item value="manual" label="Manual" />
				<Select.Item value="article" label="From Article" />
				<Select.Item value="synthetic" label="Synthetic" />
			</Select.Content>
		</Select.Root>

		<Button.Root onclick={loadTests} disabled={loading}>
			{#if loading}
				<LoaderCircle class="mr-2 h-4 w-4 animate-spin" />
			{:else}
				<Search class="mr-2 h-4 w-4" />
			{/if}
			Search
		</Button.Root>
	</div>

	<!-- Loading state -->
	{#if loading && tests.length === 0}
		<div class="flex justify-center py-8">
			<LoadingSpinner size="lg" />
		</div>
	{:else if error}
		<Alert.Root variant="destructive">
			<Alert.Description>{error}</Alert.Description>
		</Alert.Root>
	{:else if tests.length === 0}
		<div class="text-center py-8 text-gray-500">No tests found</div>
	{:else}
		<!-- Test List -->
		<div class="space-y-3">
			{#each tests as test (test.id)}
				<TestCard
					{test}
					onRun={onSelectTest ? () => onSelectTest(test.id) : undefined}
					onDelete={() => handleDelete(test.id)}
					{loading}
				/>
			{/each}
		</div>

		<!-- Pagination -->
		<div class="flex justify-between items-center pt-4 border-t border-gray-200">
			<div class="text-sm text-gray-600">
				Showing {tests.length} of {total} tests
			</div>
			<div class="flex gap-2">
				<Button.Root
					variant="secondary"
					size="sm"
					onclick={handlePrevious}
					disabled={!hasPrevious || loading}
				>
					Previous
				</Button.Root>
				<Button.Root
					variant="secondary"
					size="sm"
					onclick={handleNext}
					disabled={!hasNext || loading}
				>
					Next
				</Button.Root>
			</div>
		</div>
	{/if}
</div>
