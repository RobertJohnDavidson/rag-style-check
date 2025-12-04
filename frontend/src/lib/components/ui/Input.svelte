<script lang="ts">
	// Input component with label and inline error display
	import { inputClasses } from '$lib/theme';
	
	interface Props {
		label?: string;
		type?: string;
		value: string | number;
		placeholder?: string;
		error?: string;
		disabled?: boolean;
		required?: boolean;
		autofocus?: boolean;
		class?: string;
		min?: number;
		max?: number;
	}
	
	let {
		label,
		type = 'text',
		value = $bindable(''),
		placeholder,
		error,
		disabled = false,
		required = false,
		autofocus = false,
		class: className = '',
		min,
		max
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
	
	<input
		{type}
		bind:value
		{placeholder}
		{disabled}
		{required}
		{autofocus}
		min={min}
		max={max}
		class={classes}
	/>
	
	{#if error}
		<div class="mt-1 text-sm text-red-600">{error}</div>
	{/if}
</div>
