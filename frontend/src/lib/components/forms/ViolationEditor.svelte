<script lang="ts">
	import { Input, Button, Label } from '$lib/components/ui';
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
	<div class="space-y-1">
		<Label.Root>Rule name</Label.Root>
		<Input.Root
			type="text"
			bind:value={violation.rule}
			onblur={() => validateField('rule')}
			required
		/>
		{#if errors.rule}
			<p class="text-xs text-destructive">{errors.rule}</p>
		{/if}
	</div>

	<div class="space-y-1">
		<Label.Root>Violating text snippet</Label.Root>
		<Input.Root
			type="text"
			bind:value={violation.text}
			onblur={() => validateField('text')}
			required
		/>
		{#if errors.text}
			<p class="text-xs text-destructive">{errors.text}</p>
		{/if}
	</div>

	<div class="space-y-1">
		<Label.Root>Reason (optional)</Label.Root>
		<Input.Root type="text" bind:value={violation.reason} onblur={() => validateField('reason')} />
		{#if errors.reason}
			<p class="text-xs text-destructive">{errors.reason}</p>
		{/if}
	</div>

	<div class="space-y-1">
		<Label.Root>Link to rule</Label.Root>
		<Input.Root
			type="url"
			bind:value={violation.link}
			onblur={() => validateField('link')}
			required
		/>
		{#if errors.link}
			<p class="text-xs text-destructive">{errors.link}</p>
		{/if}
	</div>

	{#if showRemove && onRemove}
		<Button.Root variant="destructive" size="sm" onclick={onRemove} class="w-full">
			Remove Violation
		</Button.Root>
	{/if}
</div>
