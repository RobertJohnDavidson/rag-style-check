<script lang="ts">
	import type { ExpectedViolation } from '$lib/types';
	import { cardClasses } from '$lib/theme';

	interface Props {
		violation: ExpectedViolation;
		showRemove?: boolean;
		onRemove?: () => void;
		class?: string;
	}

	let { violation, showRemove = false, onRemove, class: className = '' }: Props = $props();
</script>

<div class="{cardClasses(false)} !p-3 bg-gray-50 flex items-start justify-between {className}">
	<div class="flex-1">
		<div class="font-semibold text-sm text-gray-900">{violation.rule}</div>
		<div class="text-sm text-gray-600 mt-1">"{violation.text}"</div>
		{#if violation.reason}
			<div class="text-xs text-gray-500 mt-1">{violation.reason}</div>
		{/if}
		{#if violation.link}
			<a 
				href={violation.link} 
				target="_blank" 
				rel="noopener noreferrer" 
				class="text-xs text-indigo-600 hover:text-indigo-800 mt-1 inline-block"
			>
				View Rule →
			</a>
		{/if}
	</div>
	{#if showRemove && onRemove}
		<button
			onclick={onRemove}
			class="ml-2 text-red-600 hover:text-red-800 text-sm font-medium"
			type="button"
		>
			Remove
		</button>
	{/if}
</div>
