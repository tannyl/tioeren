<script lang="ts">
	import { page } from '$app/stores';
	import { _ } from '$lib/i18n';

	interface NavItem {
		href: string;
		labelKey: string;
		icon: string;
	}

	let budgetId = $derived($page.params.id || '');

	let navItems: NavItem[] = $derived([
		{
			href: `/budgets/${budgetId}`,
			labelKey: 'nav.dashboard',
			icon: 'home'
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

	function isActive(itemHref: string): boolean {
		const currentPath = $page.url.pathname;
		// Exact match for dashboard
		if (itemHref === `/budgets/${budgetId}`) {
			return currentPath === itemHref;
		}
		// Prefix match for other pages
		return currentPath.startsWith(itemHref);
	}

	function getIconSvg(icon: string): string {
		switch (icon) {
			case 'home':
				return '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><polyline points="9 22 9 12 15 12 15 22"/></svg>';
			case 'list':
				return '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="8" x2="21" y1="6" y2="6"/><line x1="8" x2="21" y1="12" y2="12"/><line x1="8" x2="21" y1="18" y2="18"/><line x1="3" x2="3.01" y1="6" y2="6"/><line x1="3" x2="3.01" y1="12" y2="12"/><line x1="3" x2="3.01" y1="18" y2="18"/></svg>';
			case 'trending-up':
				return '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/></svg>';
			case 'settings':
				return '<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/></svg>';
			default:
				return '';
		}
	}
</script>

<!-- Desktop Sidebar -->
<nav class="nav-sidebar">
	{#each navItems as item}
		<a href={item.href} class="nav-item" class:active={isActive(item.href)}>
			<span class="nav-icon">{@html getIconSvg(item.icon)}</span>
			<span class="nav-label">{$_(item.labelKey)}</span>
		</a>
	{/each}
</nav>

<!-- Mobile Bottom Bar -->
<nav class="nav-bottom">
	{#each navItems as item}
		<a href={item.href} class="nav-item" class:active={isActive(item.href)}>
			<span class="nav-icon">{@html getIconSvg(item.icon)}</span>
			<span class="nav-label">{$_(item.labelKey)}</span>
		</a>
	{/each}
</nav>

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

	/* Mobile Bottom Bar */
	.nav-bottom {
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
	}
</style>
