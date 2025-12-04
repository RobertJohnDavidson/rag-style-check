<script lang="ts">
	import type { Test } from '$lib/types';
	import { Card, Button } from '$lib/components/ui';
	import { ViolationEditor } from '$lib/components/forms';

	interface Props {
		test: Test;
		onSave?: () => void;
		onCancel?: () => void;
		loading?: boolean;
		class?: string;
	}

	let { 
		test, 
		onSave, 
		onCancel,
		loading = false,
		class: className = ''
	}: Props = $props();

	function removeViolation(index: number) {
		test.expected_violations = test.expected_violations.filter((_, i) => i !== index);
	}
</script>

<Card class={className}>
	<div class="space-y-4">
		<!-- Label -->
		<div>
			<label class="block text-xs font-medium text-gray-600 mb-1">Label</label>
			<input
			type="text"
			bind:value={test.label}
			class="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#CC0000]"
			disabled={loading}
			/>
		</div>

		<!-- Text -->
		<div>
			<label class="block text-xs font-medium text-gray-600 mb-1">Text</label>
			<textarea
			bind:value={test.text}
			rows="4"
			class="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#CC0000] text-sm"
			disabled={loading}
			></textarea>
		</div>

		<!-- Expected Violations -->
		<div>
			<label class="block text-xs font-medium text-gray-600 mb-2">Expected Violations</label>
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
		{#if test.notes}
			<div>
				<label class="block text-xs font-medium text-gray-600 mb-1">Notes</label>
				<textarea
				bind:value={test.notes}
				rows="2"
				class="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-[#CC0000] text-sm"
				disabled={loading}
				></textarea>
			</div>
		{/if}

		<!-- Actions -->
		{#if onSave || onCancel}
			<div class="flex gap-3 pt-2">
				{#if onSave}
					<Button
						variant="success"
						onclick={onSave}
						{loading}
						class="flex-1"
					>
						Save Test
					</Button>
				{/if}
				
				{#if onCancel}
					<Button
						variant="secondary"
						onclick={onCancel}
						{loading}
					>
						Cancel
					</Button>
				{/if}
			</div>
		{/if}
	</div>
</Card>
