<script lang="ts">
	// Error boundary component to catch and display component errors
	import { onMount } from 'svelte';
	
	let hasError = $state(false);
	let errorMessage = $state('');
	
	onMount(() => {
		const handleError = (event: ErrorEvent) => {
			hasError = true;
			errorMessage = event.error?.message || 'An unexpected error occurred';
			console.error('Error caught by boundary:', event.error);
		};
		
		window.addEventListener('error', handleError);
		
		return () => {
			window.removeEventListener('error', handleError);
		};
	});
	
	function reset() {
		hasError = false;
		errorMessage = '';
	}
</script>

{#if hasError}
	<div class="min-h-[200px] flex items-center justify-center p-6">
		<div class="bg-red-100 border border-red-200 rounded-lg p-6 max-w-2xl">
			<h3 class="text-lg font-bold text-red-900 mb-2">Something went wrong</h3>
			<p class="text-red-800 mb-4">{errorMessage}</p>
			<button
				onclick={reset}
				class="px-4 py-2 bg-red-600 hover:bg-red-700 text-white font-semibold rounded-lg transition-colors"
			>
				Try Again
			</button>
		</div>
	</div>
{:else}
	<slot />
{/if}
