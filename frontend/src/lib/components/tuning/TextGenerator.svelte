<script lang="ts">
	import { Button, Input, Label, Select } from '$lib/components/ui';
	import { generateTests } from '$lib/api';
	import { LoaderCircle, Sparkles } from '@lucide/svelte';
	
	interface Props {
		onGenerated: (text: string) => void;
	}

	let { onGenerated }: Props = $props();

	let method = $state('synthetic');
	let articleUrl = $state('');
	let count = $state(1);
	let loading = $state(false);
	let error = $state('');

	async function handleGenerate() {
		loading = true;
		error = '';
		
		const { data, error: apiError } = await generateTests({
			method: method === 'synthetic' ? 'synthetic' : undefined,
			article_url: method === 'article' ? articleUrl : undefined,
			count: method === 'synthetic' ? Number(count) : 1
		});

		if (data && data.tests.length > 0) {
			onGenerated(data.tests[0].text);
		} else if (apiError) {
			error = apiError;
		}
		
		loading = false;
	}
</script>

<div class="p-6 bg-secondary/20 rounded-xl border border-border space-y-6">
	<div class="grid gap-4 md:grid-cols-2 lg:grid-cols-3 items-end">
		<div class="space-y-2 col-span-2 lg:col-span-2">
			<Label.Root>Generation Source</Label.Root>
			<Select.Root type="single" bind:value={method}>
				<Select.Trigger class="w-full">
					{method === 'synthetic' ? 'Synthetic Generation' : 'From CBC Article URL'}
				</Select.Trigger>
				<Select.Content>
					<Select.Item value="synthetic" label="Synthetic Generation" />
					<Select.Item value="article" label="From CBC Article URL" />
				</Select.Content>
			</Select.Root>
		</div>

		{#if method === 'synthetic'}
			<div class="space-y-2 col-span-1">
				<Label.Root>Count</Label.Root>
				<Input.Root type="number" bind:value={count} min="1" max="5" />
			</div>
		{/if}
	</div>

	{#if method === 'article'}
		<div class="space-y-2">
			<Label.Root>Article URL</Label.Root>
			<Input.Root bind:value={articleUrl} placeholder="https://www.cbc.ca/news/..." />
		</div>
	{/if}

	{#if error}
		<div
			class="p-4 rounded-lg bg-red-50 text-red-600 dark:bg-red-900/20 dark:text-red-400 text-sm font-medium"
		>
			{error}
		</div>
	{/if}

	<Button.Root
		class="w-full"
		onclick={handleGenerate}
		disabled={loading || (method === 'article' && !articleUrl)}
	>
		{#if loading}
			<LoaderCircle class="mr-2 h-4 w-4 animate-spin" />
			Generating...
		{:else}
			<Sparkles class="mr-2 h-4 w-4" />
			Generate Text Content
		{/if}
	</Button.Root>
</div>
