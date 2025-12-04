<script lang="ts">
	// Button component with loading spinner and variants
	import LoadingSpinner from './LoadingSpinner.svelte';
	import { buttonVariants } from '$lib/theme';
	
	type Variant = 'primary' | 'secondary' | 'success' | 'danger' | 'ghost';
	type Size = 'sm' | 'md' | 'lg';
	
	interface Props {
		variant?: Variant;
		size?: Size;
		loading?: boolean;
		disabled?: boolean;
		type?: 'button' | 'submit' | 'reset';
		onclick?: (event: MouseEvent) => void;
		class?: string;
	}
	
	let {
		variant = 'primary',
		size = 'md',
		loading = false,
		disabled = false,
		type = 'button',
		onclick,
		class: className = ''
	}: Props = $props();
	
	const isDisabled = $derived(disabled || loading);
	const classes = $derived(buttonVariants(variant, size, isDisabled) + ' ' + className);
</script>

<button
	{type}
	disabled={isDisabled}
	onclick={onclick}
	class={classes}
>
	{#if loading}
		<span class="flex items-center justify-center gap-2">
			<LoadingSpinner size="sm" />
			<span>Loading...</span>
		</span>
	{:else}
		<slot />
	{/if}
</button>
