<script lang="ts">
	import type { ExpectedViolation } from '$lib/types';
	import { Input, Textarea, Button, Alert } from '$lib/components/ui';
	import { ViolationForm, ViolationList } from '$lib/components/forms';
	import { TestInputSchema } from '$lib/schemas';
	import { createTest as apiCreateTest } from '$lib/api';
	import type { ExpectedViolationInput } from '$lib/schemas';

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
	<Input
		label="Test Label"
		type="text"
		bind:value={label}
		placeholder="e.g., Cabinet capitalization test"
		error={validationErrors.label}
		disabled={loading}
		required
		autofocus
	/>

	<Textarea
		label="Test Text"
		bind:value={text}
		placeholder="Enter the text to test..."
		rows={6}
		error={validationErrors.text}
		disabled={loading}
		required
	/>

	<div>
		<label class="block text-sm font-semibold text-gray-700 mb-2">Expected Violations</label>
		
		<ViolationList
			violations={violations}
			onRemove={removeViolation}
			showRemove={true}
			emptyMessage="No violations added yet. Add at least one violation below."
			class="mb-3"
		/>

		<ViolationForm
			onAdd={addViolation}
			disabled={loading}
		/>
		
		{#if validationErrors.expected_violations}
			<p class="text-sm text-red-600 mt-2">{validationErrors.expected_violations}</p>
		{/if}
	</div>

	<Textarea
		label="Notes (Optional)"
		bind:value={notes}
		placeholder="Additional notes..."
		rows={3}
		error={validationErrors.notes}
		disabled={loading}
	/>

	<Button
		variant="primary"
		onclick={handleCreateTest}
		loading={loading}
		disabled={!label || !text || violations.length === 0}
		class="w-full"
	>
		Create Test
	</Button>

	{#if error}
		<Alert variant="error">{error}</Alert>
	{/if}

	{#if success}
		<Alert variant="success">{success}</Alert>
	{/if}
</div>
