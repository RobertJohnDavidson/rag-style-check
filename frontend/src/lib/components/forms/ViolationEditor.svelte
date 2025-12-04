<script lang="ts">
	import { Input, Button } from '$lib/components/ui';
	import { ExpectedViolationSchema } from '$lib/schemas';
	import type { ExpectedViolation } from '$lib/types';

	interface Props {
		violation: ExpectedViolation;
		onRemove?: () => void;
		showRemove?: boolean;
		class?: string;
	}

	let { 
		violation = $bindable(), 
		onRemove, 
		showRemove = false,
		class: className = ''
	}: Props = $props();

	// Validation errors (only shown on blur)
	let errors = $state<Record<string, string>>({});

	function validateField(field: keyof ExpectedViolation) {
		const result = ExpectedViolationSchema.safeParse(violation);
		
		if (!result.success) {
			const fieldError = result.error.issues.find(err => err.path[0] === field);
			if (fieldError) {
				errors = { ...errors, [field]: fieldError.message };
			} else {
				const { [field]: _, ...rest } = errors;
				errors = rest;
			}
		} else {
			const { [field]: _, ...rest } = errors;
			errors = rest;
		}
	}
</script>

<div class="border border-gray-200 rounded-lg p-4 space-y-3 {className}">
	<Input
		label="Rule name"
		type="text"
		bind:value={violation.rule}
		error={errors.rule}
		required
	/>
	
	<Input
		label="Violating text snippet"
		type="text"
		bind:value={violation.text}
		error={errors.text}
		required
	/>
	
	<Input
		label="Reason (optional)"
		type="text"
		value={violation.reason ?? ''}
		error={errors.reason}
	/>
	
	<Input
		label="Link to rule"
		type="url"
		bind:value={violation.link}
		error={errors.link}
		required
	/>
	
	{#if showRemove && onRemove}
		<Button
			variant="danger"
			size="sm"
			onclick={onRemove}
			class="w-full"
		>
			Remove Violation
		</Button>
	{/if}
</div>
