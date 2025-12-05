<script lang="ts">
	import type { Test } from '$lib/types';
	import { Card, Badge, Button } from '$lib/components/ui';

	interface Props {
		test: Test;
		onRun?: () => void;
		onDelete?: () => void;
		loading?: boolean;
		class?: string;
	}

	let { test, onRun, onDelete, loading = false, class: className = '' }: Props = $props();

	// Truncate text for preview
	const truncatedText = $derived(
		test.text.length > 150 ? test.text.substring(0, 150) + '...' : test.text
	);

	const formattedDate = $derived(new Date(test.created_at).toLocaleDateString());
</script>

<Card hover={true} class="flex items-start justify-between {className}">
	<div class="flex-1">
		<div class="flex items-center gap-2 mb-2">
			<h3 class="font-bold text-gray-900">{test.label}</h3>
			<Badge variant={test.generation_method}>{test.generation_method}</Badge>
		</div>
		
		<p class="text-sm text-gray-600 mb-2">{truncatedText}</p>
		
		<details class="mt-2">
			<summary class="flex gap-4 text-xs text-gray-500 cursor-pointer hover:text-gray-700">
				<span>Violations: {test.expected_violations.length}</span>
				<span>{formattedDate}</span>
			</summary>
			<div class="mt-2 pl-4 space-y-2">
				{#each test.expected_violations as violation}
					<div class="text-xs border-l-2 border-gray-300 pl-3 py-1">
						<p class="font-semibold text-gray-700">{violation.rule}</p>
						<p class="text-gray-600">"{violation.text}"</p>
						{#if violation.reason}
							<p class="italic text-gray-500">Reason: {violation.reason}</p>
						{/if}
						{#if violation.link}
							<a 
								href={violation.link} 
								target="_blank" 
								rel="noopener noreferrer" 
								class="text-indigo-600 hover:text-indigo-800"
							>
								View Rule →
							</a>
						{/if}
						
					</div>
				{/each}
			</div>
		</details>
		
		{#if test.notes}
			<p class="text-xs text-gray-500 mt-2 italic">{test.notes}</p>
		{/if}
	</div>
	
	<div class="flex gap-2 ml-4">
		{#if onRun}
			<Button
				variant="primary"
				size="sm"
				onclick={onRun}
				{loading}
			>
				Run
			</Button>
		{/if}
		
		{#if onDelete}
			<Button
				variant="danger"
				size="sm"
				onclick={onDelete}
				{loading}
			>
				Delete
			</Button>
		{/if}
	</div>
</Card>
