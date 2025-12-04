<script lang="ts">
	import { Input, Button } from '$lib/components/ui';
	import { ExpectedViolationSchema } from '$lib/schemas';
	import type { ExpectedViolationInput } from '$lib/schemas';

	interface Props {
		onAdd: (violation: ExpectedViolationInput) => void;
		disabled?: boolean;
	}

	let { onAdd, disabled = false }: Props = $props();

	// Form state
	let rule = $state('');
	let text = $state('');
	let reason = $state('');
	let link = $state('');

	// Error state
	let errors = $state<Record<string, string>>({});

	// Auto-focus element
	let ruleInput: HTMLInputElement | undefined = $state();

	function resetForm() {
		rule = '';
		text = '';
		reason = '';
		link = '';
		errors = {};
		ruleInput?.focus();
	}

	function handleAdd() {
		// Build violation object
		const violation: ExpectedViolationInput = {
			rule,
			text,
			link,
			...(reason ? { reason } : {})
		};

		// Validate with Zod
		const result = ExpectedViolationSchema.safeParse(violation);

		if (!result.success) {
			// Extract errors
			const newErrors: Record<string, string> = {};
			result.error.issues.forEach(err => {
				const field = err.path[0] as string;
				newErrors[field] = err.message;
			});
			errors = newErrors;
			return;
		}

		// Call callback
		onAdd(result.data);

		// Reset form
		resetForm();
	}

	function clearError(field: string) {
		const { [field]: _, ...rest } = errors;
		errors = rest;
	}
</script>

<div class="border border-gray-200 rounded-lg p-4 space-y-3">
	<Input
		label="Rule name"
		type="text"
		bind:value={rule}
		placeholder="e.g., cabinet_capitalization"
		error={errors.rule}
		{disabled}
		required
		autofocus
	/>
	
	<Input
		label="Violating text snippet"
		type="text"
		bind:value={text}
		placeholder="The exact text that violates the rule"
		error={errors.text}
		{disabled}
		required
	/>
	
	<Input
		label="Reason (optional)"
		type="text"
		bind:value={reason}
		placeholder="Why this is a violation"
		error={errors.reason}
		{disabled}
	/>
	
	<Input
		label="Link to rule"
		type="url"
		bind:value={link}
		placeholder="https://..."
		error={errors.link}
		{disabled}
		required
	/>
	
	<Button
		variant="secondary"
		onclick={handleAdd}
		{disabled}
		class="w-full"
	>
		Add Violation
	</Button>
</div>
