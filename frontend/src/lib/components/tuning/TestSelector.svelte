<script lang="ts">
	import { onMount } from 'svelte';
	import { Input } from '$lib/components/ui';
	import { LoaderCircle, Search } from '@lucide/svelte';
	import { loadTests } from '$lib/api';
	import type { Test } from '$lib/types';

	interface Props {
		onSelect: (test: Test) => void;
	}

	let { onSelect }: Props = $props();

	let tests = $state<Test[]>([]);
	let loading = $state(false);
	let search = $state('');
	let debounceTimer: any;

	async function fetchTests() {
		loading = true;
		const { data, error } = await loadTests({ search, page_size: 10 });
		if (data) {
			tests = data.tests;
		}
		loading = false;
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
	<div class="relative">
		<Search class="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
		<Input.Root
			bind:value={search}
			placeholder="Search tests by label or text..."
			class="bg-background pl-9"
		/>
	</div>

	{#if loading}
		<div class="flex justify-center py-8">
			<LoaderCircle class="h-6 w-6 animate-spin text-muted-foreground" />
		</div>
	{:else if tests.length > 0}
		<div class="grid grid-cols-1 gap-2 max-h-64 overflow-y-auto pr-2 custom-scrollbar">
			{#each tests as test}
				<button
					onclick={() => onSelect(test)}
					class="w-full text-left p-3 rounded-lg border border-border hover:bg-accent/50 transition-all group"
				>
					<div class="font-bold text-sm text-foreground group-hover:text-primary">{test.label}</div>
					<div class="text-xs text-muted-foreground truncate">{test.text}</div>
				</button>
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
