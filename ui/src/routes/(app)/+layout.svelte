<script lang="ts">
	import type { Snippet } from 'svelte';
	import Header from '$lib/components/Header.svelte';
	import Navigation from '$lib/components/Navigation.svelte';

	let { children }: { children: Snippet } = $props();
</script>

<div class="app-layout">
	<Header />
	<Navigation />
	<main class="main-content">
		{@render children()}
	</main>
</div>

<style>
	.app-layout {
		min-height: 100vh;
		padding-top: 60px; /* Header height */
	}

	.main-content {
		margin-left: 240px; /* Sidebar width on desktop */
		min-height: calc(100vh - 60px);
		background: var(--bg-page);
	}

	/* Mobile styles */
	@media (max-width: 768px) {
		.main-content {
			margin-left: 0;
			padding-bottom: 70px; /* Bottom nav height */
		}
	}
</style>
