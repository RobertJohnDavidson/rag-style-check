<script lang="ts">
	import { LoaderCircle } from "@lucide/svelte";
	import { cn } from "$lib/utils";

	let { 
		size = "md",
		class: className = "" 
	}: { 
		size?: "sm" | "md" | "lg" | "xl";
		class?: string;
	} = $props();

	const sizeClasses = {
		sm: "h-4 w-4",
		md: "h-6 w-6",
		lg: "h-8 w-8",
		xl: "h-12 w-12"
	};
</script>

<div class={cn('flex items-center justify-center', className)}>
	<LoaderCircle class={cn('animate-spin text-primary', sizeClasses[size])} />
</div>
