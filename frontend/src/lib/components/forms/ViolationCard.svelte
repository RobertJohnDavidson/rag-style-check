<script lang="ts">
	import type { ExpectedViolation } from '$lib/types';
	import { Card, Button } from '$lib/components/ui';

	interface Props {
		violation: ExpectedViolation;
		showRemove?: boolean;
		onRemove?: () => void;
		class?: string;
	}

	let { violation, showRemove = false, onRemove, class: className = '' }: Props = $props();
</script>

<Card.Root class="!p-3 bg-accent/20 flex items-start justify-between {className}">
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
				class="text-xs text-primary hover:underline mt-1 inline-block"
			>
				View Rule →
			</a>
		{/if}
	</div>
	{#if showRemove && onRemove}
		<Button.Root
			variant="ghost"
			size="sm"
			onclick={onRemove}
			class="h-auto p-0 px-2 text-destructive hover:text-destructive/80 hover:bg-transparent"
		>
			Remove
		</Button.Root>
	{/if}
</Card.Root>
