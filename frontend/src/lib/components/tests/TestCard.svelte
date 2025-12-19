<script lang="ts">
	import type { Test } from '$lib/types';
	import { Card, Badge, Button } from '$lib/components/ui';
	import { LoaderCircle } from '@lucide/svelte';

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

	// Map generation method to badge variant
	const badgeVariant = $derived(() => {
		switch (test.generation_method) {
			case 'manual': return 'outline';
			case 'article': return 'secondary';
			case 'synthetic': return 'default';
			default: return 'outline';
		}
	});
</script>

<Card.Root class="hover:bg-accent/50 transition-colors {className}">
	<Card.Content class="flex items-start justify-between pt-6">
		<div class="flex-1">
			<div class="flex items-center gap-2 mb-2">
				<h3 class="font-bold text-gray-900">{test.label}</h3>
				<Badge.Root variant={badgeVariant()}>{test.generation_method}</Badge.Root>
			</div>

			<p class="text-sm text-gray-600 mb-2">{truncatedText}</p>

			<details class="mt-2">
				<summary class="flex gap-4 text-xs text-gray-500 cursor-pointer hover:text-gray-700">
					<span>Violations: {test.expected_violations.length}</span>
					<span>{formattedDate}</span>
				</summary>
				<div class="mt-2 pl-4 space-y-2">
					{#each test.expected_violations as violation}
						<div class="text-xs border-l-2 border-primary/30 pl-3 py-1">
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
									class="text-primary hover:underline"
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
				<Button.Root size="sm" onclick={onRun} disabled={loading}>
					{#if loading}
						<LoaderCircle class="mr-2 h-3 w-3 animate-spin" />
					{/if}
					Run
				</Button.Root>
			{/if}

			{#if onDelete}
				<Button.Root variant="destructive" size="sm" onclick={onDelete} disabled={loading}>
					{#if loading}
						<LoaderCircle class="mr-2 h-3 w-3 animate-spin" />
					{/if}
					Delete
				</Button.Root>
			{/if}
		</div>
	</Card.Content>
</Card.Root>
