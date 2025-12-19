<script lang="ts">
	import { fly, fade } from 'svelte/transition';
	import { Button, Separator } from '$lib/components/ui';
	import { X, Settings2, RotateCcw } from '@lucide/svelte';
	import TuningParameters from './TuningParameters.svelte';
	import type { TuningParameters as TuningParams } from '$lib/types';
	import { getTuningDefaults } from '$lib/api';

	interface Props {
		isOpen: boolean;
		parameters: TuningParams;
	}

	let { isOpen = $bindable(), parameters = $bindable() }: Props = $props();

	async function resetDefaults() {
		const { data } = await getTuningDefaults();
		if (data) {
			parameters = data;
		}
	}

	function close() {
		isOpen = false;
	}
</script>

{#if isOpen}
	<!-- Backdrop -->
	<div
		class="fixed inset-0 z-[60] bg-background/80 backdrop-blur-sm"
		onclick={close}
		onkeydown={(e) => e.key === 'Escape' && close()}
		role="button"
		tabindex="-1"
		aria-label="Close settings"
		transition:fade={{ duration: 200 }}
	></div>

	<!-- Drawer Panel -->
	<div
		class="fixed inset-y-0 right-0 z-[70] w-full max-w-sm border-l bg-background p-0 shadow-2xl sm:max-w-md"
		transition:fly={{ x: 400, duration: 300, opacity: 1 }}
	>
		<div class="flex h-full flex-col">
			<!-- Header -->
			<div class="flex items-center justify-between border-b px-6 py-4">
				<div class="flex items-center gap-2">
					<div class="rounded-full bg-primary/10 p-2 text-primary">
						<Settings2 class="h-5 w-5" />
					</div>
					<div>
						<h2 class="text-lg font-bold">Tuning Settings</h2>
						<p class="text-xs text-muted-foreground">Adjust auditor & RAG parameters</p>
					</div>
				</div>
				<Button.Root variant="ghost" size="icon" onclick={close} class="rounded-full">
					<X class="h-5 w-5" />
				</Button.Root>
			</div>

			<!-- Content -->
			<div class="flex-1 overflow-y-auto px-6 py-6 custom-scrollbar">
				<TuningParameters bind:parameters />
			</div>

			<!-- Footer -->
			<div class="border-t bg-muted/30 px-6 py-4">
				<div class="flex items-center justify-between gap-4">
					<Button.Root
						variant="outline"
						size="sm"
						class="gap-2 text-muted-foreground hover:text-foreground"
						onclick={resetDefaults}
					>
						<RotateCcw class="h-4 w-4" /> Reset Defaults
					</Button.Root>
					<Button.Root variant="default" size="sm" class="px-8" onclick={close}>
						Apply & Close
					</Button.Root>
				</div>
			</div>
		</div>
	</div>
{/if}

<style>
	.custom-scrollbar::-webkit-scrollbar {
		width: 4px;
	}
	.custom-scrollbar::-webkit-scrollbar-track {
		background: transparent;
	}
	.custom-scrollbar::-webkit-scrollbar-thumb {
		background: hsl(var(--muted-foreground) / 0.3);
		border-radius: 10px;
	}
</style>
