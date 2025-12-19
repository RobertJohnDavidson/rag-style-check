<script lang="ts">
	import { Tabs } from "$lib/components/ui";

	interface Props {
		currentMode: 'manual' | 'generate' | 'test';
		onModeChange: (mode: 'manual' | 'generate' | 'test') => void;
	}

	let { currentMode, onModeChange }: Props = $props();

	function handleValueChange(value: string | undefined) {
		if (value) {
			onModeChange(value as 'manual' | 'generate' | 'test');
		}
	}
</script>

<Tabs.Root value={currentMode} onValueChange={handleValueChange} class="w-full mb-6">
	<Tabs.List class="grid w-full grid-cols-3">
		<Tabs.Trigger value="manual">Manual Entry</Tabs.Trigger>
		<Tabs.Trigger value="generate">Generate Text</Tabs.Trigger>
		<Tabs.Trigger value="test">Existing Test</Tabs.Trigger>
	</Tabs.List>
</Tabs.Root>
