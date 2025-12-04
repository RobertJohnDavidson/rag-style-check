<script lang="ts">
	// Modal component with focus trap and keyboard navigation
	import { onMount } from 'svelte';
	
	interface Props {
		isOpen: boolean;
		title: string;
		onConfirm: () => void;
		onCancel: () => void;
		confirmText?: string;
		cancelText?: string;
	}
	
	let {
		isOpen = $bindable(),
		title,
		onConfirm,
		onCancel,
		confirmText = 'Confirm',
		cancelText = 'Cancel'
	}: Props = $props();
	
	let modalRef: HTMLDivElement | null = $state(null);
	let firstFocusable: HTMLElement | null = $state(null);
	let lastFocusable: HTMLElement | null = $state(null);
	
	function handleKeyDown(event: KeyboardEvent) {
		if (!isOpen) return;
		
		if (event.key === 'Escape') {
			event.preventDefault();
			onCancel();
		} else if (event.key === 'Enter' && event.target !== firstFocusable) {
			event.preventDefault();
			onConfirm();
		} else if (event.key === 'Tab') {
			handleTabKey(event);
		}
	}
	
	function handleTabKey(event: KeyboardEvent) {
		if (!firstFocusable || !lastFocusable) return;
		
		if (event.shiftKey) {
			if (document.activeElement === firstFocusable) {
				event.preventDefault();
				lastFocusable.focus();
			}
		} else {
			if (document.activeElement === lastFocusable) {
				event.preventDefault();
				firstFocusable.focus();
			}
		}
	}
	
	function handleBackdropClick(event: MouseEvent) {
		if (event.target === event.currentTarget) {
			onCancel();
		}
	}
	
	$effect(() => {
		if (isOpen && modalRef) {
			const focusableElements = modalRef.querySelectorAll<HTMLElement>(
				'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
			);
			firstFocusable = focusableElements[0] || null;
			lastFocusable = focusableElements[focusableElements.length - 1] || null;
			
			// Focus first element
			firstFocusable?.focus();
		}
	});
</script>

<svelte:window onkeydown={handleKeyDown} />

{#if isOpen}
	<!-- Backdrop -->
	<div
		class="fixed inset-0 z-50 bg-black bg-opacity-50 flex items-center justify-center p-4"
		onclick={handleBackdropClick}
		role="dialog"
		aria-modal="true"
		aria-labelledby="modal-title"
	>
		<!-- Modal content -->
		<div
			bind:this={modalRef}
			class="bg-white rounded-lg shadow-xl max-w-md w-full p-6"
			role="document"
		>
			<h2 id="modal-title" class="text-xl font-bold text-gray-900 mb-4">{title}</h2>
			
			<div class="mb-6">
				<slot />
			</div>
			
			<div class="flex gap-3 justify-end">
				<button
					type="button"
					onclick={onCancel}
					class="px-4 py-2 bg-gray-200 hover:bg-gray-300 text-gray-800 font-semibold rounded-lg transition-colors"
				>
					{cancelText}
				</button>
				<button
					type="button"
					onclick={onConfirm}
					class="px-4 py-2 bg-[#CC0000] hover:bg-[#A30000] text-white font-semibold rounded-lg transition-colors"
				>
					{confirmText}
				</button>
			</div>
		</div>
	</div>
{/if}
