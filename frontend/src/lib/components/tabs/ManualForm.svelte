<script lang="ts">
	import type { ExpectedViolation } from '$lib/types';
	import { Input, Textarea, Button, Alert, Label } from '$lib/components/ui';
	import { ViolationForm, ViolationList } from '$lib/components/forms';
	import { TestInputSchema } from '$lib/schemas';
	import { createTest as apiCreateTest } from '$lib/api';
	import type { ExpectedViolationInput } from '$lib/schemas';
	import { LoaderCircle, Info } from '@lucide/svelte';

	interface Props {
		onUnsavedChanges?: (hasChanges: boolean) => void;
		onRegisterReset?: (resetFn: () => void) => void;
	}

	let { onUnsavedChanges, onRegisterReset }: Props = $props();

	// Local form state
	let label = $state('');
	let text = $state('');
	let notes = $state('');
	let violations = $state<ExpectedViolation[]>([]);
	let loading = $state(false);
	let error = $state('');
	let success = $state('');

	// Local error tracking
	let validationErrors = $state<Record<string, string>>({});

	// Track unsaved changes
	$effect(() => {
		const hasChanges = label !== '' || text !== '' || violations.length > 0;
		onUnsavedChanges?.(hasChanges);
	});

	// Register reset function
	$effect(() => {
		if (onRegisterReset) {
			onRegisterReset(resetForm);
		}
	});

	function addViolation(violation: ExpectedViolationInput) {
		violations = [...violations, violation];
		clearError('violations');
	}

	function removeViolation(index: number) {
		violations = violations.filter((_, i) => i !== index);
	}

	function resetForm() {
		label = '';
		text = '';
		notes = '';
		violations = [];
		error = '';
		success = '';
		validationErrors = {};
	}

	async function handleCreateTest() {
		// Build test input
		const testInput = {
			label,
			text,
			expected_violations: violations,
			generation_method: 'manual' as const,
			...(notes ? { notes } : {})
		};

		// Validate
		const result = TestInputSchema.safeParse(testInput);
		if (!result.success) {
			const newErrors: Record<string, string> = {};
			result.error.issues.forEach(err => {
				const field = err.path[0] as string;
				newErrors[field] = err.message;
			});
			validationErrors = newErrors;
			error = 'Please fix validation errors';
			return;
		}

		// Clear errors
		validationErrors = {};
		error = '';
		loading = true;

		// API call
		const response = await apiCreateTest(result.data);

		loading = false;

		if (response.error) {
			error = response.error;
		} else {
			success = 'Test created successfully!';
			// Reset form after 2 seconds
			setTimeout(() => {
				resetForm();
			}, 2000);
		}
	}

	function clearError(field: string) {
		if (validationErrors[field]) {
			const { [field]: _, ...rest } = validationErrors;
			validationErrors = rest;
		}
	}
</script>

<div class="space-y-4">
	<div class="space-y-2">
		<Label.Root>Test Label</Label.Root>
		<Input.Root
			type="text"
			bind:value={label}
			placeholder="e.g., Cabinet capitalization test"
			disabled={loading}
			required
		/>
		{#if validationErrors.label}
			<p class="text-xs text-destructive">{validationErrors.label}</p>
		{/if}
	</div>

	<div class="space-y-2">
		<Label.Root>Test Text</Label.Root>
		<Textarea.Root
			bind:value={text}
			placeholder="Enter the text to test..."
			rows={6}
			disabled={loading}
			required
		/>
		{#if validationErrors.text}
			<p class="text-xs text-destructive">{validationErrors.text}</p>
		{/if}
	</div>

	<div class="space-y-2">
		<Label.Root class="text-base">Expected Violations</Label.Root>

		<ViolationList
			{violations}
			onRemove={removeViolation}
			showRemove={true}
			emptyMessage="No violations added yet. Add at least one violation below."
			class="mb-3"
		/>

		<ViolationForm onAdd={addViolation} disabled={loading} />

		{#if validationErrors.expected_violations}
			<p class="text-xs text-destructive mt-2">{validationErrors.expected_violations}</p>
		{/if}
	</div>

	<div class="space-y-2">
		<Label.Root>Notes (Optional)</Label.Root>
		<Textarea.Root
			bind:value={notes}
			placeholder="Additional notes..."
			rows={3}
			disabled={loading}
		/>
		{#if validationErrors.notes}
			<p class="text-xs text-destructive">{validationErrors.notes}</p>
		{/if}
	</div>

	<Button.Root
		onclick={handleCreateTest}
		disabled={loading || !label || !text || violations.length === 0}
		class="w-full"
	>
		{#if loading}
			<LoaderCircle class="mr-2 h-4 w-4 animate-spin" />
		{/if}
		Create Test
	</Button.Root>

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
