<script lang="ts">
	import { onMount } from 'svelte';
	import { Input } from '$lib/components/ui';
	import { LoaderCircle, Search } from '@lucide/svelte';
	import { loadTests } from '$lib/api';
	import type { Test } from '$lib/types';

	interface Props {
		onSelect?: (test: Test) => void;
		onSelectionChange?: (selectedIds: string[]) => void;
		multiSelect?: boolean;
	}

	let { 
		onSelect, 
		onSelectionChange, 
		multiSelect = false 
	}: Props = $props();

	let tests = $state<Test[]>([]);
	let selectedIds = $state<string[]>([]);
	let loading = $state(false);
	let search = $state('');
	let debounceTimer: any;

	async function fetchTests() {
		loading = true;
		const { data, error } = await loadTests({ search, page_size: 20 });
		if (data) {
			tests = data.tests;
		}
		loading = false;
	}

	function toggleSelection(testId: string) {
		if (selectedIds.includes(testId)) {
			selectedIds = selectedIds.filter(id => id !== testId);
		} else {
			selectedIds = [...selectedIds, testId];
		}
		onSelectionChange?.(selectedIds);
	}

	$effect(() => {
		if (search !== undefined) {
			clearTimeout(debounceTimer);
			debounceTimer = setTimeout(fetchTests, 300);
		}
	});

	onMount(fetchTests);
</script>

<div class="space-y-4">
	<div class="flex gap-2 items-center">
		<div class="relative flex-1">
			<Search class="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
			<Input.Root
				bind:value={search}
				placeholder="Search tests by label or text..."
				class="bg-background pl-9"
			/>
		</div>
		<button
			type="button"
			onclick={fetchTests}
			class="inline-flex items-center gap-1 px-3 py-2 rounded-md border border-border text-xs font-semibold text-muted-foreground hover:text-foreground hover:border-primary transition-colors"
			disabled={loading}
		>
			{#if loading}
				<LoaderCircle class="h-4 w-4 animate-spin" />
			{:else}
				↻ Refresh
			{/if}
		</button>
	</div>

	{#if loading}
		<div class="flex justify-center py-8">
			<LoaderCircle class="h-6 w-6 animate-spin text-muted-foreground" />
		</div>
	{:else if tests.length > 0}
		<div class="grid grid-cols-1 gap-2 max-h-80 overflow-y-auto pr-2 custom-scrollbar">
			{#each tests as test}
				<div class="flex items-center gap-2 group">
					{#if multiSelect}
						<input
							type="checkbox"
							checked={selectedIds.includes(test.id)}
							onchange={() => toggleSelection(test.id)}
							class="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary accent-primary cursor-pointer"
						/>
					{/if}
					<button
						onclick={() => (multiSelect ? toggleSelection(test.id) : onSelect?.(test))}
						class="flex-1 text-left p-3 rounded-lg border border-border hover:bg-accent/50 transition-all"
						class:bg-accent={selectedIds.includes(test.id)}
						class:border-primary={selectedIds.includes(test.id)}
					>
						<div
							class="font-bold text-sm text-foreground group-hover:text-primary transition-colors"
						>
							{test.label}
						</div>
						<div class="text-xs text-muted-foreground truncate">{test.text}</div>
					</button>
				</div>
			{/each}
		</div>
	{:else}
		<div class="text-center py-8 text-muted-foreground text-sm">No tests found.</div>
	{/if}
</div>

<style>
	.custom-scrollbar::-webkit-scrollbar {
		width: 4px;
	}
	.custom-scrollbar::-webkit-scrollbar-track {
		background: transparent;
	}
	.custom-scrollbar::-webkit-scrollbar-thumb {
		background: hsl(var(--muted-foreground) / 0.3);
		border-radius: 10px;
	}
</style>
