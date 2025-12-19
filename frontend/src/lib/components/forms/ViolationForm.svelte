<script lang="ts">
	import { Input, Button, Label } from '$lib/components/ui';
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

	function resetForm() {
		rule = '';
		text = '';
		reason = '';
		link = '';
		errors = {};
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
</script>

<div class="border border-gray-200 rounded-lg p-4 space-y-3">
	<div class="space-y-1">
		<Label.Root>Rule name</Label.Root>
		<Input.Root
			type="text"
			bind:value={rule}
			placeholder="e.g., cabinet_capitalization"
			{disabled}
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
			bind:value={text}
			placeholder="The exact text that violates the rule"
			{disabled}
			required
		/>
		{#if errors.text}
			<p class="text-xs text-destructive">{errors.text}</p>
		{/if}
	</div>

	<div class="space-y-1">
		<Label.Root>Reason (optional)</Label.Root>
		<Input.Root type="text" bind:value={reason} placeholder="Why this is a violation" {disabled} />
		{#if errors.reason}
			<p class="text-xs text-destructive">{errors.reason}</p>
		{/if}
	</div>

	<div class="space-y-1">
		<Label.Root>Link to rule</Label.Root>
		<Input.Root type="url" bind:value={link} placeholder="https://..." {disabled} required />
		{#if errors.link}
			<p class="text-xs text-destructive">{errors.link}</p>
		{/if}
	</div>

	<Button.Root variant="secondary" onclick={handleAdd} {disabled} class="w-full">
		Add Violation
	</Button.Root>
</div>
