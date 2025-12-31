<script lang="ts">
	import { onMount } from 'svelte';
	import { Input } from '$lib/components/ui';
	import { Trash2, LoaderCircle, Search } from '@lucide/svelte';
	import { loadTests, deleteTest } from '$lib/api';
	import type { Test } from '$lib/types';

	interface Props {
		onSelect?: (test: Test) => void;
		onSelectionChange?: (selectedIds: string[]) => void;
		multiSelect?: boolean;
		disabled?: boolean;
	}

	let { 
		onSelect, 
		onSelectionChange, 
		multiSelect = false,
		disabled = false
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

	async function handleDelete(id: string, event: MouseEvent) {
		event.stopPropagation();
		if (!confirm('Are you sure you want to delete this test?')) return;
		
		const { error } = await deleteTest(id);
		if (error) {
			alert('Failed to delete test: ' + error);
		} else {
			tests = tests.filter(t => t.id !== id);
			selectedIds = selectedIds.filter(sid => sid !== id);
			onSelectionChange?.(selectedIds);
		}
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
				{disabled}
			/>
		</div>
		<button
			type="button"
			onclick={fetchTests}
			class="inline-flex items-center gap-1 px-3 py-2 rounded-md border border-border text-xs font-semibold text-muted-foreground hover:text-foreground hover:border-primary transition-colors"
			disabled={loading || disabled}
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
		<div class="grid grid-cols-1 gap-3 max-h-[600px] overflow-y-auto pr-2 custom-scrollbar">
			{#each tests as test}
				<div class="flex items-center gap-2 group">
					{#if multiSelect}
						<input
							type="checkbox"
							checked={selectedIds.includes(test.id)}
							onchange={() => !disabled && toggleSelection(test.id)}
							class="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary accent-primary cursor-pointer disabled:opacity-50"
							{disabled}
						/>
					{/if}
					<button
						onclick={() => !disabled && (multiSelect ? toggleSelection(test.id) : onSelect?.(test))}
						class="flex-1 text-left p-4 rounded-lg border border-border hover:bg-accent/50 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
						class:bg-accent={selectedIds.includes(test.id)}
						class:border-primary={selectedIds.includes(test.id)}
						{disabled}
					>
						<div
							class="font-bold text-base text-foreground group-hover:text-primary transition-colors"
						>
							{test.label}
						</div>
						<div class="text-xs text-muted-foreground line-clamp-2">{test.text}</div>
					</button>

					<button
						type="button"
						onclick={(e) => handleDelete(test.id, e)}
						{disabled}
						class="p-2 text-muted-foreground hover:text-destructive hover:bg-destructive/10 rounded-md transition-all opacity-0 group-hover:opacity-100 disabled:hidden"
						title="Delete Test"
					>
						<Trash2 class="h-4 w-4" />
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
