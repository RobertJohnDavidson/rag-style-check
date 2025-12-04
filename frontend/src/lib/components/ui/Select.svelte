<script lang="ts">
	// Select component with label and inline error display
	import { inputClasses } from '$lib/theme';
	
	interface Props {
		label?: string;
		value: string;
		error?: string;
		disabled?: boolean;
		required?: boolean;
		class?: string;
	}
	
	let {
		label,
		value = $bindable(''),
		error,
		disabled = false,
		required = false,
		class: className = ''
	}: Props = $props();
	
	const classes = $derived(`${inputClasses(error)} p-3 ${className}`);
</script>

<div class="w-full">
	{#if label}
		<label class="block text-sm font-semibold text-gray-700 mb-2">
			{label}
			{#if required}<span class="text-red-500">*</span>{/if}
		</label>
	{/if}
	
	<select
		bind:value
		{disabled}
		{required}
		class={classes}
	>
		<slot />
	</select>
	
	{#if error}
		<div class="mt-1 text-sm text-red-600">{error}</div>
	{/if}
</div>
