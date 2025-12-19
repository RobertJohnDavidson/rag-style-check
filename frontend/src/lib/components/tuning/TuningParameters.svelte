<script lang="ts">
	import { Select, Slider, Label, Switch } from '$lib/components/ui';
	import type { TuningParameters, ModelInfo } from '$lib/types';

	interface Props {
		parameters: TuningParameters;
		disabled?: boolean;
		class?: string;
		models?: ModelInfo[];
	}

	let { 
		parameters = $bindable(), 
		disabled = false,
		class: className = '',
		models = []
	}: Props = $props();

	// Helper for Slider array binding
	function handleSliderChange(key: keyof TuningParameters, val: number[]) {
		(parameters as any)[key] = val[0];
	}
</script>

<div class="space-y-6 {className}">
	<div class="grid grid-cols-1 gap-6">
		<!-- Model Selection -->
		<div class="space-y-2">
			<Label.Root class="text-xs font-bold uppercase tracking-wider text-muted-foreground"
				>Model Configuration</Label.Root
			>
			<Select.Root type="single" bind:value={parameters.model_name} {disabled}>
				<Select.Trigger class="w-full h-11">
					{models.find((m) => m.name === parameters.model_name)?.display_name || 'Select a model'}
				</Select.Trigger>
				<Select.Content class="z-100">
					{#each models as model}
						<Select.Item value={model.name} label={model.display_name} />
					{/each}
				</Select.Content>
			</Select.Root>
		</div>

		<!-- Thinking Process Toggle -->
		<div
			class="flex items-center justify-between p-4 rounded-lg bg-muted/30 border border-border/50"
		>
			<div class="space-y-0.5">
				<Label.Root class="text-sm font-medium">Include Thinking</Label.Root>
				<p class="text-[10px] text-muted-foreground uppercase font-bold tracking-tighter">
					Will increase cost and time
				</p>
			</div>
			<Switch.Root bind:checked={parameters.include_thinking} {disabled} />
		</div>

		<div class="h-px bg-border my-2"></div>

		<!-- LLM Parameters -->
		<div class="space-y-4">
			<Label.Root class="text-xs font-bold uppercase tracking-wider text-muted-foreground"
				>LLM Settings</Label.Root
			>

			<!-- Temperature -->
			<div class="space-y-3">
				<div class="flex items-center justify-between">
					<span class="text-sm font-medium">Temperature</span>
					<span class="text-xs font-mono bg-muted px-1.5 py-0.5 rounded"
						>{parameters.temperature.toFixed(1)}</span
					>
				</div>
				<Slider.Root
					type="multiple"
					value={[parameters.temperature]}
					onValueChange={(v: number[]) => handleSliderChange('temperature', v)}
					min={0}
					max={2}
					step={0.1}
					{disabled}
				/>
			</div>

			<!-- Max Agent Iterations -->
			<div class="space-y-3">
				<div class="flex items-center justify-between">
					<span class="text-sm font-medium">Max Agent Iterations</span>
					<span class="text-xs font-mono bg-muted px-1.5 py-0.5 rounded"
						>{parameters.max_agent_iterations}</span
					>
				</div>
				<Slider.Root
					type="multiple"
					value={[parameters.max_agent_iterations]}
					onValueChange={(v: number[]) => handleSliderChange('max_agent_iterations', v)}
					min={1}
					max={3}
					step={1}
					{disabled}
				/>
			</div>
		</div>

		<div class="h-px bg-border my-2"></div>

		<!-- Retrieval Parameters -->
		<div class="space-y-4">
			<Label.Root class="text-xs font-bold uppercase tracking-wider text-muted-foreground"
				>RAG / Retrieval</Label.Root
			>

			<!-- Initial Retrieval Count -->
			<div class="space-y-3">
				<div class="flex items-center justify-between">
					<span class="text-sm font-medium">Initial Retrieval</span>
					<span class="text-xs font-mono bg-muted px-1.5 py-0.5 rounded"
						>{parameters.initial_retrieval_count}</span
					>
				</div>
				<Slider.Root
					type="multiple"
					value={[parameters.initial_retrieval_count]}
					onValueChange={(v: number[]) => handleSliderChange('initial_retrieval_count', v)}
					min={10}
					max={200}
					step={5}
					{disabled}
				/>
			</div>

			<!-- Final Top K -->
			<div class="space-y-3">
				<div class="flex items-center justify-between">
					<span class="text-sm font-medium">Final Top K</span>
					<span class="text-xs font-mono bg-muted px-1.5 py-0.5 rounded"
						>{parameters.final_top_k}</span
					>
				</div>
				<Slider.Root
					type="multiple"
					value={[parameters.final_top_k]}
					onValueChange={(v: number[]) => handleSliderChange('final_top_k', v)}
					min={5}
					max={100}
					step={5}
					{disabled}
				/>
			</div>

			<!-- Rerank Score Threshold -->
			<div class="space-y-3">
				<div class="flex items-center justify-between">
					<span class="text-sm font-medium">Rerank Threshold</span>
					<span class="text-xs font-mono bg-muted px-1.5 py-0.5 rounded"
						>{parameters.rerank_score_threshold.toFixed(2)}</span
					>
				</div>
				<Slider.Root
					type="multiple"
					value={[parameters.rerank_score_threshold]}
					onValueChange={(v: number[]) => handleSliderChange('rerank_score_threshold', v)}
					min={0}
					max={1}
					step={0.05}
					{disabled}
				/>
			</div>
		</div>

		<div class="h-px bg-border my-2"></div>

		<!-- Guardrails -->
		<div class="space-y-4">
			<Label.Root class="text-xs font-bold uppercase tracking-wider text-muted-foreground"
				>Guardrails & Logic</Label.Root
			>

			<!-- Aggregated Rule Limit -->
			<div class="space-y-3">
				<div class="flex items-center justify-between">
					<span class="text-sm font-medium">Rule Limit</span>
					<span class="text-xs font-mono bg-muted px-1.5 py-0.5 rounded"
						>{parameters.aggregated_rule_limit}</span
					>
				</div>
				<Slider.Root
					type="multiple"
					value={[parameters.aggregated_rule_limit]}
					onValueChange={(v: number[]) => handleSliderChange('aggregated_rule_limit', v)}
					min={15}
					max={100}
					step={5}
					{disabled}
				/>
			</div>

			<!-- Confidence Threshold -->
			<div class="space-y-3">
				<div class="flex items-center justify-between">
					<span class="text-sm font-medium">Confidence Threshold</span>
					<span class="text-xs font-mono bg-muted px-1.5 py-0.5 rounded"
						>{parameters.confidence_threshold.toFixed(2)}</span
					>
				</div>
				<Slider.Root
					type="multiple"
					value={[parameters.confidence_threshold]}
					onValueChange={(v: number[]) => handleSliderChange('confidence_threshold', v)}
					min={0}
					max={1}
					step={0.05}
					{disabled}
				/>
			</div>

		</div>
	</div>
</div>
