<script lang="ts">
	import { Button, Input, Card, Tabs, Label } from '$lib/components/ui';
	import { Plus, Trash2, Settings2, Copy } from '@lucide/svelte';
	import TuningParametersComponent from './TuningParameters.svelte';
	import type { TuningParameters, ModelInfo } from '$lib/types';

	interface ConfigProfile {
		id: string;
		label: string;
		params: TuningParameters;
	}

	interface Props {
		profiles: ConfigProfile[];
		models: ModelInfo[];
		onProfilesChange: (profiles: ConfigProfile[]) => void;
	}

	let { profiles = $bindable(), models = [], onProfilesChange }: Props = $props();
	let activeProfileId = $state('');

	$effect(() => {
		if (profiles.length > 0 && !activeProfileId) {
			activeProfileId = profiles[0].id;
		}
	});

	function addProfile() {
		const newId = crypto.randomUUID();
		const newProfile: ConfigProfile = {
			id: newId,
			label: `Config ${profiles.length + 1}`,
			// Deep copy the first profile's params or use defaults if available
			params: profiles.length > 0 ? JSON.parse(JSON.stringify(profiles[0].params)) : {
				model_name: models[0]?.name || '',
				temperature: 0.1,
				initial_retrieval_count: 50,
				final_top_k: 25,
				rerank_score_threshold: 0.5,
				aggregated_rule_limit: 50,
				max_agent_iterations: 2,
				include_thinking: false,
				use_query_fusion: true,
				use_llm_rerank: false,
				use_vertex_rerank: true,
				sparse_top_k: 10,
				num_fusion_queries: 3,
				max_violation_terms: 5
			}
		};
		profiles = [...profiles, newProfile];
		activeProfileId = newId;
		onProfilesChange(profiles);
	}

	function removeProfile(id: string) {
		if (profiles.length <= 1) return;
		profiles = profiles.filter(p => p.id !== id);
		if (activeProfileId === id) {
			activeProfileId = profiles[0].id;
		}
		onProfilesChange(profiles);
	}

	function duplicateProfile(profile: ConfigProfile) {
		const newId = crypto.randomUUID();
		const newProfile: ConfigProfile = {
			id: newId,
			label: `${profile.label} (Copy)`,
			params: JSON.parse(JSON.stringify(profile.params))
		};
		profiles = [...profiles, newProfile];
		activeProfileId = newId;
		onProfilesChange(profiles);
	}

	let activeProfile = $derived(profiles.find(p => p.id === activeProfileId));

</script>

<div class="space-y-6">
	<div class="flex items-center justify-between">
		<div class="space-y-1">
			<h3 class="text-lg font-bold">Configuration Profiles</h3>
			<p class="text-sm text-muted-foreground">Define sets of parameters to benchmark against</p>
		</div>
		<Button.Root variant="outline" size="sm" onclick={addProfile} class="gap-2">
			<Plus class="h-4 w-4" /> Add Profile
		</Button.Root>
	</div>

	<Tabs.Root value={activeProfileId} onValueChange={(v) => (activeProfileId = v)} class="w-full">
		<div class="flex items-center gap-2 overflow-x-auto pb-2 no-scrollbar">
			<Tabs.List class="justify-start bg-transparent h-auto p-0 gap-2">
				{#each profiles as profile}
					<Tabs.Trigger
						value={profile.id}
						class="px-4 py-2 h-10 gap-2 border border-transparent data-[state=active]:border-input"
					>
						<span class="truncate max-w-[200px] font-bold">{profile.label}</span>
					</Tabs.Trigger>
				{/each}
			</Tabs.List>
		</div>

		{#each profiles as profile}
			<Tabs.Content value={profile.id} class="mt-4 animate-in fade-in duration-300">
				<Card.Root>
					<Card.Content class="pt-6 space-y-6">
						<div class="grid grid-cols-1 md:grid-cols-2 gap-6 items-end">
							<div class="space-y-2">
								<Label.Root for="profile-label-{profile.id}">Profile Name</Label.Root>
								<Input.Root
									id="profile-label-{profile.id}"
									bind:value={profile.label}
									placeholder="e.g. Gemini Fast"
								/>
							</div>
							<div class="flex gap-2">
								<Button.Root
									variant="outline"
									class="flex-1 gap-2"
									onclick={() => duplicateProfile(profile)}
								>
									<Copy class="h-4 w-4" /> Duplicate
								</Button.Root>
								<Button.Root
									variant="destructive"
									size="icon"
									disabled={profiles.length <= 1}
									onclick={() => removeProfile(profile.id)}
								>
									<Trash2 class="h-4 w-4" />
								</Button.Root>
							</div>
						</div>

						<div class="pt-4 border-t">
							<TuningParametersComponent bind:parameters={profile.params} {models} />
						</div>
					</Card.Content>
				</Card.Root>
			</Tabs.Content>
		{/each}
	</Tabs.Root>
</div>

<style>
	.no-scrollbar::-webkit-scrollbar {
		display: none;
	}
	.no-scrollbar {
		-ms-overflow-style: none;
		scrollbar-width: none;
	}
</style>
