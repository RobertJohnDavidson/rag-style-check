<script lang="ts">

	let text = $state('');
	let violations = $state<Array<{ text: string; rule: string; reason: string; source_url?: string }>>([]);
	let loading = $state(false);
	let error = $state('');
	let processingTime = $state(0);

	async function auditText() {
		if (!text.trim()) {
			error = 'Please enter some text to audit';
			return;
		}

		loading = true;
		error = '';
		violations = [];


		try {
			const response = await fetch('http://localhost:8000/audit', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({ text })
			});

			if (!response.ok) {
				throw new Error(`API error: ${response.statusText}`);
			}

			const data = await response.json();
			violations = data.violations;
			processingTime = data.metadata?.processing_time_seconds || 0;

			if (violations.length === 0) {
				error = 'No style violations found! ✓';
			}
		} catch (err) {
			error = `Error: ${err instanceof Error ? err.message : 'Failed to connect to API'}`;
			console.error('Audit error:', err);
		} finally {
			loading = false;
		}
	}

	function clearText() {
		text = '';
		violations = [];
		error = '';
		processingTime = 0;
	}

	function highlightViolation(violationText: string) {
		// Find and highlight the violation text in the main text
		const index = text.indexOf(violationText);
		if (index !== -1) {
			text = text.substring(0, index) + text.substring(index + violationText.length);
		}
	}
</script>

<div class="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-8">
	<div class="max-w-6xl mx-auto">
		<!-- Header -->
		<div class="mb-8">
			<h1 class="text-4xl font-bold text-gray-900 mb-2">CBC News Style Checker</h1>
			<p class="text-gray-600">Check your text against CBC News style guidelines using AI</p>
		</div>

		<div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
			<!-- Main Input Panel -->
			<div class="lg:col-span-2">
				<div class="bg-white rounded-lg shadow-lg p-6">
					<label for="text-input" class="block text-sm font-semibold text-gray-700 mb-4">
						Paste your text here:
					</label>
					<textarea
						id="text-input"
						bind:value={text}
						placeholder="Enter the text you want to audit..."
						class="w-full h-64 p-4 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent resize-none"
						disabled={loading}
					></textarea>

					<div class="mt-4 flex gap-3">
						<button
							onclick={auditText}
							disabled={loading || !text.trim()}
							class="flex-1 bg-indigo-600 hover:bg-indigo-700 disabled:bg-gray-400 text-white font-semibold py-3 px-6 rounded-lg transition"
						>
							{loading ? '🔄 Auditing...' : '✓ Audit Text'}
						</button>
						<button
							onclick={clearText}
							disabled={loading}
							class="bg-gray-300 hover:bg-gray-400 disabled:bg-gray-200 text-gray-800 font-semibold py-3 px-6 rounded-lg transition"
						>
							Clear
						</button>
					</div>

					<!-- Status Messages -->
					{#if error}
						<div
							class="mt-4 p-4 rounded-lg {error.includes('No style')
								? 'bg-green-100 text-green-800'
								: 'bg-red-100 text-red-800'}"
						>
							{error}
						</div>
					{/if}

					{#if processingTime > 0}
						<div class="mt-3 text-xs text-gray-500">
							Processing time: {processingTime.toFixed(2)}s
						</div>
					{/if}
				</div>
			</div>

			<!-- Sidebar Info -->
			<div class="lg:col-span-1">
				<div class="bg-white rounded-lg shadow-lg p-6">
					<h2 class="text-lg font-bold text-gray-900 mb-4">📊 Statistics</h2>
					<div class="space-y-3">
						<div>
							<div class="text-2xl font-bold text-indigo-600">{violations.length}</div>
							<div class="text-sm text-gray-600">Violations found</div>
						</div>
						<div class="pt-4 border-t border-gray-200">
							<div class="text-sm font-semibold text-gray-700 mb-2">How it works:</div>
							<ul class="text-xs text-gray-600 space-y-2">
								<li>✓ Paste your text</li>
								<li>✓ Click "Audit Text"</li>
								<li>✓ Review violations below</li>
								<li>✓ Check source guides</li>
							</ul>
						</div>
					</div>
				</div>
			</div>
		</div>

		<!-- Violations Display -->
		{#if violations.length > 0}
			<div class="mt-8">
				<h2 class="text-2xl font-bold text-gray-900 mb-4">Style Violations Found</h2>
				<div class="space-y-4">
					{#each violations as violation, i (i)}
						<div class="bg-white rounded-lg shadow-md p-6 border-l-4 border-red-500">
							<div class="flex justify-between items-start mb-2">
								<h3 class="font-bold text-gray-900">{violation.rule}</h3>
								<span class="text-xs bg-red-100 text-red-800 px-3 py-1 rounded-full">
									Issue #{i + 1}
								</span>
							</div>

							<div class="bg-red-50 p-3 rounded mb-3 font-mono text-sm text-gray-800">
								"{violation.text}"
							</div>

							<p class="text-gray-700 text-sm mb-4">{violation.reason}</p>

							{#if violation.source_url}
								<a
									href={violation.source_url}
									target="_blank"
									rel="noopener noreferrer"
									class="text-indigo-600 hover:text-indigo-800 text-sm font-semibold inline-flex items-center gap-1"
								>
									📖 View in Style Guide
									<span>→</span>
								</a>
							{/if}
						</div>
					{/each}
				</div>
			</div>
		{/if}
	</div>
</div>

<style>
	:global(body) {
		margin: 0;
		padding: 0;
		font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue',
			Arial, sans-serif;
	}
</style>
