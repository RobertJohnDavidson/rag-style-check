<script lang="ts">
	// Badge component for labels and tags
	import { badgeVariants } from '$lib/theme';
	
	type Variant = 'manual' | 'article' | 'synthetic' | 'default';
	
	interface Props {
		variant?: Variant;
		class?: string;
	}
	
	let {
		variant = 'default',
		class: className = ''
	}: Props = $props();
	
	const classes = $derived(`${badgeVariants(variant)} ${className}`);
</script>

<span class={classes}>
	<slot />
</span>
