<script lang="ts">
	// Loading spinner component with CBC red color
	
	type Size = 'sm' | 'md' | 'lg';
	
	interface Props {
		size?: Size;
	}
	
	let { size = 'md' }: Props = $props();
	
	const sizeClasses = {
		sm: 'w-4 h-4 border-2',
		md: 'w-8 h-8 border-3',
		lg: 'w-12 h-12 border-4'
	};
</script>

<div class="inline-block {sizeClasses[size]} border-[#CC0000] border-t-transparent rounded-full animate-spin" role="status" aria-label="Loading">
	<span class="sr-only">Loading...</span>
</div>

<style>
	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}
	
	.animate-spin {
		animation: spin 0.8s linear infinite;
	}
</style>
