<script lang="ts">
	// Alert component for displaying messages
	import { alertVariants } from '$lib/theme';
	
	type Variant = 'error' | 'success' | 'warning' | 'info';
	
	interface Props {
		variant?: Variant;
		class?: string;
	}
	
	let {
		variant = 'info',
		class: className = ''
	}: Props = $props();
	
	const classes = $derived(`${alertVariants(variant)} ${className}`);
</script>

<div class={classes} role="alert">
	<slot />
</div>
