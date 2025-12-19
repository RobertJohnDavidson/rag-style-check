<script lang="ts">
	import type { ExpectedViolation, Test } from '$lib/types';
	import { Input, Button, Alert, Label } from '$lib/components/ui';
	import { TestPreview } from '$lib/components/tests';
	import { SyntheticCountSchema } from '$lib/schemas';
	import { generateTests as apiGenerateTests, createTest as apiCreateTest } from '$lib/api';
	import { LoaderCircle, Info } from '@lucide/svelte';

	interface Props {
		onUnsavedChanges?: (hasChanges: boolean) => void;
		onRegisterReset?: (resetFn: () => void) => void;
	}

	let { onUnsavedChanges, onRegisterReset }: Props = $props();

	// Local form state
	let syntheticCount = $state(5);
	let generatedTests = $state<Array<Test>>([]);
	let showPreview = $state(false);
	let loading = $state(false);
	let error = $state('');
	let success = $state('');
	let countError = $state('');

	// Track unsaved changes
	$effect(() => {
		const hasChanges = showPreview && generatedTests.length > 0;
		onUnsavedChanges?.(hasChanges);
	});

	// Register reset function
	$effect(() => {
		if (onRegisterReset) {
			onRegisterReset(resetForm);
		}
	});

	function resetForm() {
		syntheticCount = 5;
		generatedTests = [];
		showPreview = false;
		error = '';
		success = '';
		countError = '';
	}

	async function handleGenerate() {
		// Validate count
		const result = SyntheticCountSchema.safeParse(syntheticCount);
		if (!result.success) {
			countError = result.error.issues[0].message;
			return;
		}

		countError = '';
		error = '';
		loading = true;
		showPreview = false;

		const response = await apiGenerateTests({ 
			method: 'synthetic',
			count: result.data
		});

		loading = false;

		if (response.error) {
			error = response.error;
		} else if (response.data && response.data.tests.length > 0) {
			generatedTests = response.data.tests.map(t => ({
				id: '',
				...t,
				generation_method: 'synthetic' as const,
				created_at: new Date().toISOString()
			}));
			showPreview = true;
		} else {
			error = 'No tests generated';
		}
	}

	async function handleSaveTest(index: number) {
		const test = generatedTests[index];
		
		const testInput = {
			label: test.label,
			text: test.text,
			expected_violations: test.expected_violations,
			generation_method: 'synthetic' as const,
			...(test.notes ? { notes: test.notes } : {})
		};

		loading = true;
		error = '';

		const response = await apiCreateTest(testInput);

		loading = false;

		if (response.error) {
			error = response.error;
		} else {
			// Remove saved test from array
			generatedTests = generatedTests.filter((_, i) => i !== index);
			
			// Show success message
			success = 'Test saved successfully!';
			setTimeout(() => {
				success = '';
				
				// If no more tests, reset
				if (generatedTests.length === 0) {
					resetForm();
				}
			}, 2000);
		}
	}

	function handleCancelAll() {
		resetForm();
	}
</script>

<div class="space-y-4">
	{#if !showPreview}
		<div class="space-y-2">
			<Label.Root>Number of Tests to Generate</Label.Root>
			<Input.Root
				type="number"
				bind:value={syntheticCount}
				min={1}
				max={20}
				disabled={loading}
				required
			/>
			{#if countError}
				<p class="text-xs text-destructive">{countError}</p>
			{:else}
				<p class="text-xs text-gray-500">Generate between 1 and 20 synthetic tests</p>
			{/if}
		</div>

		<Button.Root onclick={handleGenerate} disabled={loading || !syntheticCount} class="w-full">
			{#if loading}
				<LoaderCircle class="mr-2 h-4 w-4 animate-spin" />
			{/if}
			Generate {syntheticCount} Synthetic Test{syntheticCount > 1 ? 's' : ''}
		</Button.Root>
	{:else}
		<Alert.Root>
			<Info class="h-4 w-4" />
			<Alert.Title>Generated Tests - Review and Save</Alert.Title>
			<Alert.Description>
				{generatedTests.length} test(s) generated. Review and save individually.
			</Alert.Description>
		</Alert.Root>

		<div class="space-y-4">
			{#each generatedTests as test, idx (idx)}
				<div>
					<h4 class="font-semibold text-gray-900 mb-3">Test {idx + 1}</h4>
					<TestPreview test={generatedTests[idx]} onSave={() => handleSaveTest(idx)} {loading} />
				</div>
			{/each}

			<Button.Root variant="secondary" onclick={handleCancelAll} disabled={loading} class="w-full">
				Cancel All
			</Button.Root>
		</div>
	{/if}

	{#if error}
		<Alert.Root variant="destructive">
			<Alert.Description>{error}</Alert.Description>
		</Alert.Root>
	{/if}

	{#if success}
		<Alert.Root class="bg-green-50 text-green-700 border-green-200">
			<Alert.Description>{success}</Alert.Description>
		</Alert.Root>
	{/if}
</div>
