<script lang="ts">
	import type { Test } from '$lib/types';
	import { Card, Button, Label, Input, Textarea } from '$lib/components/ui';
	import { ViolationEditor } from '$lib/components/forms';
	import { LoaderCircle, Save } from '@lucide/svelte';

	interface Props {
		test: Test;
		onSave?: () => void;
		onCancel?: () => void;
		loading?: boolean;
		class?: string;
	}

	let { 
		test = $bindable(), 
		onSave, 
		onCancel,
		loading = false,
		class: className = ''
	}: Props = $props();

	function removeViolation(index: number) {
		test.expected_violations = test.expected_violations.filter((_, i) => i !== index);
	}
</script>

<Card.Root class={className}>
	<Card.Content class="pt-6">
		<div class="space-y-4">
			<!-- Label -->
			<div class="space-y-1.5">
				<Label.Root>Label</Label.Root>
				<Input.Root type="text" bind:value={test.label} disabled={loading} />
			</div>

			<!-- Text -->
			<div class="space-y-1.5">
				<Label.Root>Text</Label.Root>
				<Textarea.Root bind:value={test.text} rows={4} class="text-sm" disabled={loading} />
			</div>

			<!-- Expected Violations -->
			<div class="space-y-2">
				<Label.Root class="text-base">Expected Violations</Label.Root>
				<div class="space-y-3">
					{#each test.expected_violations as violation, i (i)}
						<ViolationEditor
							bind:violation={test.expected_violations[i]}
							onRemove={() => removeViolation(i)}
							showRemove={true}
						/>
					{/each}
				</div>
			</div>

			<!-- Notes (if present) -->
			{#if test.notes !== undefined}
				<div class="space-y-1.5">
					<Label.Root>Notes</Label.Root>
					<Textarea.Root bind:value={test.notes} rows={2} class="text-sm" disabled={loading} />
				</div>
			{/if}

			<!-- Actions -->
			{#if onSave || onCancel}
				<div class="flex gap-3 pt-2">
					{#if onSave}
						<Button.Root
							onclick={onSave}
							disabled={loading}
							class="flex-1 bg-green-600 hover:bg-green-700 text-white"
						>
							{#if loading}
								<LoaderCircle class="mr-2 h-4 w-4 animate-spin" />
							{/if}
							Save Test
						</Button.Root>
					{/if}

					{#if onCancel}
						<Button.Root variant="secondary" onclick={onCancel} disabled={loading}>
							Cancel
						</Button.Root>
					{/if}
				</div>
			{/if}
		</div>
	</Card.Content>
</Card.Root>
