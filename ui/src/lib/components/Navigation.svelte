<script lang="ts">
	import { page } from '$app/stores';
	import { _ } from '$lib/i18n';

	interface NavItem {
		href: string;
		labelKey: string;
		icon: string;
	}

	let budgetId = $derived($page.params.id || '');
	let hasBudgetId = $derived(budgetId && budgetId.length > 0);

	// All 8 navigation items for desktop sidebar
	let allNavItems: NavItem[] = $derived([
		{
			href: `/budgets/${budgetId}`,
			labelKey: 'nav.dashboard',
			icon: 'home'
		},
		{
			href: `/budgets/${budgetId}/pengekasser`,
			labelKey: 'nav.pengekasser',
			icon: 'wallet'
		},
		{
			href: `/budgets/${budgetId}/sparegrise`,
			labelKey: 'nav.sparegrise',
			icon: 'piggy-bank'
		},
		{
			href: `/budgets/${budgetId}/gaeldsbyrder`,
			labelKey: 'nav.gaeldsbyrder',
			icon: 'landmark'
		},
		{
			href: `/budgets/${budgetId}/budget-posts`,
			labelKey: 'nav.budgetPosts',
			icon: 'layers'
		},
		{
			href: `/budgets/${budgetId}/transactions`,
			labelKey: 'nav.transactions',
			icon: 'list'
		},
		{
			href: `/budgets/${budgetId}/forecast`,
			labelKey: 'nav.forecast',
			icon: 'trending-up'
		},
		{
			href: `/budgets/${budgetId}/settings`,
			labelKey: 'nav.settings',
			icon: 'settings'
		}
	]);

	// 5 primary items for mobile bottom bar (4 items + "Mere")
	let mobileNavItems: NavItem[] = $derived([
		{
			href: `/budgets/${budgetId}`,
			labelKey: 'nav.dashboard',
			icon: 'home'
		},
		{
			href: `/budgets/${budgetId}/budget-posts`,
			labelKey: 'nav.budgetPosts',
			icon: 'layers'
		},
		{
			href: `/budgets/${budgetId}/transactions`,
			labelKey: 'nav.transactions',
			icon: 'list'
		},
		{
			href: `/budgets/${budgetId}/forecast`,
			labelKey: 'nav.forecast',
			icon: 'trending-up'
		}
	]);

	// Items hidden in "Mere" popup on mobile
	let moreNavItems: NavItem[] = $derived([
		{
			href: `/budgets/${budgetId}/pengekasser`,
			labelKey: 'nav.pengekasser',
			icon: 'wallet'
		},
		{
			href: `/budgets/${budgetId}/sparegrise`,
			labelKey: 'nav.sparegrise',
			icon: 'piggy-bank'
		},
		{
			href: `/budgets/${budgetId}/gaeldsbyrder`,
			labelKey: 'nav.gaeldsbyrder',
			icon: 'landmark'
		},
		{
			href: `/budgets/${budgetId}/settings`,
			labelKey: 'nav.settings',
			icon: 'settings'
		}
	]);

	let showMore = $state(false);

	function isActive(itemHref: string): boolean {
		const currentPath = $page.url.pathname;
		// Exact match for dashboard
		if (itemHref === `/budgets/${budgetId}`) {
			return currentPath === itemHref;
		}
		// Prefix match for other pages
		return currentPath.startsWith(itemHref);
	}

	// Check if "Mere" button should be active (any of its items is active)
	function isMoreActive(): boolean {
		return moreNavItems.some((item) => isActive(item.href));
	}

	function toggleMore() {
		showMore = !showMore;
	}

	function closeMore() {
		showMore = false;
	}

	function handleMoreItemClick() {
		showMore = false;
	}

	function handleBackdropClick(event: MouseEvent) {
		if (event.target === event.currentTarget) {
			closeMore();
		}
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape' && showMore) {
			closeMore();
		}
	}

	function getIconSvg(icon: string): string {
		switch (icon) {
			case 'home':
				return '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>';
			case 'wallet':
				return '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 7V4a1 1 0 0 0-1-1H5a2 2 0 0 0 0 4h15a1 1 0 0 1 1 1v4h-3a2 2 0 0 0 0 4h3a1 1 0 0 0 1-1v-2a1 1 0 0 0-1-1"/><path d="M3 5v14a2 2 0 0 0 2 2h15a1 1 0 0 0 1-1v-4"/></svg>';
			case 'piggy-bank':
				return '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 5c-1.5 0-2.8 1.4-3 2-3.5-1.5-11-.3-11 5 0 1.8 0 3 2 4.5V20h4v-2h3v2h4v-4c1-.5 1.7-1 2-2h2v-4h-2c0-1-.5-1.5-1-2"/><path d="M2 9.5a1 1 0 0 1 1-1 4.5 4.5 0 0 1 3 1.5"/><circle cx="14.5" cy="10.5" r=".5" fill="currentColor"/></svg>';
			case 'landmark':
				return '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="3" x2="21" y1="22" y2="22"/><line x1="6" x2="6" y1="18" y2="11"/><line x1="10" x2="10" y1="18" y2="11"/><line x1="14" x2="14" y1="18" y2="11"/><line x1="18" x2="18" y1="18" y2="11"/><polygon points="12 2 20 7 4 7"/></svg>';
			case 'list':
				return '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="8" x2="21" y1="6" y2="6"/><line x1="8" x2="21" y1="12" y2="12"/><line x1="8" x2="21" y1="18" y2="18"/><line x1="3" x2="3.01" y1="6" y2="6"/><line x1="3" x2="3.01" y1="12" y2="12"/><line x1="3" x2="3.01" y1="18" y2="18"/></svg>';
			case 'layers':
				return '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m12.83 2.18a2 2 0 0 0-1.66 0L2.6 6.08a1 1 0 0 0 0 1.83l8.58 3.91a2 2 0 0 0 1.66 0l8.58-3.9a1 1 0 0 0 0-1.83Z"/><path d="m22 17.65-9.17 4.16a2 2 0 0 1-1.66 0L2 17.65"/><path d="m22 12.65-9.17 4.16a2 2 0 0 1-1.66 0L2 12.65"/></svg>';
			case 'trending-up':
				return '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/></svg>';
			case 'settings':
				return '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/></svg>';
			case 'ellipsis':
				return '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/><circle cx="5" cy="12" r="1"/></svg>';
			default:
				return '';
		}
	}
</script>

<svelte:window onkeydown={handleKeydown} />

{#if hasBudgetId}
	<!-- Desktop Sidebar -->
	<nav class="nav-sidebar">
		{#each allNavItems as item}
			<a href={item.href} class="nav-item" class:active={isActive(item.href)}>
				<span class="nav-icon">{@html getIconSvg(item.icon)}</span>
				<span class="nav-label">{$_(item.labelKey)}</span>
			</a>
		{/each}
	</nav>

	<!-- Mobile Bottom Bar -->
	<nav class="nav-bottom">
		{#each mobileNavItems as item}
			<a href={item.href} class="nav-item" class:active={isActive(item.href)}>
				<span class="nav-icon">{@html getIconSvg(item.icon)}</span>
				<span class="nav-label">{$_(item.labelKey)}</span>
			</a>
		{/each}

		<!-- Mere button -->
		<button type="button" class="nav-item nav-more" class:active={isMoreActive()} onclick={toggleMore}>
			<span class="nav-icon">{@html getIconSvg('ellipsis')}</span>
			<span class="nav-label">{$_('nav.more')}</span>
		</button>
	</nav>

	<!-- More popup (mobile only) -->
	{#if showMore}
		<div
			class="more-backdrop"
			role="presentation"
			tabindex="0"
			onclick={handleBackdropClick}
			onkeydown={(e) => e.key === 'Enter' && closeMore()}
		>
			<div class="more-popup">
				{#each moreNavItems as item}
					<a
						href={item.href}
						class="more-item"
						class:active={isActive(item.href)}
						onclick={handleMoreItemClick}
					>
						<span class="more-icon">{@html getIconSvg(item.icon)}</span>
						<span class="more-label">{$_(item.labelKey)}</span>
					</a>
				{/each}
			</div>
		</div>
	{/if}
{:else}
	<!-- Empty state when no budget selected -->
	<nav class="nav-sidebar empty">
		<div class="empty-nav-message">
			<p>{$_('budget.messages.noBudgetSelected')}</p>
			<p class="hint">{$_('budget.messages.createFirst')}</p>
		</div>
	</nav>

	<nav class="nav-bottom empty">
		<div class="empty-nav-message">
			<p>{$_('budget.messages.noBudgetSelected')}</p>
		</div>
	</nav>
{/if}

<style>
	/* Desktop Sidebar */
	.nav-sidebar {
		position: fixed;
		left: 0;
		top: 60px; /* Below header */
		width: 240px;
		height: calc(100vh - 60px);
		background: var(--bg-card);
		border-right: 1px solid var(--border);
		padding: var(--spacing-lg);
		display: flex;
		flex-direction: column;
		gap: var(--spacing-xs);
	}

	.nav-sidebar .nav-item {
		display: flex;
		align-items: center;
		gap: var(--spacing-md);
		padding: var(--spacing-md);
		border-radius: var(--radius-md);
		text-decoration: none;
		color: var(--text-secondary);
		transition: all 0.2s;
	}

	.nav-sidebar .nav-item:hover {
		background: var(--bg-page);
		color: var(--text-primary);
	}

	.nav-sidebar .nav-item:focus-visible {
		outline: 2px solid var(--accent);
		outline-offset: -2px;
	}

	.nav-sidebar .nav-item.active {
		background: color-mix(in srgb, var(--accent) 10%, transparent);
		color: var(--accent);
		font-weight: 500;
	}

	.nav-sidebar .nav-icon {
		width: 24px;
		height: 24px;
		display: flex;
		align-items: center;
		justify-content: center;
		flex-shrink: 0;
	}

	.nav-sidebar .nav-label {
		font-size: var(--font-size-base);
	}

	.nav-sidebar.empty {
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.empty-nav-message {
		text-align: center;
		padding: var(--spacing-lg);
		color: var(--text-secondary);
	}

	.empty-nav-message p {
		font-size: var(--font-size-base);
		margin-bottom: var(--spacing-sm);
	}

	.empty-nav-message .hint {
		font-size: var(--font-size-sm);
		color: var(--text-tertiary);
	}

	/* Mobile Bottom Bar */
	.nav-bottom {
		display: none;
	}

	.more-backdrop {
		display: none;
	}

	.more-popup {
		display: none;
	}

	/* Mobile styles */
	@media (max-width: 768px) {
		.nav-sidebar {
			display: none;
		}

		.nav-bottom {
			position: fixed;
			bottom: 0;
			left: 0;
			right: 0;
			height: 70px;
			background: var(--bg-card);
			border-top: 1px solid var(--border);
			display: flex;
			justify-content: space-around;
			align-items: center;
			padding: var(--spacing-sm) var(--spacing-md);
			z-index: 100;
		}

		.nav-bottom.empty .empty-nav-message {
			width: 100%;
		}

		.nav-bottom.empty .empty-nav-message p {
			font-size: var(--font-size-sm);
			margin-bottom: 0;
		}

		.nav-bottom .nav-item {
			position: relative;
			display: flex;
			flex-direction: column;
			align-items: center;
			gap: var(--spacing-xs);
			padding: var(--spacing-xs);
			text-decoration: none;
			color: var(--text-secondary);
			flex: 1;
			max-width: 80px;
		}

		.nav-bottom .nav-more {
			background: none;
			border: none;
			cursor: pointer;
			font-family: inherit;
		}

		.nav-bottom .nav-item:focus-visible {
			outline: 2px solid var(--accent);
			outline-offset: -2px;
			border-radius: var(--radius-sm);
		}

		.nav-bottom .nav-item.active {
			color: var(--accent);
		}

		.nav-bottom .nav-item.active::after {
			content: '';
			position: absolute;
			bottom: 0;
			left: 50%;
			transform: translateX(-50%);
			width: 32px;
			height: 3px;
			background: var(--accent);
			border-radius: 2px 2px 0 0;
		}

		.nav-bottom .nav-icon {
			width: 24px;
			height: 24px;
			display: flex;
			align-items: center;
			justify-content: center;
		}

		.nav-bottom .nav-label {
			font-size: var(--font-size-sm);
			text-align: center;
			white-space: nowrap;
			overflow: hidden;
			text-overflow: ellipsis;
			max-width: 100%;
		}

		/* More popup */
		.more-backdrop {
			display: block;
			position: fixed;
			top: 0;
			left: 0;
			right: 0;
			bottom: 0;
			background: rgba(0, 0, 0, 0.3);
			z-index: 150;
		}

		.more-popup {
			display: block;
			position: fixed;
			bottom: 70px;
			left: var(--spacing-md);
			right: var(--spacing-md);
			background: var(--bg-card);
			border: 1px solid var(--border);
			border-radius: var(--radius-lg);
			box-shadow: 0 -4px 16px rgba(0, 0, 0, 0.2);
			padding: var(--spacing-sm);
			animation: slideUp 0.2s ease-out;
		}

		@keyframes slideUp {
			from {
				transform: translateY(20px);
				opacity: 0;
			}
			to {
				transform: translateY(0);
				opacity: 1;
			}
		}

		.more-item {
			display: flex;
			align-items: center;
			gap: var(--spacing-md);
			padding: var(--spacing-md);
			border-radius: var(--radius-md);
			text-decoration: none;
			color: var(--text-primary);
			transition: background 0.2s;
		}

		.more-item:hover {
			background: var(--bg-page);
		}

		.more-item.active {
			background: color-mix(in srgb, var(--accent) 10%, transparent);
			color: var(--accent);
			font-weight: 500;
		}

		.more-icon {
			width: 24px;
			height: 24px;
			display: flex;
			align-items: center;
			justify-content: center;
			color: var(--text-secondary);
		}

		.more-item.active .more-icon {
			color: var(--accent);
		}

		.more-label {
			font-size: var(--font-size-base);
		}
	}
</style>
