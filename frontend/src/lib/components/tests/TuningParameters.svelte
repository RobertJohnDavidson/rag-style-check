<script lang="ts">
	import { Select, Slider } from '$lib/components/ui';
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
</script>

<div class="space-y-4 {className}">
	<h3 class="font-bold text-gray-900 mb-4">Tuning Parameters</h3>
	
	<div class="grid grid-cols-2 gap-4">
		<!-- Model Selection -->
		<div class="col-span-2">
			<Select
				label="Model"
				bind:value={parameters.model_name}
				{disabled}
			>
				<option value="models/gemini-1.5-flash">Gemini 1.5 Flash</option>
				<option value="models/gemini-1.5-pro">Gemini 1.5 Pro</option>
				<option value="models/gemini-2.0-flash-thinking-exp">Gemini 2.0 Thinking</option>
			</Select>
		</div>

		<!-- Temperature -->
		<Slider
			label="Temperature"
			bind:value={parameters.temperature}
			min={0}
			max={2}
			step={0.1}
			{disabled}
			formatter={(v) => v.toFixed(1)}
		/>

		<!-- Initial Retrieval Count -->
		<Slider
			label="Initial Retrieval"
			bind:value={parameters.initial_retrieval_count}
			min={10}
			max={200}
			step={5}
			{disabled}
		/>

		<!-- Final Top K -->
		<Slider
			label="Final Top K"
			bind:value={parameters.final_top_k}
			min={5}
			max={100}
			step={5}
			{disabled}
		/>

		<!-- Rerank Score Threshold -->
		<Slider
			label="Rerank Threshold"
			bind:value={parameters.rerank_score_threshold}
			min={0}
			max={1}
			step={0.05}
			{disabled}
			formatter={(v) => v.toFixed(2)}
		/>

		<!-- Aggregated Rule Limit -->
		<Slider
			label="Rule Limit"
			bind:value={parameters.aggregated_rule_limit}
			min={10}
			max={100}
			step={5}
			{disabled}
		/>

		<!-- Min Sentence Length -->
		<Slider
			label="Min Sentence Length"
			bind:value={parameters.min_sentence_length}
			min={1}
			max={50}
			step={1}
			{disabled}
		/>

		<!-- Max Agent Iterations -->
		<Slider
			label="Max Iterations"
			bind:value={parameters.max_agent_iterations}
			min={1}
			max={10}
			step={1}
			{disabled}
		/>

		<!-- Confidence Threshold -->
		<Slider
			label="Confidence Threshold"
			bind:value={parameters.confidence_threshold}
			min={0}
			max={1}
			step={0.05}
			{disabled}
			formatter={(v) => v.toFixed(2)}
		/>
	</div>
</div>
