<script lang="ts">
	import { Badge, Button, Card, Separator } from '$lib/components/ui';
	import { X, CheckCircle2, AlertCircle, Info, ChevronRight, MessageSquare } from '@lucide/svelte';
	import type { TestResult, Test, Violation } from '$lib/types';

	interface Props {
		test: Test;
		result: TestResult;
		onClose: () => void;
	}

	let { test, result, onClose }: Props = $props();

	function getStatus(metrics: any) {
		const expected = metrics.true_positives + metrics.false_negatives;
		const hits = metrics.true_positives;
		const missed = metrics.false_negatives;
		const noise = metrics.false_positives;

		if (expected === 0) {
			return noise === 0 ? 'CLEAN' : 'NOISY';
		}
		if (missed === 0 && noise === 0) return 'PERFECT';
		if (hits > 0) return 'IMPERFECT';
		return 'FAILED';
	}

	function getStatusColor(status: string) {
		switch (status) {
			case 'PERFECT':
			case 'CLEAN':
				return 'text-green-500';
			case 'IMPERFECT':
			case 'NOISY':
				return 'text-yellow-500';
			case 'FAILED':
				return 'text-red-500';
			default:
				return 'text-muted-foreground';
		}
	}

	let status = $derived(getStatus(result.metrics));
</script>

<div
	class="fixed inset-0 z-[100] flex items-center justify-center p-4 sm:p-6 md:p-10 bg-background/80 backdrop-blur-sm animate-in fade-in duration-200"
>
	<div
		class="bg-card w-full max-w-5xl h-full max-h-[90vh] rounded-2xl border shadow-2xl flex flex-col overflow-hidden animate-in slide-in-from-bottom-4 duration-300"
	>
		<!-- Header -->
		<div class="p-6 border-b flex items-center justify-between bg-muted/30">
			<div class="flex items-center gap-4">
				<div class="p-2 rounded-xl bg-primary/10">
					<Info class="h-6 w-6 text-primary" />
				</div>
				<div class="flex flex-col">
					<h2 class="text-xl font-bold tracking-tight">{test.label}</h2>
					<p class="text-xs text-muted-foreground uppercase tracking-widest font-bold">
						{test.generation_method} • Ran at {new Date(result.executed_at).toLocaleTimeString()}
					</p>
				</div>
			</div>
			<Button.Root variant="ghost" size="icon" class="rounded-full" onclick={onClose}>
				<X class="h-5 w-5" />
			</Button.Root>
		</div>

		<!-- Content -->
		<div class="flex-1 overflow-y-auto p-8 space-y-8">
			<!-- Metrics Summary -->
			<section class="grid grid-cols-1 md:grid-cols-4 gap-4">
				<Card.Root class="p-6 flex flex-col items-center justify-center text-center">
					<div class="text-2xl font-black {getStatusColor(status)}">{status}</div>
					<div class="text-[10px] text-muted-foreground uppercase font-bold tracking-tighter mt-1">
						Status
					</div>
				</Card.Root>
				<Card.Root
					class="p-6 flex flex-col items-center justify-center text-center border-green-500/20 bg-green-500/5"
				>
					<div class="text-3xl font-black text-green-600">{result.metrics.true_positives}</div>
					<div class="text-[10px] text-green-600 uppercase font-bold tracking-tighter mt-1">
						Hits (TP)
					</div>
				</Card.Root>
				<Card.Root
					class="p-6 flex flex-col items-center justify-center text-center border-red-500/20 bg-red-500/5"
				>
					<div class="text-3xl font-black text-red-600">{result.metrics.false_negatives}</div>
					<div class="text-[10px] text-red-600 uppercase font-bold tracking-tighter mt-1">
						Misses (FN)
					</div>
				</Card.Root>
				<Card.Root
					class="p-6 flex flex-col items-center justify-center text-center border-amber-500/20 bg-amber-500/5"
				>
					<div class="text-3xl font-black text-amber-600">{result.metrics.false_positives}</div>
					<div class="text-[10px] text-amber-600 uppercase font-bold tracking-tighter mt-1">
						Noise (FP)
					</div>
				</Card.Root>
			</section>

			<div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
				<!-- Left Column: Source Text -->
				<div class="space-y-4">
					<div class="flex items-center gap-2 px-1">
						<MessageSquare class="h-4 w-4 text-primary" />
						<h3 class="text-sm font-bold uppercase tracking-wider">Audited Text</h3>
					</div>
					<Card.Root class="h-fit">
						<Card.Content class="p-6">
							<div
								class="prose prose-sm dark:prose-invert max-w-none whitespace-pre-wrap font-serif text-lg leading-relaxed"
							>
								{test.text}
							</div>
						</Card.Content>
					</Card.Root>
				</div>

				<!-- Right Column: Violations Comparison -->
				<div class="space-y-8">
					<!-- Expected Violations -->
					<div class="space-y-4">
						<div class="flex items-center gap-2 px-1">
							<CheckCircle2 class="h-4 w-4 text-green-500" />
							<h3 class="text-sm font-bold uppercase tracking-wider">Expected Violations</h3>
						</div>
						<div class="space-y-2">
							{#if test.expected_violations && test.expected_violations.length > 0}
								{#each test.expected_violations as v}
									<div class="p-4 rounded-xl border bg-muted/30 flex items-start gap-3">
										<div class="mt-1 p-1 rounded-full bg-green-500/10">
											<div class="h-2 w-2 rounded-full bg-green-500"></div>
										</div>
										<div class="flex flex-col gap-1">
											<span class="text-sm font-bold">{v.rule || 'Unnamed Rule'}</span>
											<p class="text-xs text-muted-foreground leading-tight italic">"{v.text}"</p>
											{#if v.link}
												<a
													href={v.link}
													target="_blank"
													class="text-[10px] text-primary hover:underline mt-1"
													>View Rule Reference</a
												>
											{/if}
										</div>
									</div>
								{/each}
							{:else}
								<div
									class="py-12 border-2 border-dashed rounded-xl flex items-center justify-center text-muted-foreground text-sm italic"
								>
									No violations expected in this text.
								</div>
							{/if}
						</div>
					</div>

					<!-- Detected Violations -->
					<div class="space-y-4">
						<div class="flex items-center gap-2 px-1">
							<AlertCircle class="h-4 w-4 text-primary" />
							<h3 class="text-sm font-bold uppercase tracking-wider">Detected by AI</h3>
						</div>
						<div class="space-y-2">
							{#if result.detected_violations && result.detected_violations.length > 0}
								{#each result.detected_violations as v}
									{@const isMatched = test.expected_violations?.some(
										(ev) => ev.rule === v.rule || ev.link === v.url
									)}
									<div
										class="p-4 rounded-xl border {isMatched
											? 'border-green-500/50 bg-green-500/5'
											: 'border-amber-500/50 bg-amber-500/5'} flex items-start gap-3"
									>
										<div
											class="mt-1 p-1 rounded-full {isMatched
												? 'bg-green-500/20'
												: 'bg-amber-500/20'}"
										>
											<ChevronRight
												class="h-3 w-3 {isMatched ? 'text-green-600' : 'text-amber-600'}"
											/>
										</div>
										<div class="flex flex-col gap-1">
											<div class="flex items-center gap-2">
												<span class="text-sm font-bold">{v.rule || 'Unknown Rule'}</span>
												{#if !isMatched}
													<Badge.Root
														variant="outline"
														class="text-[9px] py-0 h-4 border-amber-500/30 text-amber-700 bg-amber-500/10 uppercase"
													>
														EXTRA NOISE
													</Badge.Root>
												{/if}
											</div>
											<p class="text-xs text-muted-foreground leading-tight italic">"{v.text}"</p>
											<p class="text-[10px] text-muted-foreground mt-1">
												<span class="font-bold">Reasoning:</span>
												{v.reason}
											</p>
										</div>
									</div>
								{/each}
							{:else}
								<div
									class="py-12 border-2 border-dashed rounded-xl flex items-center justify-center text-muted-foreground text-sm italic"
								>
									AI detected 0 violations.
								</div>
							{/if}
						</div>
					</div>
				</div>
			</div>
		</div>

		<!-- Footer -->
		<div class="p-4 border-t flex justify-end bg-muted/10">
			<Button.Root variant="secondary" onclick={onClose}>Close Detailed View</Button.Root>
		</div>
	</div>
</div>

<style>
	.animate-in {
		animation-duration: 0.2s;
		animation-fill-mode: both;
	}
	.fade-in { animation-name: fadeIn; }
	.slide-in-from-bottom-4 { animation-name: slideInFromBottom; animation-duration: 0.3s; }
	
	@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
	@keyframes slideInFromBottom { from { transform: translateY(1rem); opacity: 0; } to { transform: translateY(0); opacity: 1; } }
</style>
