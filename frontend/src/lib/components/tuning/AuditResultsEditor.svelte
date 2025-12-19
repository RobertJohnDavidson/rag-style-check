<script lang="ts">
	import { Card, Button, Badge, Textarea, Input, Label } from '$lib/components/ui';
	import type { Violation } from '$lib/types';
	import { Plus, Check, Trash2, ExternalLink } from '@lucide/svelte';

	interface Props {
		violations: Violation[];
		onSaveAsTest: (finalViolations: Violation[]) => void;
	}

	let { violations, onSaveAsTest }: Props = $props();

	// Local state for editing
	let editableViolations = $state<Violation[]>([]);
	let approvedIndices = $state<Set<number>>(new Set());

	function isComplete(v: Violation) {
		return !!v.rule?.trim() && !!v.text?.trim() && !!v.reason?.trim() && !!v.source_url?.trim();
	}

	function canSave() {
		if (approvedIndices.size === 0) return false;
		return editableViolations.every((v, i) => !approvedIndices.has(i) || isComplete(v));
	}

	$effect(() => {
		editableViolations = JSON.parse(JSON.stringify(violations));
		approvedIndices = new Set(violations.map((_, i) => i));
	});

	function toggleApproval(index: number) {
		if (approvedIndices.has(index)) {
			approvedIndices.delete(index);
		} else {
			approvedIndices.add(index);
		}
		approvedIndices = new Set(approvedIndices);
	}

	function removeViolation(index: number) {
		editableViolations = editableViolations.filter((_, i) => i !== index);
		const newApproved = new Set<number>();
		approvedIndices.forEach(i => {
			if (i < index) newApproved.add(i);
			if (i > index) newApproved.add(i - 1);
		});
		approvedIndices = newApproved;
	}

	function addViolation() {
		editableViolations = [
			{ text: '', rule: 'Custom Rule', reason: '', source_url: '' },
			...editableViolations
		];
		// shift existing approvals and approve the new top item
		const shifted = new Set<number>();
		approvedIndices.forEach(i => shifted.add(i + 1));
		shifted.add(0);
		approvedIndices = shifted;
	}

	function handleSave() {
		const final = editableViolations.filter((_, i) => approvedIndices.has(i));
		onSaveAsTest(final);
	}
</script>

<div class="space-y-6">
	<div class="flex justify-between items-center">
		<h2 class="text-xl font-bold tracking-tight">Audit Results</h2>
		<div class="flex gap-2">
			<Button.Root variant="outline" size="sm" onclick={addViolation}>
				<Plus class="mr-2 h-4 w-4" />
				Add Violation
			</Button.Root>
			<Button.Root size="sm" onclick={handleSave} disabled={!canSave()}>
				<Check class="mr-2 h-4 w-4" />
				Save as Test Case
			</Button.Root>
		</div>
	</div>

	<div class="grid grid-cols-1 gap-4">
		{#each editableViolations as v, i}
			<Card.Root
				class="relative transition-all {approvedIndices.has(i)
					? isComplete(v)
						? 'border-l-4 border-l-green-500'
						: 'border-l-4 border-l-amber-500'
					: 'opacity-50 grayscale'}"
			>
				<div class="absolute top-4 right-4 flex gap-2">
					<Button.Root
						variant={approvedIndices.has(i) ? 'secondary' : 'outline'}
						size="sm"
						onclick={() => toggleApproval(i)}
						class="text-xs font-bold"
					>
						{approvedIndices.has(i) ? 'Approved' : 'Approve'}
					</Button.Root>
					<Button.Root
						variant="ghost"
						size="sm"
						onclick={() => removeViolation(i)}
						class="text-xs font-bold text-muted-foreground hover:text-destructive"
					>
						<Trash2 class="h-4 w-4" />
					</Button.Root>
				</div>

				<Card.Content class="pt-6 space-y-4 pr-16">
					<div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
						<div class="space-y-1">
							<Label.Root>Rule</Label.Root>
							<Input.Root bind:value={v.rule} placeholder="Rule Name" />
						</div>
						<div class="space-y-1">
							<Label.Root>Snippet</Label.Root>
							<Input.Root bind:value={v.text} placeholder="Violating text" />
						</div>
					</div>

					<div class="space-y-1">
						<Label.Root>Explanation</Label.Root>
						<Textarea.Root bind:value={v.reason} placeholder="Why is this a violation?" rows={2} />
					</div>

					<div class="space-y-1">
						<Label.Root>Style Guide Link</Label.Root>
						<Input.Root bind:value={v.source_url} placeholder="https://..." type="url" />
					</div>

					{#if approvedIndices.has(i) && !isComplete(v)}
						<p class="text-xs text-amber-600">Fill all fields before saving this violation.</p>
					{/if}

					{#if v.source_url}
						<div class="pt-2 border-t border-border">
							<a
								href={v.source_url}
								target="_blank"
								class="text-xs text-primary hover:underline flex items-center gap-1"
							>
								<ExternalLink class="h-3 w-3" />
								View in Style Guide
							</a>
						</div>
					{/if}
				</Card.Content>
			</Card.Root>
		{/each}
	</div>
</div>
