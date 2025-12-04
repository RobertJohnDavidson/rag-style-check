<script lang="ts">
	import type { ExpectedViolation, Test } from '$lib/types';
	import { Input, Button, Alert } from '$lib/components/ui';
	import { TestPreview } from '$lib/components/tests';
	import { CBCArticleUrlSchema } from '$lib/schemas';
	import { generateTests as apiGenerateTests, createTest as apiCreateTest } from '$lib/api';

	interface Props {
		onUnsavedChanges?: (hasChanges: boolean) => void;
		onRegisterReset?: (resetFn: () => void) => void;
	}

	let { onUnsavedChanges, onRegisterReset }: Props = $props();

	// Local form state
	let articleUrl = $state('');
	let previewTest = $state<Test>({
		id: '',
		label: '',
		text: '',
		expected_violations: [],
		generation_method: 'article',
		notes: '',
		created_at: new Date().toISOString()
	});
	let showPreview = $state(false);
	let loading = $state(false);
	let error = $state('');
	let success = $state('');
	let urlError = $state('');

	// Track unsaved changes
	$effect(() => {
		const hasChanges = articleUrl !== '' || showPreview;
		onUnsavedChanges?.(hasChanges);
	});

	// Register reset function
	$effect(() => {
		if (onRegisterReset) {
			onRegisterReset(resetForm);
		}
	});

	function resetForm() {
		articleUrl = '';
		previewTest = {
			id: '',
			label: '',
			text: '',
			expected_violations: [],
			generation_method: 'article',
			notes: '',
			created_at: new Date().toISOString()
		};
		showPreview = false;
		error = '';
		success = '';
		urlError = '';
	}

	async function handleGenerate() {
		// Validate URL
		const result = CBCArticleUrlSchema.safeParse(articleUrl);
		if (!result.success) {
			urlError = result.error.issues[0].message;
			return;
		}

		urlError = '';
		error = '';
		loading = true;
		showPreview = false;

		const response = await apiGenerateTests({ article_url: result.data });

		loading = false;

		if (response.error) {
			error = response.error;
		} else if (response.data && response.data.tests.length > 0) {
			// Take first test and populate form
			const test = response.data.tests[0];
			previewTest = {
				id: '',
				label: test.label,
				text: test.text,
				expected_violations: test.expected_violations,
				generation_method: 'article',
				notes: '',
				created_at: new Date().toISOString()
			};
			showPreview = true;
		} else {
			error = 'No test generated from article';
		}
	}

	async function handleSave() {
		const testInput = {
			label: previewTest.label,
			text: previewTest.text,
			expected_violations: previewTest.expected_violations,
			generation_method: 'article' as const,
			...(previewTest.notes ? { notes: previewTest.notes } : {})
		};

		loading = true;
		error = '';

		const response = await apiCreateTest(testInput);

		loading = false;

		if (response.error) {
			error = response.error;
		} else {
			success = 'Test saved successfully!';
			setTimeout(() => {
				resetForm();
			}, 2000);
		}
	}

	function handleCancel() {
		resetForm();
	}
</script>

<div class="space-y-4">
	{#if !showPreview}
		<Input
			label="CBC Article URL"
			type="url"
			bind:value={articleUrl}
			placeholder="https://www.cbc.ca/news/..."
			error={urlError}
			disabled={loading}
			required
			autofocus
		/>
		
		<p class="text-xs text-gray-500">Enter a valid CBC article URL to generate a test</p>

		<Button
			variant="primary"
			onclick={handleGenerate}
			loading={loading}
			disabled={!articleUrl}
			class="w-full"
		>
			Generate Test from Article
		</Button>
	{:else}
		<Alert variant="info">
			<strong>Generated Test - Review and Edit</strong><br />
			Review and modify the generated test before saving
		</Alert>

		<TestPreview
			test={previewTest}
			onSave={handleSave}
			onCancel={handleCancel}
			loading={loading}
		/>
	{/if}

	{#if error}
		<Alert variant="error">{error}</Alert>
	{/if}

	{#if success}
		<Alert variant="success">{success}</Alert>
	{/if}
</div>