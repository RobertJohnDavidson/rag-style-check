<script lang="ts">
	import type { ExpectedViolation, Test } from '$lib/types';
	import { Input, Button, Alert, Label } from '$lib/components/ui';
	import { TestPreview } from '$lib/components/tests';
	import { CBCArticleUrlSchema } from '$lib/schemas';
	import { generateTests as apiGenerateTests, createTest as apiCreateTest } from '$lib/api';
	import { LoaderCircle, Info } from '@lucide/svelte';

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
		<div class="space-y-2">
			<Label.Root>CBC Article URL</Label.Root>
			<Input.Root
				type="url"
				bind:value={articleUrl}
				placeholder="https://www.cbc.ca/news/..."
				disabled={loading}
				required
			/>
			{#if urlError}
				<p class="text-xs text-destructive">{urlError}</p>
			{:else}
				<p class="text-xs text-gray-500">Enter a valid CBC article URL to generate a test</p>
			{/if}
		</div>

		<Button.Root onclick={handleGenerate} disabled={loading || !articleUrl} class="w-full">
			{#if loading}
				<LoaderCircle class="mr-2 h-4 w-4 animate-spin" />
			{/if}
			Generate Test from Article
		</Button.Root>
	{:else}
		<Alert.Root>
			<Info class="h-4 w-4" />
			<Alert.Title>Generated Test - Review and Edit</Alert.Title>
			<Alert.Description>Review and modify the generated test before saving</Alert.Description>
		</Alert.Root>

		<TestPreview test={previewTest} onSave={handleSave} onCancel={handleCancel} {loading} />
	{/if}

	{#if error}
		<Alert.Root variant="destructive">
			<Alert.Description>{error}</Alert.Description>
		</Alert.Root>
	{/if}

	{#if success}
		<Alert.Root class="bg-green-50 text-green-700 border-green-200">
			<Alert.Description>{success}</Alert.Description>
		</Alert.Root>
	{/if}
</div>
