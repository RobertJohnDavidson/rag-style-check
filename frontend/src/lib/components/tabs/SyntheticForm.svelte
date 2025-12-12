<script lang="ts">
	import type { ExpectedViolation, Test } from '$lib/types';
	import { Input, Button, Alert } from '$lib/components/ui';
	import { TestPreview } from '$lib/components/tests';
	import { SyntheticCountSchema } from '$lib/schemas';
	import { generateTests as apiGenerateTests, createTest as apiCreateTest } from '$lib/api';

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
		<Input
			label="Number of Tests to Generate"
			type="number"
			bind:value={syntheticCount}
			min={1}
			max={20}
			error={countError}
			disabled={loading}
			required
			autofocus
		/>

		<p class="text-xs text-gray-500">Generate between 1 and 20 synthetic tests</p>

		<Button
			variant="primary"
			onclick={handleGenerate}
			{loading}
			disabled={!syntheticCount}
			class="w-full"
		>
			Generate {syntheticCount} Synthetic Test{syntheticCount > 1 ? 's' : ''}
		</Button>
	{:else}
		<Alert variant="info">
			<strong>Generated Tests - Review and Save</strong><br />
			{generatedTests.length} test(s) generated. Review and save individually.
		</Alert>

		<div class="space-y-4">
			{#each generatedTests as test, idx (idx)}
				<div>
					<h4 class="font-semibold text-gray-900 mb-3">Test {idx + 1}</h4>
					<TestPreview test={generatedTests[idx]} onSave={() => handleSaveTest(idx)} {loading} />
				</div>
			{/each}

			<Button variant="secondary" onclick={handleCancelAll} disabled={loading} class="w-full">
				Cancel All
			</Button>
		</div>
	{/if}

	{#if error}
		<Alert variant="error">{error}</Alert>
	{/if}

	{#if success}
		<Alert variant="success">{success}</Alert>
	{/if}
</div>
