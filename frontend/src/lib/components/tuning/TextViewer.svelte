<script lang="ts">
	import type { Violation } from '$lib/types';
	import { Button } from '$lib/components/ui';
	import { Plus } from '@lucide/svelte';

	interface Props {
		text: string;
		violations: Violation[];
		onAddViolation: (selectedText: string) => void;
		onHighlightClick: (violationIndex: number) => void;
	}

	let { text, violations, onAddViolation, onHighlightClick }: Props = $props();

	let selection = $state('');
	let showSelectionButton = $state(false);
	let buttonPos = $state({ x: 0, y: 0 });

	function handleMouseUp(e: MouseEvent) {
		const sel = window.getSelection();
		if (sel && sel.toString().trim().length > 0) {
			selection = sel.toString().trim();
			showSelectionButton = true;
			buttonPos = { x: e.clientX, y: e.clientY - 40 };
		} else {
			showSelectionButton = false;
		}
	}

	function addManual() {
		onAddViolation(selection);
		showSelectionButton = false;
		window.getSelection()?.removeAllRanges();
	}

	function escapeHtml(str: string) {
		return str
			.replace(/&/g, '&amp;')
			.replace(/</g, '&lt;')
			.replace(/>/g, '&gt;')
			.replace(/"/g, '&quot;')
			.replace(/'/g, '&#039;');
	}

	function escapeRegExp(string: string) {
		return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
	}

	let processedText = $derived.by(() => {
		let output = escapeHtml(text);
		if (!violations.length) return output;

		const snippets = violations
			.map((v, i) => ({ text: v.text, index: i }))
			.filter((s) => s.text.length > 0)
			.sort((a, b) => b.text.length - a.text.length);

		if (!snippets.length) return output;

		let matches: {start: number, end: number, index: number}[] = [];
		
		snippets.forEach((s) => {
			const escapedSnippet = escapeHtml(s.text);
			const pattern = escapeRegExp(escapedSnippet);
			const regex = new RegExp(pattern, 'g');
			let match;
			while ((match = regex.exec(output)) !== null) {
				const start = match.index;
				const end = start + escapedSnippet.length;
				
				// Only add if it doesn't overlap with existing matches
				const overlaps = matches.some(m => 
					(start >= m.start && start < m.end) || 
					(end > m.start && end <= m.end) ||
					(m.start >= start && m.start < end)
				);

				if (!overlaps) {
					matches.push({
						start,
						end,
						index: s.index
					});
				}
				// Avoid infinite loops with global regex and empty matches
				if (match.index === regex.lastIndex) {
					regex.lastIndex++;
				}
			}
		});
		
		// Sort matches by start position
		matches.sort((a, b) => a.start - b.start);
		
		let lastIndex = 0;
		let html = '';
		matches.forEach(m => {
			html += output.substring(lastIndex, m.start);
			html += `<mark class="bg-primary/20 border-b-2 border-primary cursor-pointer hover:bg-primary/30 transition-colors px-0.5 rounded-sm" data-violation-index="${m.index}">${output.substring(m.start, m.end)}</mark>`;
			lastIndex = m.end;
		});
		html += output.substring(lastIndex);
		
		return html;
	});

	function handleClick(e: MouseEvent) {
		const target = e.target as HTMLElement;
		if (target.tagName === 'MARK') {
			const index = parseInt(target.getAttribute('data-violation-index') || '-1');
			if (index !== -1) {
				onHighlightClick(index);
			}
		}
	}

	function handleKeyDown(e: KeyboardEvent) {
		if (e.key === 'Enter' || e.key === ' ') {
			const target = e.target as HTMLElement;
			if (target.tagName === 'MARK') {
				e.preventDefault();
				const index = parseInt(target.getAttribute('data-violation-index') || '-1');
				if (index !== -1) {
					onHighlightClick(index);
				}
			}
		}
	}
</script>

<div class="relative">
	<!-- svelte-ignore a11y_no_noninteractive_tabindex -->
	<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
	<div
		class="prose dark:prose-invert max-w-none p-6 rounded-xl border bg-card text-card-foreground shadow-sm whitespace-pre-wrap leading-relaxed text-lg focus:outline-none min-h-[300px]"
		onmouseup={handleMouseUp}
		onclick={handleClick}
		onkeydown={handleKeyDown}
		role="article"
		tabindex="0"
		aria-label="Article text viewer. Select text to add violations or click highlights to view details."
	>
		{@html processedText}
	</div>

	{#if showSelectionButton}
		<div
			class="fixed z-[100] animate-in fade-in zoom-in duration-200"
			style="left: {buttonPos.x}px; top: {buttonPos.y}px; transform: translate(-50%, -100%);"
		>
			<Button.Root
				size="sm"
				class="shadow-lg gap-2 bg-primary text-primary-foreground hover:bg-primary/90 rounded-full"
				onclick={addManual}
			>
				<Plus class="h-4 w-4" /> Add Violation
			</Button.Root>
		</div>
	{/if}
</div>

<style>
	:global(mark) {
		color: inherit;
	}
</style>
