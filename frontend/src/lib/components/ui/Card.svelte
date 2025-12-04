<script lang="ts">
	// Card component for content containers
	import { cardClasses } from '$lib/theme';
	
	interface Props {
		hover?: boolean;
		class?: string;
	}
	
	let {
		hover = false,
		class: className = ''
	}: Props = $props();
	
	const classes = $derived(`${cardClasses(hover)} p-6 ${className}`);
</script>

<div class={classes}>
	<slot />
</div>
