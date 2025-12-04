<script lang="ts">
	// Slider component for range inputs with live value display
	
	interface Props {
		label: string;
		value: number;
		min: number;
		max: number;
		step: number;
		disabled?: boolean;
		formatter?: (value: number) => string;
		class?: string;
	}
	
	let {
		label,
		value = $bindable(0),
		min,
		max,
		step,
		disabled = false,
		formatter = (v) => v.toString(),
		class: className = ''
	}: Props = $props();
	
	const formattedValue = $derived(formatter(value));
</script>

<div class="w-full {className}">
	<label class="block text-sm font-medium text-gray-700 mb-1">
		{label}: <span class="font-semibold">{formattedValue}</span>
	</label>
	
	<input
		type="range"
		bind:value
		{min}
		{max}
		{step}
		{disabled}
		class="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-[#CC0000]"
	/>
</div>
