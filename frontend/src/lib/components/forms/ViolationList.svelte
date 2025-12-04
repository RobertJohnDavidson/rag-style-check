<script lang="ts">
	import type { ExpectedViolation } from '$lib/types';
	import ViolationCard from './ViolationCard.svelte';

	interface Props {
		violations: ExpectedViolation[];
		onRemove?: (index: number) => void;
		showRemove?: boolean;
		emptyMessage?: string;
		class?: string;
	}

	let { 
		violations, 
		onRemove, 
		showRemove = false,
		emptyMessage = 'No violations added yet.',
		class: className = ''
	}: Props = $props();

	function handleRemove(index: number) {
		if (onRemove) {
			onRemove(index);
		}
	}
</script>

<div class="space-y-3 {className}">
	{#if violations.length === 0}
		<p class="text-sm text-gray-500 italic">{emptyMessage}</p>
	{:else}
		{#each violations as violation, i (i)}
			<ViolationCard
				{violation}
				{showRemove}
				onRemove={() => handleRemove(i)}
			/>
		{/each}
	{/if}
</div>
