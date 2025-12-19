<script lang="ts">
	import { Select, Slider, Label } from '$lib/components/ui';
	import type { TuningParametersInput } from '$lib/schemas';

	interface Props {
		parameters: TuningParametersInput;
		disabled?: boolean;
		class?: string;
	}

	let { 
		parameters = $bindable(), 
		disabled = false,
		class: className = ''
	}: Props = $props();

	// Helper for Slider array binding
	function handleSliderChange(key: keyof TuningParametersInput, val: number[]) {
		(parameters as any)[key] = val[0];
	}
</script>

<div class="space-y-4 {className}">
	<h3 class="font-bold text-gray-900 mb-4">Tuning Parameters</h3>

	<div class="grid grid-cols-2 gap-4">
		<!-- Model Selection -->
		<div class="col-span-2 space-y-2">
			<Label.Root>Model</Label.Root>
			<Select.Root type="single" bind:value={parameters.model_name} {disabled}>
				<Select.Trigger class="w-full">
					{parameters.model_name || 'Select a model'}
				</Select.Trigger>
				<Select.Content>
					<Select.Item value="gemini-2.0-flash" label="Gemini 2.0 flash" />
					<Select.Item value="gemini-1.5-pro" label="Gemini 1.5 pro" />
					<Select.Item value="gemini-1.5-flash" label="Gemini 1.5 flash" />
				</Select.Content>
			</Select.Root>
		</div>

		<!-- Temperature -->
		<div class="space-y-2">
			<div class="flex items-center justify-between">
				<Label.Root>Temperature</Label.Root>
				<span class="text-xs font-mono bg-gray-100 px-1.5 py-0.5 rounded"
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

		<!-- Initial Retrieval Count -->
		<div class="space-y-2">
			<div class="flex items-center justify-between">
				<Label.Root>Initial Retrieval</Label.Root>
				<span class="text-xs font-mono bg-gray-100 px-1.5 py-0.5 rounded"
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
		<div class="space-y-2">
			<div class="flex items-center justify-between">
				<Label.Root>Final Top K</Label.Root>
				<span class="text-xs font-mono bg-gray-100 px-1.5 py-0.5 rounded"
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
		<div class="space-y-2">
			<div class="flex items-center justify-between">
				<Label.Root>Rerank Threshold</Label.Root>
				<span class="text-xs font-mono bg-gray-100 px-1.5 py-0.5 rounded"
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

		<!-- Aggregated Rule Limit -->
		<div class="space-y-2">
			<div class="flex items-center justify-between">
				<Label.Root>Rule Limit</Label.Root>
				<span class="text-xs font-mono bg-gray-100 px-1.5 py-0.5 rounded"
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

		<!-- Min Sentence Length -->
		<div class="space-y-2">
			<div class="flex items-center justify-between">
				<Label.Root>Min Sentence Length</Label.Root>
				<span class="text-xs font-mono bg-gray-100 px-1.5 py-0.5 rounded"
					>{parameters.min_sentence_length}</span
				>
			</div>
			<Slider.Root
				type="multiple"
				value={[parameters.min_sentence_length]}
				onValueChange={(v: number[]) => handleSliderChange('min_sentence_length', v)}
				min={1}
				max={50}
				step={1}
				{disabled}
			/>
		</div>

		<!-- Max Agent Iterations -->
		<div class="space-y-2">
			<div class="flex items-center justify-between">
				<Label.Root>Max Iterations</Label.Root>
				<span class="text-xs font-mono bg-gray-100 px-1.5 py-0.5 rounded"
					>{parameters.max_agent_iterations}</span
				>
			</div>
			<Slider.Root
				type="multiple"
				value={[parameters.max_agent_iterations]}
				onValueChange={(v: number[]) => handleSliderChange('max_agent_iterations', v)}
				min={1}
				max={10}
				step={1}
				{disabled}
			/>
		</div>

		<!-- Confidence Threshold -->
		<div class="space-y-2">
			<div class="flex items-center justify-between">
				<Label.Root>Confidence Threshold</Label.Root>
				<span class="text-xs font-mono bg-gray-100 px-1.5 py-0.5 rounded"
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
