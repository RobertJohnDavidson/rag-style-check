<script lang="ts">
	import { ErrorBoundary, Modal } from '$lib/components/ui';
	import { CreateTab, BrowseTab, RunTab } from '$lib/components/tabs';
	// Active tab state
	let activeTab: 'create' | 'browse' | 'run' = $state('create');

	// Selected test ID for Run tab (passed from Browse tab)
	let runTestId: string | undefined = $state();

	// Track unsaved changes in CreateTab
	let hasUnsavedChanges = $state(false);
	let createTabResetFn: (() => void) | null = null;

	// Modal state for unsaved changes
	let showUnsavedModal = $state(false);
	let pendingTab: 'create' | 'browse' | 'run' | null = $state(null);

	// Scroll container reference
	let scrollContainer: HTMLDivElement | undefined = $state();

	function handleTabChange(newTab: 'create' | 'browse' | 'run') {
		// Check for unsaved changes
		if (activeTab === 'create' && hasUnsavedChanges && newTab !== 'create') {
			pendingTab = newTab;
			showUnsavedModal = true;
			return;
		}

		// Switch tab
		switchTab(newTab);
	}

	function switchTab(newTab: 'create' | 'browse' | 'run') {
		activeTab = newTab;
		pendingTab = null;
		showUnsavedModal = false;

		// Reset scroll position
		if (scrollContainer) {
			scrollContainer.scrollTop = 0;
		}
	}

	function handleUnsavedConfirm() {
		if (pendingTab) {
			if (createTabResetFn) {
				createTabResetFn();
			}
			switchTab(pendingTab);
		}
	}

	function handleUnsavedCancel() {
		pendingTab = null;
		showUnsavedModal = false;
	}

	function handleSelectTestForRun(testId: string) {
		runTestId = testId;
		handleTabChange('run');
	}

	// Keyboard navigation
	function handleKeydown(event: KeyboardEvent) {
		// Ctrl/Cmd + 1/2/3 to switch tabs
		if ((event.ctrlKey || event.metaKey) && !event.shiftKey) {
			if (event.key === '1') {
				event.preventDefault();
				handleTabChange('create');
			} else if (event.key === '2') {
				event.preventDefault();
				handleTabChange('browse');
			} else if (event.key === '3') {
				event.preventDefault();
				handleTabChange('run');
			}
		}
	}
</script>

<svelte:window onkeydown={handleKeydown} />

<ErrorBoundary>
	<div class="min-h-screen bg-linear-to-br from-blue-50 to-indigo-100 p-8">
		<div class="max-w-7xl mx-auto">
			<!-- Header -->
			<div class="mb-8">
				<h1 class="text-4xl font-bold text-gray-900 mb-2">Test Management</h1>
				<p class="text-gray-600">Create, browse, and run style checker tests</p>
				<a href="/" class="text-[#CC0000] hover:text-[#A30000] text-sm mt-2 inline-block">
					← Back to Auditor
				</a>
			</div>

			<!-- Tabs -->
			<div class="bg-white rounded-lg shadow-lg mb-6">
				<div class="border-b border-gray-200">
					<div class="flex -mb-px" role="tablist">
						<button
							role="tab"
							aria-selected={activeTab === 'create'}
							aria-controls="create-panel"
							onclick={() => handleTabChange('create')}
							class="px-6 py-4 text-sm font-medium border-b-2 transition-colors {activeTab === 'create'
								? 'border-[#CC0000] text-[#CC0000]'
								: 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'}"
						>
							Create Test
							<span class="sr-only">(Ctrl/Cmd + 1)</span>
						</button>
						<button
							role="tab"
							aria-selected={activeTab === 'browse'}
							aria-controls="browse-panel"
							onclick={() => handleTabChange('browse')}
							class="px-6 py-4 text-sm font-medium border-b-2 transition-colors {activeTab === 'browse'
								? 'border-[#CC0000] text-[#CC0000]'
								: 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'}"
						>
							Browse Tests
							<span class="sr-only">(Ctrl/Cmd + 2)</span>
						</button>
						<button
							role="tab"
							aria-selected={activeTab === 'run'}
							aria-controls="run-panel"
							onclick={() => handleTabChange('run')}
							class="px-6 py-4 text-sm font-medium border-b-2 transition-colors {activeTab === 'run'
								? 'border-[#CC0000] text-[#CC0000]'
								: 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'}"
						>
							Run Test
							<span class="sr-only">(Ctrl/Cmd + 3)</span>
						</button>
					</div>
				</div>

				<!-- Tab Content with scroll reset -->
				<div class="p-6 overflow-y-auto" bind:this={scrollContainer}>
				{#if activeTab === 'create'}
					<div role="tabpanel" id="create-panel" aria-labelledby="create-tab">
						<CreateTab 
							onUnsavedChanges={(hasChanges) => hasUnsavedChanges = hasChanges}
							onRegisterReset={(resetFn) => createTabResetFn = resetFn}
						/>
					</div>
					{:else if activeTab === 'browse'}
						<div role="tabpanel" id="browse-panel" aria-labelledby="browse-tab">
							<BrowseTab onSelectTest={handleSelectTestForRun} />
						</div>
					{:else if activeTab === 'run'}
						<div role="tabpanel" id="run-panel" aria-labelledby="run-tab">
							<RunTab testId={runTestId} />
						</div>
					{/if}
				</div>
			</div>
		</div>
	</div>

	<!-- Unsaved Changes Modal -->
	<Modal
		bind:isOpen={showUnsavedModal}
		title="Unsaved Changes"
		onConfirm={handleUnsavedConfirm}
		onCancel={handleUnsavedCancel}
		confirmText="Discard Changes"
		cancelText="Keep Editing"
	>
		<p>You have unsaved changes in the Create tab. Do you want to discard them?</p>
	</Modal>
</ErrorBoundary>

<style>
	:global(body) {
		margin: 0;
		padding: 0;
		font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
	}
</style>
