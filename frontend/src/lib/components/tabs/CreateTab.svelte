<script lang="ts">
	import { Select, Label } from '$lib/components/ui';
	import { ManualForm, ArticleForm, SyntheticForm } from '.';

	interface Props {
		onUnsavedChanges?: (hasChanges: boolean) => void;
		onRegisterReset?: (resetFn: () => void) => void;
	}

	let { onUnsavedChanges, onRegisterReset }: Props = $props();

	// Local state
	let method = $state<'manual' | 'article' | 'synthetic'>('manual');
	let currentResetFn: (() => void) | null = null;

	// Reset form when method changes
	$effect(() => {
		// Don't reset on initial mount
		if (currentResetFn) {
			currentResetFn();
		}
	});

	function handleRegisterReset(resetFn: () => void) {
		currentResetFn = resetFn;
		onRegisterReset?.(resetFn);
	}
</script>

<div class="space-y-4">
	<div class="space-y-2">
		<Label.Root>Generation Method</Label.Root>
		<Select.Root type="single" bind:value={method}>
			<Select.Trigger class="w-full">
				{#if method === 'manual'}
					Manual Entry
				{:else if method === 'article'}
					From CBC Article
				{:else if method === 'synthetic'}
					Generate Synthetic
				{/if}
			</Select.Trigger>
			<Select.Content>
				<Select.Item value="manual" label="Manual Entry" />
				<Select.Item value="article" label="From CBC Article" />
				<Select.Item value="synthetic" label="Generate Synthetic" />
			</Select.Content>
		</Select.Root>
	</div>

	{#if method === 'manual'}
		<ManualForm {onUnsavedChanges} onRegisterReset={handleRegisterReset} />
	{:else if method === 'article'}
		<ArticleForm {onUnsavedChanges} onRegisterReset={handleRegisterReset} />
	{:else if method === 'synthetic'}
		<SyntheticForm {onUnsavedChanges} onRegisterReset={handleRegisterReset} />
	{/if}
</div>
