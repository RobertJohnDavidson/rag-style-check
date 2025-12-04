<script lang="ts">
	import { Select } from '$lib/components/ui';
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
	<Select
		label="Generation Method"
		bind:value={method}
	>
		<option value="manual">Manual Entry</option>
		<option value="article">From CBC Article</option>
		<option value="synthetic">Generate Synthetic</option>
	</Select>

	{#if method === 'manual'}
		<ManualForm {onUnsavedChanges} onRegisterReset={handleRegisterReset} />
	{:else if method === 'article'}
		<ArticleForm {onUnsavedChanges} onRegisterReset={handleRegisterReset} />
	{:else if method === 'synthetic'}
		<SyntheticForm {onUnsavedChanges} onRegisterReset={handleRegisterReset} />
	{/if}
</div>
