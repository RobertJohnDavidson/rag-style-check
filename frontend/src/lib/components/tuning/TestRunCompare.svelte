<script lang="ts">
	import { Card, Badge } from '$lib/components/ui';

	interface Metrics {
		precision: number | null;
		recall: number | null;
		f1_score: number | null;
		true_positives: number;
		false_positives: number;
		false_negatives: number;
	}

	interface Props {
		metrics: Metrics;
		expectedCount: number;
		detectedCount: number;
	}

	let { metrics, expectedCount, detectedCount }: Props = $props();

	function getScoreColor(val: number) {
		if (val > 0.8) return 'bg-green-500';
		if (val > 0.5) return 'bg-yellow-500';
		return 'bg-red-500';
	}
</script>

<div class="grid grid-cols-1 md:grid-cols-3 gap-6">
	<!-- Main Scores -->
	<Card.Root class="md:col-span-2">
		<Card.Header class="pb-2">
			<Card.Title class="text-sm font-medium text-muted-foreground uppercase tracking-wider"
				>Evaluation Scores</Card.Title
			>
		</Card.Header>
		<Card.Content>
			<div class="flex items-center justify-around py-4">
				<div class="text-center">
					<div class="text-3xl font-black">{((metrics.precision || 0) * 100).toFixed(0)}%</div>
					<div class="text-xs text-muted-foreground font-bold uppercase mt-1">Precision</div>
				</div>
				<div class="w-px h-12 bg-border"></div>
				<div class="text-center">
					<div class="text-3xl font-black">{((metrics.recall || 0) * 100).toFixed(0)}%</div>
					<div class="text-xs text-muted-foreground font-bold uppercase mt-1">Recall</div>
				</div>
				<div class="w-px h-12 bg-border"></div>
				<div class="text-center">
					<div class="text-3xl font-black text-primary">
						{((metrics.f1_score || 0) * 100).toFixed(0)}%
					</div>
					<div class="text-xs text-muted-foreground font-bold uppercase mt-1">F1 Score</div>
				</div>
			</div>
		</Card.Content>
	</Card.Root>

	<!-- Counts Summary -->
	<Card.Root>
		<Card.Header class="pb-2">
			<Card.Title class="text-sm font-medium text-muted-foreground uppercase tracking-wider"
				>Detection Summary</Card.Title
			>
		</Card.Header>
		<Card.Content class="space-y-4 pt-2">
			<div class="grid grid-cols-2 gap-4">
				<div class="p-3 rounded-lg bg-secondary/50 border border-border">
					<div class="text-[10px] text-muted-foreground font-bold uppercase">Matches (TP)</div>
					<div class="text-xl font-bold">{metrics.true_positives}</div>
				</div>
				<div class="p-3 rounded-lg bg-secondary/50 border border-border">
					<div class="text-[10px] text-muted-foreground font-bold uppercase">False Hits (FP)</div>
					<div class="text-xl font-bold">{metrics.false_positives}</div>
				</div>
				<div class="p-3 rounded-lg bg-secondary/50 border border-border">
					<div class="text-[10px] text-muted-foreground font-bold uppercase">Missed (FN)</div>
					<div class="text-xl font-bold">{metrics.false_negatives}</div>
				</div>
				<div class="p-3 rounded-lg bg-secondary/50 border border-border">
					<div class="text-[10px] text-muted-foreground font-bold uppercase">Expected</div>
					<div class="text-xl font-bold">{expectedCount}</div>
				</div>
			</div>
		</Card.Content>
	</Card.Root>
</div>
