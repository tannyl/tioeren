<script lang="ts">
	// Mock data types
	type MockContainer = {
		id: string;
		name: string;
		purpose: 'pengekasse' | 'sparegris' | 'gaeld';
	};

	type MockAmountPattern = {
		id: string;
		amount: number; // in øre
		recurrence_label: string;
		start_date: string;
	};

	type MockBudgetPost = {
		id: string;
		direction: 'income' | 'expense' | 'transfer';
		category_path: string[] | null;
		category_name: string;
		amount_patterns: MockAmountPattern[];
		container_ids: string[];
		accumulate: boolean;
		transfer_from_container_id?: string;
		transfer_to_container_id?: string;
	};

	type TreeNode = {
		name: string;
		path: string[];
		post: MockBudgetPost | null;
		children: TreeNode[];
		budgetAmount: number;        // This node's own budget post amount (0 if pure category)
		childrenTotal: number;       // Sum of children's displayAmount
		displayAmount: number;       // What to show: leaf→budgetAmount, envelope→budgetAmount, category→childrenTotal
		isEnvelope: boolean;         // Has budget AND children (ceiling semantics apply)
		isOverAllocated: boolean;    // isEnvelope AND childrenTotal > budgetAmount
		postCount: number;
	};

	// Mock containers
	const containers: MockContainer[] = [
		{ id: 'c1', name: 'Lønkonto', purpose: 'pengekasse' },
		{ id: 'c2', name: 'Fælleskonto', purpose: 'pengekasse' },
		{ id: 'c3', name: 'Mastercard', purpose: 'pengekasse' },
		{ id: 'c4', name: 'Ferieopsparing', purpose: 'sparegris' },
		{ id: 'c5', name: 'Nødopsparing', purpose: 'sparegris' },
		{ id: 'c6', name: 'Billån', purpose: 'gaeld' }
	];

	// Mock budget posts
	const posts: MockBudgetPost[] = [
		// Income
		{
			id: 'i1',
			direction: 'income',
			category_path: ['Løn'],
			category_name: 'Løn',
			accumulate: false,
			amount_patterns: [
				{
					id: 'ap1',
					amount: 3200000,
					recurrence_label: 'd. 25 hver md',
					start_date: '2026-01-25'
				}
			]
		},
		{
			id: 'i2',
			direction: 'income',
			category_path: ['Løn', 'Partner'],
			category_name: 'Partner',
			accumulate: false,
			amount_patterns: [
				{
					id: 'ap2',
					amount: 2800000,
					recurrence_label: 'd. 28 hver md',
					start_date: '2026-01-28'
				}
			]
		},
		{
			id: 'i3',
			direction: 'income',
			category_path: ['Børnepenge'],
			category_name: 'Børnepenge',
			accumulate: false,
			amount_patterns: [
				{
					id: 'ap3',
					amount: 180000,
					recurrence_label: 'd. 20 hver md',
					start_date: '2026-01-20'
				}
			]
		},
		// Expenses - Bolig
		{
			id: 'e1',
			direction: 'expense',
			category_path: ['Bolig'],
			category_name: 'Bolig',
			accumulate: false,
			amount_patterns: [
				{
					id: 'ap4',
					amount: 1200000,
					recurrence_label: 'løbende',
					start_date: '2026-01-01'
				}
			]
		},
		{
			id: 'e2',
			direction: 'expense',
			category_path: ['Bolig', 'Husleje'],
			category_name: 'Husleje',
			accumulate: false,
			amount_patterns: [
				{
					id: 'ap5',
					amount: 850000,
					recurrence_label: 'd. 1 hver md',
					start_date: '2026-01-01'
				}
			]
		},
		{
			id: 'e3',
			direction: 'expense',
			category_path: ['Bolig', 'El & Varme'],
			category_name: 'El & Varme',
			accumulate: false,
			amount_patterns: [
				{
					id: 'ap6',
					amount: 120000,
					recurrence_label: 'd. 1 hver md',
					start_date: '2026-01-01'
				}
			]
		},
		{
			id: 'e4',
			direction: 'expense',
			category_path: ['Bolig', 'Forsikring'],
			category_name: 'Forsikring',
			accumulate: false,
			amount_patterns: [
				{
					id: 'ap7',
					amount: 80000,
					recurrence_label: 'd. 15 hvert kvartal',
					start_date: '2026-01-15'
				}
			]
		},
		{
			id: 'e5',
			direction: 'expense',
			category_path: ['Bolig', 'Internet'],
			category_name: 'Internet',
			accumulate: false,
			amount_patterns: [
				{
					id: 'ap8',
					amount: 29900,
					recurrence_label: 'd. 1 hver md',
					start_date: '2026-01-01'
				}
			]
		},
		// Expenses - Mad
		{
			id: 'e6',
			direction: 'expense',
			category_path: ['Mad'],
			category_name: 'Mad',
			accumulate: true,
			amount_patterns: [
				{
					id: 'ap9',
					amount: 500000,
					recurrence_label: 'løbende',
					start_date: '2026-01-01'
				}
			]
		},
		{
			id: 'e7',
			direction: 'expense',
			category_path: ['Mad', 'Dagligvarer'],
			category_name: 'Dagligvarer',
			accumulate: false,
			amount_patterns: [
				{
					id: 'ap10',
					amount: 400000,
					recurrence_label: 'løbende',
					start_date: '2026-01-01'
				}
			]
		},
		{
			id: 'e8',
			direction: 'expense',
			category_path: ['Mad', 'Take-away'],
			category_name: 'Take-away',
			accumulate: false,
			amount_patterns: [
				{
					id: 'ap11',
					amount: 80000,
					recurrence_label: 'løbende',
					start_date: '2026-01-01'
				}
			]
		},
		{
			id: 'e9',
			direction: 'expense',
			category_path: ['Mad', 'Frokostordning'],
			category_name: 'Frokostordning',
			accumulate: false,
			amount_patterns: [
				{
					id: 'ap12',
					amount: 60000,
					recurrence_label: 'd. 1 hver md',
					start_date: '2026-01-01'
				}
			]
		},
		// Expenses - Transport (structural parent)
		{
			id: 'e10',
			direction: 'expense',
			category_path: ['Transport', 'Benzin'],
			category_name: 'Benzin',
			accumulate: false,
			amount_patterns: [
				{
					id: 'ap13',
					amount: 150000,
					recurrence_label: 'løbende',
					start_date: '2026-01-01'
				}
			]
		},
		{
			id: 'e11',
			direction: 'expense',
			category_path: ['Transport', 'Parkering'],
			category_name: 'Parkering',
			accumulate: false,
			amount_patterns: [
				{
					id: 'ap14',
					amount: 30000,
					recurrence_label: 'løbende',
					start_date: '2026-01-01'
				}
			]
		},
		{
			id: 'e12',
			direction: 'expense',
			category_path: ['Transport', 'Vedligeholdelse'],
			category_name: 'Vedligeholdelse',
			accumulate: true,
			amount_patterns: [
				{
					id: 'ap15',
					amount: 50000,
					recurrence_label: 'løbende',
					start_date: '2026-01-01'
				}
			]
		},
		// Expenses - Personligt (multi-level)
		{
			id: 'e13',
			direction: 'expense',
			category_path: ['Personligt', 'Tøj'],
			category_name: 'Tøj',
			accumulate: false,
			amount_patterns: [
				{
					id: 'ap16',
					amount: 50000,
					recurrence_label: 'løbende',
					start_date: '2026-01-01'
				}
			]
		},
		{
			id: 'e14',
			direction: 'expense',
			category_path: ['Personligt', 'Fitness'],
			category_name: 'Fitness',
			accumulate: false,
			amount_patterns: [
				{
					id: 'ap17',
					amount: 37900,
					recurrence_label: 'd. 1 hver md',
					start_date: '2026-01-01'
				}
			]
		},
		{
			id: 'e15',
			direction: 'expense',
			category_path: ['Personligt', 'Abonnementer', 'Streaming'],
			category_name: 'Streaming',
			accumulate: false,
			amount_patterns: [
				{
					id: 'ap18',
					amount: 19900,
					recurrence_label: 'd. 15 hver md',
					start_date: '2026-01-15'
				}
			]
		},
		{
			id: 'e16',
			direction: 'expense',
			category_path: ['Personligt', 'Abonnementer', 'Mobil'],
			category_name: 'Mobil',
			accumulate: false,
			amount_patterns: [
				{
					id: 'ap19',
					amount: 14900,
					recurrence_label: 'd. 1 hver md',
					start_date: '2026-01-01'
				}
			]
		},
		{
			id: 'e17',
			direction: 'expense',
			category_path: ['Personligt', 'Abonnementer', 'Avis'],
			category_name: 'Avis',
			accumulate: false,
			amount_patterns: [
				{
					id: 'ap20',
					amount: 9900,
					recurrence_label: 'd. 1 hver md',
					start_date: '2026-01-01'
				}
			]
		},
		// Expenses - Børn
		{
			id: 'e18',
			direction: 'expense',
			category_path: ['Børn'],
			category_name: 'Børn',
			accumulate: false,
			amount_patterns: [
				{
					id: 'ap21',
					amount: 350000,
					recurrence_label: 'løbende',
					start_date: '2026-01-01'
				}
			]
		},
		{
			id: 'e19',
			direction: 'expense',
			category_path: ['Børn', 'Institution'],
			category_name: 'Institution',
			accumulate: false,
			amount_patterns: [
				{
					id: 'ap22',
					amount: 280000,
					recurrence_label: 'd. 5 hver md',
					start_date: '2026-01-05'
				}
			]
		},
		{
			id: 'e20',
			direction: 'expense',
			category_path: ['Børn', 'Aktiviteter'],
			category_name: 'Aktiviteter',
			accumulate: false,
			amount_patterns: [
				{
					id: 'ap23',
					amount: 40000,
					recurrence_label: 'løbende',
					start_date: '2026-01-01'
				}
			]
		},
		// Transfers
		{
			id: 't1',
			direction: 'transfer',
			category_path: null,
			category_name: 'Lønkonto → Ferieopsparing',
			accumulate: false,
			transfer_from_container_id: 'c1',
			transfer_to_container_id: 'c4',
			amount_patterns: [
				{
					id: 'ap24',
					amount: 200000,
					recurrence_label: 'd. 1 hver md',
					start_date: '2026-01-01'
				}
			]
		},
		{
			id: 't2',
			direction: 'transfer',
			category_path: null,
			category_name: 'Lønkonto → Nødopsparing',
			accumulate: false,
			transfer_from_container_id: 'c1',
			transfer_to_container_id: 'c5',
			amount_patterns: [
				{
					id: 'ap25',
					amount: 100000,
					recurrence_label: 'd. 1 hver md',
					start_date: '2026-01-01'
				}
			]
		},
		{
			id: 't3',
			direction: 'transfer',
			category_path: null,
			category_name: 'Lønkonto → Billån',
			accumulate: false,
			transfer_from_container_id: 'c1',
			transfer_to_container_id: 'c6',
			amount_patterns: [
				{
					id: 'ap26',
					amount: 350000,
					recurrence_label: 'd. 1 hver md',
					start_date: '2026-01-01'
				}
			]
		}
	];

	// Helper: format amount
	function formatAmount(oreAmount: number): string {
		return (oreAmount / 100).toLocaleString('da-DK', {
			minimumFractionDigits: 0,
			maximumFractionDigits: 0
		});
	}

	// Helper: get container name
	function getContainerName(id: string): string {
		return containers.find((c) => c.id === id)?.name || id;
	}

	// Helper: compute monthly amount from patterns
	function computeMonthlyAmount(patterns: MockAmountPattern[]): number {
		return patterns.reduce((sum, p) => sum + p.amount, 0);
	}

	// Build tree from flat posts
	function buildTree(direction: 'income' | 'expense' | 'transfer'): TreeNode[] {
		const directionPosts = posts.filter((p) => p.direction === direction);

		if (direction === 'transfer') {
			// Transfers are flat (no hierarchy)
			return directionPosts.map((p) => {
				const amount = computeMonthlyAmount(p.amount_patterns);
				return {
					name: p.category_name,
					path: [],
					post: p,
					children: [],
					budgetAmount: amount,
					childrenTotal: 0,
					displayAmount: amount,
					isEnvelope: false,
					isOverAllocated: false,
					postCount: 1
				};
			});
		}

		// Build hierarchical tree for income/expense
		const nodeMap = new Map<string, TreeNode>();

		// Create nodes for all posts
		for (const post of directionPosts) {
			if (!post.category_path) continue;

			const pathKey = post.category_path.join('/');
			if (!nodeMap.has(pathKey)) {
				nodeMap.set(pathKey, {
					name: post.category_name,
					path: post.category_path,
					post: post,
					children: [],
					budgetAmount: computeMonthlyAmount(post.amount_patterns),
					childrenTotal: 0,
					displayAmount: 0,
					isEnvelope: false,
					isOverAllocated: false,
					postCount: post.amount_patterns.length > 0 ? 1 : 0
				});
			}
		}

		// Create structural parent nodes for paths without posts
		for (const post of directionPosts) {
			if (!post.category_path) continue;

			for (let i = 1; i < post.category_path.length; i++) {
				const parentPath = post.category_path.slice(0, i);
				const parentKey = parentPath.join('/');

				if (!nodeMap.has(parentKey)) {
					nodeMap.set(parentKey, {
						name: parentPath[parentPath.length - 1],
						path: parentPath,
						post: null,
						children: [],
						budgetAmount: 0,
						childrenTotal: 0,
						displayAmount: 0,
						isEnvelope: false,
						isOverAllocated: false,
						postCount: 0
					});
				}
			}
		}

		// Build parent-child relationships
		for (const node of nodeMap.values()) {
			if (node.path.length > 1) {
				const parentPath = node.path.slice(0, -1);
				const parentKey = parentPath.join('/');
				const parent = nodeMap.get(parentKey);
				if (parent) {
					parent.children.push(node);
				}
			}
		}

		// Compute aggregated amounts (bottom-up)
		function computeAggregates(node: TreeNode): void {
			for (const child of node.children) {
				computeAggregates(child);
			}

			node.childrenTotal = node.children.reduce(
				(sum, child) => sum + child.displayAmount, 0
			);

			node.isEnvelope = node.budgetAmount > 0 && node.children.length > 0;
			node.isOverAllocated = node.isEnvelope && node.childrenTotal > node.budgetAmount;

			// Display amount:
			// - Leaf or envelope: use budgetAmount (the ceiling IS the amount)
			// - Pure category: use childrenTotal (sum of what's under it)
			node.displayAmount = node.budgetAmount > 0 ? node.budgetAmount : node.childrenTotal;

			node.postCount = (node.budgetAmount > 0 ? 1 : 0) +
				node.children.reduce((sum, child) => sum + child.postCount, 0);
		}

		// Get root nodes (depth 1)
		const roots = Array.from(nodeMap.values())
			.filter((n) => n.path.length === 1)
			.sort((a, b) => a.name.localeCompare(b.name, 'da'));

		for (const root of roots) {
			computeAggregates(root);
		}

		return roots;
	}

	// Compute summary totals
	function computeSummary() {
		// Use tree to avoid double-counting envelopes
		const incomeTree = buildTree('income');
		const expenseTree = buildTree('expense');
		const transferTree = buildTree('transfer');

		const sumTree = (nodes: TreeNode[]) => nodes.reduce((sum, n) => sum + n.displayAmount, 0);

		const income = sumTree(incomeTree);
		const expense = sumTree(expenseTree);
		const transfer = sumTree(transferTree);
		const available = income - expense - transfer;

		return { income, expense, transfer, available };
	}

	const summary = $derived(computeSummary());

	// Shared drill-down state
	type DrillState = { type: 'root' } | { type: 'direction'; direction: 'income' | 'expense' | 'transfer' } | { type: 'category'; direction: 'income' | 'expense'; path: string[] };

	let drillState = $state<DrillState>({ type: 'root' });

	// Active tab
	let activeTab = $state<'A' | 'B' | 'C' | 'D'>('A');

	// Tab D expansion state
	let expanded = $state<Record<string, boolean>>({});

	// Derived: current view items
	const currentItems = $derived.by(() => {
		if (drillState.type === 'root') {
			return [
				{ name: 'Indtægter', direction: 'income' as const, amount: summary.income, postCount: posts.filter(p => p.direction === 'income').length },
				{ name: 'Udgifter', direction: 'expense' as const, amount: summary.expense, postCount: posts.filter(p => p.direction === 'expense').length },
				{ name: 'Overførsler', direction: 'transfer' as const, amount: summary.transfer, postCount: posts.filter(p => p.direction === 'transfer').length }
			];
		} else if (drillState.type === 'direction') {
			const tree = buildTree(drillState.direction);
			return tree;
		} else {
			// category drill
			const tree = buildTree(drillState.direction);
			const node = findNodeByPath(tree, drillState.path);
			return node?.children || [];
		}
	});

	// Derived: current node (for dual-nature display)
	const currentNode = $derived.by(() => {
		if (drillState.type === 'category') {
			const tree = buildTree(drillState.direction);
			return findNodeByPath(tree, drillState.path);
		}
		return null;
	});

	function findNodeByPath(tree: TreeNode[], path: string[]): TreeNode | null {
		for (const node of tree) {
			if (arraysEqual(node.path, path)) return node;
			const found = findNodeByPath(node.children, path);
			if (found) return found;
		}
		return null;
	}

	function arraysEqual(a: string[], b: string[]): boolean {
		return a.length === b.length && a.every((v, i) => v === b[i]);
	}

	// Breadcrumb helpers
	const breadcrumb = $derived.by(() => {
		if (drillState.type === 'root') return [];
		if (drillState.type === 'direction') {
			const label = drillState.direction === 'income' ? 'Indtægter' : drillState.direction === 'expense' ? 'Udgifter' : 'Overførsler';
			return [label];
		}
		// category
		const dirLabel = drillState.direction === 'income' ? 'Indtægter' : 'Udgifter';
		return [dirLabel, ...drillState.path];
	});

	function drillToRoot() {
		drillState = { type: 'root' };
		expanded = {};
	}

	function drillToDirection() {
		if (drillState.type === 'category') {
			drillState = { type: 'direction', direction: drillState.direction };
			expanded = {};
		}
	}

	function drillTo(index: number) {
		if (drillState.type === 'category') {
			const newPath = drillState.path.slice(0, index);
			drillState = { type: 'category', direction: drillState.direction, path: newPath };
			expanded = {};
		}
	}

	function drillIntoDirection(direction: 'income' | 'expense' | 'transfer') {
		drillState = { type: 'direction', direction };
		expanded = {};
	}

	function drillIntoNode(node: TreeNode) {
		if (drillState.type === 'direction' && drillState.direction !== 'transfer') {
			drillState = { type: 'category', direction: drillState.direction, path: node.path };
			expanded = {};
		} else if (drillState.type === 'category') {
			drillState = { type: 'category', direction: drillState.direction, path: node.path };
			expanded = {};
		}
	}

	function toggleExpand(nodeKey: string) {
		expanded[nodeKey] = !expanded[nodeKey];
	}

	function getNodeKey(node: any): string {
		if ('direction' in node) return node.direction;
		return node.path.join('/');
	}
</script>

<div class="design-page">
	<!-- Tab control -->
	<div class="tab-control">
		<button class="tab-btn" class:active={activeTab === 'A'} onclick={() => (activeTab = 'A')}>
			Kompakt
		</button>
		<button class="tab-btn" class:active={activeTab === 'B'} onclick={() => (activeTab = 'B')}>
			Kort
		</button>
		<button class="tab-btn" class:active={activeTab === 'C'} onclick={() => (activeTab = 'C')}>
			Detaljer
		</button>
		<button class="tab-btn" class:active={activeTab === 'D'} onclick={() => (activeTab = 'D')}>
			Hybrid
		</button>
	</div>

	<!-- Summary bar -->
	<div class="summary-bar">
		<div class="summary-card income">
			<div class="summary-label">Indtægt</div>
			<div class="summary-amount">{formatAmount(summary.income)} kr</div>
		</div>
		<div class="summary-card expense">
			<div class="summary-label">Udgift</div>
			<div class="summary-amount">{formatAmount(summary.expense)} kr</div>
		</div>
		<div class="summary-card transfer">
			<div class="summary-label">Overførsel</div>
			<div class="summary-amount">{formatAmount(summary.transfer)} kr</div>
		</div>
		<div class="summary-card available" class:negative={summary.available < 0}>
			<div class="summary-label">Til rådighed</div>
			<div class="summary-amount">{formatAmount(summary.available)} kr</div>
		</div>
	</div>

	<!-- Breadcrumb -->
	<div class="breadcrumb">
		<button class="crumb" onclick={drillToRoot}>Rod</button>
		{#each breadcrumb as crumb, i}
			<span class="sep">/</span>
			{#if i === 0 && drillState.type !== 'root'}
				<button class="crumb" onclick={drillToDirection}>{crumb}</button>
			{:else if drillState.type === 'category'}
				<button class="crumb" onclick={() => drillTo(i)}>{crumb}</button>
			{:else}
				<span class="crumb-current">{crumb}</span>
			{/if}
		{/each}
	</div>

	<!-- Envelope ceiling info (when drilled into an envelope node) -->
	{#if currentNode && currentNode.isEnvelope}
		<div class="envelope-info" class:over-allocated={currentNode.isOverAllocated}>
			<strong>{currentNode.name}</strong> — Loft: <strong>{formatAmount(currentNode.budgetAmount)} kr/md</strong>
			· Planlagt: <strong>{formatAmount(currentNode.childrenTotal)} kr/md</strong>
			{#if currentNode.isOverAllocated}
				· <span class="over-warning">Overskridelse: {formatAmount(currentNode.childrenTotal - currentNode.budgetAmount)} kr</span>
			{:else}
				· <span class="remaining">Resterende: {formatAmount(currentNode.budgetAmount - currentNode.childrenTotal)} kr</span>
			{/if}
		</div>
	{/if}

	<!-- Content area -->
	<div class="content-area">
		{#if activeTab === 'A'}
			<!-- Proposal A: Kompakt -->
			<div class="proposal-a">
				{#each currentItems as item}
					{@const isDirection = 'direction' in item}
					{@const isLeaf = !isDirection && (item as TreeNode).children.length === 0}
					{@const node = isDirection ? null : (item as TreeNode)}

					{#if isDirection}
						<!-- Root level direction row -->
						<button class="item-row drillable" onclick={() => drillIntoDirection(item.direction)}>
							<span class="item-name">{item.name}</span>
							<span class="item-spacer"></span>
							<span class="item-meta">{item.postCount} poster</span>
							<span class="item-amount">{formatAmount(item.amount)} kr/md</span>
							<svg class="chevron" width="16" height="16" viewBox="0 0 16 16" fill="none">
								<path d="M6 4L10 8L6 12" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
							</svg>
						</button>
					{:else if isLeaf && node}
						<!-- Leaf post row -->
						<div class="item-row leaf">
							<span class="item-name">{node.name}</span>
							<span class="item-spacer"></span>
							<span class="item-containers">
								{#if node.post && node.post.container_ids.length > 0}
									{node.post.container_ids.map(getContainerName).join(', ')}
								{/if}
							</span>
							<span class="item-recurrence">
								{#if node.post && node.post.amount_patterns.length > 0}
									{node.post.amount_patterns[0].recurrence_label}
								{/if}
							</span>
							<span class="item-amount">{formatAmount(node.displayAmount)} kr</span>
							{#if node.post?.accumulate}
								<span class="accumulate-badge">Akkumulerer</span>
							{/if}
						</div>
					{:else if node}
						<!-- Parent category row -->
						<button class="item-row drillable" onclick={() => drillIntoNode(node)}>
							<span class="item-name">{node.name}</span>
							{#if node.isEnvelope}
								<span class="envelope-indicator" class:over={node.isOverAllocated}>
									{formatAmount(node.childrenTotal)}/{formatAmount(node.budgetAmount)} kr
								</span>
							{/if}
							<span class="item-spacer"></span>
							<span class="item-meta">{node.postCount} poster</span>
							<span class="item-amount">{formatAmount(node.displayAmount)} kr/md</span>
							<svg class="chevron" width="16" height="16" viewBox="0 0 16 16" fill="none">
								<path d="M6 4L10 8L6 12" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
							</svg>
						</button>
					{/if}
				{/each}
			</div>
		{:else if activeTab === 'B'}
			<!-- Proposal B: Kort -->
			<div class="proposal-b">
				{#each currentItems as item}
					{@const isDirection = 'direction' in item}
					{@const isLeaf = !isDirection && (item as TreeNode).children.length === 0}
					{@const node = isDirection ? null : (item as TreeNode)}

					{#if isDirection}
						<!-- Root level direction card -->
						<button class="item-card drillable" onclick={() => drillIntoDirection(item.direction)}>
							<div class="card-header">
								<span class="card-name">{item.name}</span>
								<svg class="chevron" width="20" height="20" viewBox="0 0 16 16" fill="none">
									<path d="M6 4L10 8L6 12" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
								</svg>
							</div>
							<div class="card-meta">{item.postCount} poster</div>
							<div class="card-amount">{formatAmount(item.amount)} kr/md</div>
						</button>
					{:else if isLeaf && node}
						<!-- Leaf post card -->
						<div class="item-card leaf">
							<div class="card-header">
								<span class="card-name">{node.name}</span>
								<span class="card-amount-inline">{formatAmount(node.displayAmount)} kr/md</span>
							</div>
							<div class="card-meta">
								{#if node.post && node.post.container_ids.length > 0}
									{node.post.container_ids.map(getContainerName).join(', ')}
								{/if}
								·
								{#if node.post && node.post.amount_patterns.length > 0}
									{node.post.amount_patterns[0].recurrence_label}
								{/if}
							</div>
							{#if node.post?.accumulate}
								<div class="accumulate-badge">Akkumulerer</div>
							{/if}
						</div>
					{:else if node}
						<!-- Parent category card -->
						<button class="item-card drillable parent" onclick={() => drillIntoNode(node)}>
							<div class="card-header">
								<span class="card-name">{node.name}</span>
								<svg class="chevron" width="20" height="20" viewBox="0 0 16 16" fill="none">
									<path d="M6 4L10 8L6 12" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
								</svg>
							</div>
							<div class="card-meta">
								{node.postCount} poster
								{#if node.post && node.post.container_ids.length > 0}
									· {node.post.container_ids.map(getContainerName).join(', ')}
								{/if}
							</div>
							{#if node.isEnvelope}
								<div class="envelope-display">
									<div class="envelope-bar-container">
										<div class="envelope-bar-fill" class:over={node.isOverAllocated}
											 style="width: {Math.min(100, (node.childrenTotal / node.budgetAmount) * 100)}%">
										</div>
									</div>
									<div class="envelope-meta">
										Planlagt: {formatAmount(node.childrenTotal)} kr / Loft: {formatAmount(node.budgetAmount)} kr
									</div>
								</div>
							{:else}
								<div class="card-amount">{formatAmount(node.displayAmount)} kr/md</div>
							{/if}
						</button>
					{/if}
				{/each}
			</div>
		{:else if activeTab === 'C'}
			<!-- Proposal C: Detaljer -->
			<div class="proposal-c">
				{#each currentItems as item}
					{@const isDirection = 'direction' in item}
					{@const isLeaf = !isDirection && (item as TreeNode).children.length === 0}
					{@const node = isDirection ? null : (item as TreeNode)}

					{#if isDirection}
						<!-- Root level direction detail card -->
						<button class="detail-card drillable" onclick={() => drillIntoDirection(item.direction)}>
							<div class="detail-header">
								<span class="detail-name">{item.name}</span>
								<svg class="chevron" width="24" height="24" viewBox="0 0 16 16" fill="none">
									<path d="M6 4L10 8L6 12" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
								</svg>
							</div>
							<div class="detail-amount-main">Månedligt budget: {formatAmount(item.amount)} kr</div>
							<div class="detail-meta">{item.postCount} poster</div>
						</button>
					{:else if isLeaf && node}
						<!-- Leaf post detail card -->
						<div class="detail-card leaf">
							<div class="detail-header">
								<span class="detail-name">{node.name}</span>
							</div>
							<div class="detail-amount-main">{formatAmount(node.displayAmount)} kr/md</div>
							<div class="detail-meta">
								{#if node.post && node.post.container_ids.length > 0}
									{node.post.container_ids.map(getContainerName).join(', ')}
								{/if}
								·
								{#if node.post && node.post.amount_patterns.length > 0}
									{node.post.amount_patterns[0].recurrence_label}
								{/if}
							</div>
							{#if node.post?.accumulate}
								<div class="accumulate-label">Akkumulerer</div>
							{/if}
						</div>
					{:else if node}
						<!-- Parent category detail card -->
						<button class="detail-card drillable parent" onclick={() => drillIntoNode(node)}>
							<div class="detail-header">
								<span class="detail-name">{node.name}</span>
								<svg class="chevron" width="24" height="24" viewBox="0 0 16 16" fill="none">
									<path d="M6 4L10 8L6 12" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
								</svg>
							</div>
							<div class="detail-amount-main">Månedligt budget: {formatAmount(node.displayAmount)} kr</div>
							{#if node.isEnvelope}
								<div class="detail-envelope">
									Loft: {formatAmount(node.budgetAmount)} kr · Planlagt: {formatAmount(node.childrenTotal)} kr
									{#if node.isOverAllocated}
										· <span class="over-text">+{formatAmount(node.childrenTotal - node.budgetAmount)} kr over loft</span>
									{/if}
								</div>
							{/if}
							<!-- Mini stacked bar -->
							{#if node.children.length > 0 && node.isEnvelope}
								<div class="mini-bar">
									{#each node.children.slice(0, 3) as child}
										{@const pct = (child.displayAmount / node.budgetAmount) * 100}
										<div class="bar-segment" style="width: {pct}%" title={`${child.name}: ${formatAmount(child.displayAmount)} kr`}></div>
									{/each}
									{#if node.children.length > 3}
										<div class="bar-more">+{node.children.length - 3}</div>
									{/if}
								</div>
							{/if}
							<div class="detail-meta">
								{#if node.post && node.post.container_ids.length > 0}
									Beholdere: {node.post.container_ids.map(getContainerName).join(', ')} ·
								{/if}
								{node.postCount} poster
							</div>
						</button>
					{/if}
				{/each}
			</div>
		{:else if activeTab === 'D'}
			<!-- Proposal D: Hybrid -->
			<div class="proposal-d">
				{#each currentItems as item}
					{@const isDirection = 'direction' in item}
					{@const isLeaf = !isDirection && (item as TreeNode).children.length === 0}
					{@const node = isDirection ? null : (item as TreeNode)}
					{@const nodeKey = getNodeKey(item)}
					{@const isExpanded = expanded[nodeKey] || false}

					{#if isDirection}
						<!-- Root level direction row -->
						<div class="hybrid-item">
							<div class="hybrid-row parent">
								{#if item.postCount > 0}
									<button class="expand-btn" onclick={() => toggleExpand(nodeKey)}>
										<svg width="16" height="16" viewBox="0 0 16 16" fill="none">
											{#if isExpanded}
												<path d="M4 6L8 10L12 6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
											{:else}
												<path d="M6 4L10 8L6 12" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
											{/if}
										</svg>
									</button>
								{:else}
									<span class="expand-placeholder"></span>
								{/if}
								<button class="row-content drillable" onclick={() => drillIntoDirection(item.direction)}>
									<span class="row-name">{item.name}</span>
									<span class="row-spacer"></span>
									<span class="row-amount">{formatAmount(item.amount)} kr/md</span>
									<svg class="chevron-drill" width="16" height="16" viewBox="0 0 16 16" fill="none">
										<path d="M6 4L10 8L6 12" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
									</svg>
								</button>
							</div>
							{#if isExpanded}
								<div class="hybrid-children">
									{#each buildTree(item.direction) as childNode}
										<div class="child-preview">
											<span class="child-name">{childNode.name}</span>
											<span class="child-amount">{formatAmount(childNode.displayAmount)} kr</span>
										</div>
									{/each}
								</div>
							{/if}
						</div>
					{:else if isLeaf && node}
						<!-- Leaf post row -->
						<div class="hybrid-item">
							<div class="hybrid-row leaf">
								<span class="expand-placeholder"></span>
								<div class="row-content">
									<span class="row-name">{node.name}</span>
									<span class="row-spacer"></span>
									<span class="row-meta">
										{#if node.post && node.post.container_ids.length > 0}
											{node.post.container_ids.map(getContainerName).join(', ')}
										{/if}
										·
										{#if node.post && node.post.amount_patterns.length > 0}
											{node.post.amount_patterns[0].recurrence_label}
										{/if}
									</span>
									<span class="row-amount">{formatAmount(node.displayAmount)} kr</span>
									{#if node.post?.accumulate}
										<span class="accumulate-badge-inline">Akk.</span>
									{/if}
								</div>
							</div>
						</div>
					{:else if node}
						<!-- Parent category row -->
						<div class="hybrid-item">
							<div class="hybrid-row parent">
								<button class="expand-btn" onclick={() => toggleExpand(nodeKey)}>
									<svg width="16" height="16" viewBox="0 0 16 16" fill="none">
										{#if isExpanded}
											<path d="M4 6L8 10L12 6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
										{:else}
											<path d="M6 4L10 8L6 12" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
										{/if}
									</svg>
								</button>
								<button class="row-content drillable" onclick={() => drillIntoNode(node)}>
									<span class="row-name">{node.name}</span>
									{#if node.isEnvelope}
										<span class="envelope-indicator" class:over={node.isOverAllocated}>
											{formatAmount(node.childrenTotal)}/{formatAmount(node.budgetAmount)} kr
										</span>
									{/if}
									<span class="row-spacer"></span>
									<span class="row-amount">{formatAmount(node.displayAmount)} kr/md</span>
									<svg class="chevron-drill" width="16" height="16" viewBox="0 0 16 16" fill="none">
										<path d="M6 4L10 8L6 12" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
									</svg>
								</button>
							</div>
							{#if isExpanded}
								<div class="hybrid-children">
									{#each node.children as childNode}
										<div class="child-preview">
											<span class="child-name">{childNode.name}</span>
											<span class="child-amount">{formatAmount(childNode.displayAmount)} kr</span>
										</div>
									{/each}
								</div>
							{/if}
						</div>
					{/if}
				{/each}
			</div>
		{/if}
	</div>
</div>

<style>
	.design-page {
		padding: var(--spacing-lg);
		max-width: 1200px;
		margin: 0 auto;
	}

	/* Tab control */
	.tab-control {
		display: flex;
		gap: var(--spacing-sm);
		margin-bottom: var(--spacing-lg);
		border-bottom: 2px solid var(--border);
	}

	.tab-btn {
		padding: var(--spacing-sm) var(--spacing-md);
		background: transparent;
		border: none;
		border-bottom: 2px solid transparent;
		margin-bottom: -2px;
		font-size: var(--font-size-base);
		color: var(--text-secondary);
		cursor: pointer;
		transition: all 0.2s;
	}

	.tab-btn:hover {
		color: var(--text-primary);
	}

	.tab-btn.active {
		color: var(--accent);
		border-bottom-color: var(--accent);
		font-weight: 600;
	}

	/* Summary bar */
	.summary-bar {
		display: grid;
		grid-template-columns: repeat(4, 1fr);
		gap: var(--spacing-md);
		margin-bottom: var(--spacing-lg);
	}

	.summary-card {
		background: var(--bg-card);
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		padding: var(--spacing-md);
	}

	.summary-card.income {
		border-left: 4px solid var(--positive);
	}

	.summary-card.expense {
		border-left: 4px solid var(--negative);
	}

	.summary-card.transfer {
		border-left: 4px solid var(--accent);
	}

	.summary-card.available {
		border-left: 4px solid var(--positive);
	}

	.summary-card.available.negative {
		border-left-color: var(--negative);
	}

	.summary-label {
		font-size: var(--font-size-sm);
		color: var(--text-secondary);
		margin-bottom: var(--spacing-xs);
	}

	.summary-amount {
		font-size: var(--font-size-2xl);
		font-weight: 700;
		color: var(--text-primary);
	}

	/* Breadcrumb */
	.breadcrumb {
		display: flex;
		align-items: center;
		gap: var(--spacing-sm);
		margin-bottom: var(--spacing-md);
		font-size: var(--font-size-sm);
		color: var(--text-secondary);
	}

	.crumb {
		background: transparent;
		border: none;
		color: var(--accent);
		cursor: pointer;
		padding: 0;
		font-size: var(--font-size-sm);
		text-decoration: underline;
	}

	.crumb:hover {
		color: var(--text-primary);
	}

	.crumb-current {
		color: var(--text-primary);
		font-weight: 600;
	}

	.sep {
		color: var(--text-secondary);
	}

	/* Envelope ceiling info */
	.envelope-info {
		background: var(--bg-card);
		border: 1px solid var(--border);
		border-left: 4px solid var(--positive);
		border-radius: var(--radius-md);
		padding: var(--spacing-md);
		margin-bottom: var(--spacing-md);
		font-size: var(--font-size-sm);
		color: var(--text-secondary);
	}

	.envelope-info.over-allocated {
		background: rgba(var(--negative-rgb, 239, 68, 68), 0.05);
		border-left-color: var(--negative);
	}

	.envelope-info .over-warning {
		color: var(--negative);
		font-weight: 600;
	}

	.envelope-info .remaining {
		color: var(--positive);
		font-weight: 600;
	}

	/* Content area */
	.content-area {
		background: var(--bg-card);
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		padding: var(--spacing-md);
		min-height: 400px;
	}

	/* Proposal A: Kompakt */
	.proposal-a {
		display: flex;
		flex-direction: column;
		gap: var(--spacing-xs);
	}

	.proposal-a .item-row {
		display: flex;
		align-items: center;
		gap: var(--spacing-sm);
		padding: var(--spacing-sm) var(--spacing-md);
		border: none;
		background: transparent;
		cursor: default;
		transition: background 0.2s;
		font-size: var(--font-size-base);
		width: 100%;
		text-align: left;
	}

	.proposal-a .item-row.drillable {
		cursor: pointer;
	}

	.proposal-a .item-row.drillable:hover {
		background: var(--bg-page);
	}

	.proposal-a .item-row.leaf {
		color: var(--text-secondary);
		font-size: var(--font-size-sm);
	}


	.proposal-a .item-name {
		font-weight: 600;
		color: var(--text-primary);
	}

	.proposal-a .item-spacer {
		flex: 1;
		min-width: var(--spacing-md);
	}

	.proposal-a .item-meta {
		color: var(--text-secondary);
		font-size: var(--font-size-sm);
	}

	.proposal-a .item-containers {
		color: var(--text-secondary);
		font-size: var(--font-size-sm);
	}

	.proposal-a .item-recurrence {
		color: var(--text-secondary);
		font-size: var(--font-size-sm);
	}

	.proposal-a .item-amount {
		font-weight: 700;
		color: var(--text-primary);
		white-space: nowrap;
	}

	.proposal-a .chevron {
		color: var(--text-secondary);
		flex-shrink: 0;
	}

	.proposal-a .accumulate-badge {
		background: var(--warning);
		color: white;
		font-size: var(--font-size-xs);
		padding: 2px 6px;
		border-radius: var(--radius-sm);
		white-space: nowrap;
	}

	.proposal-a .envelope-indicator {
		font-size: var(--font-size-xs);
		color: var(--positive);
		padding: 2px 6px;
		border-radius: var(--radius-sm);
		background: rgba(var(--positive-rgb, 34, 197, 94), 0.1);
		white-space: nowrap;
	}

	.proposal-a .envelope-indicator.over {
		color: var(--negative);
		background: rgba(var(--negative-rgb, 239, 68, 68), 0.1);
	}

	/* Proposal B: Kort */
	.proposal-b {
		display: flex;
		flex-direction: column;
		gap: var(--spacing-md);
	}

	.proposal-b .item-card {
		background: var(--bg-page);
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		padding: var(--spacing-md);
		cursor: default;
		transition: all 0.2s;
		width: 100%;
		text-align: left;
	}

	.proposal-b .item-card.drillable {
		cursor: pointer;
	}

	.proposal-b .item-card.drillable:hover {
		border-color: var(--accent);
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
	}

	.proposal-b .item-card.parent {
		background: linear-gradient(135deg, var(--bg-card) 0%, var(--bg-page) 100%);
	}

	.proposal-b .item-card.leaf {
		background: var(--bg-card);
	}

	.proposal-b .card-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: var(--spacing-sm);
	}

	.proposal-b .card-name {
		font-size: var(--font-size-lg);
		font-weight: 600;
		color: var(--text-primary);
	}

	.proposal-b .card-meta {
		font-size: var(--font-size-sm);
		color: var(--text-secondary);
		margin-bottom: var(--spacing-sm);
	}

	.proposal-b .card-amount {
		font-size: var(--font-size-xl);
		font-weight: 700;
		color: var(--text-primary);
		margin-top: var(--spacing-sm);
	}

	.proposal-b .card-amount-inline {
		font-size: var(--font-size-lg);
		font-weight: 700;
		color: var(--text-primary);
	}

	.proposal-b .envelope-display {
		margin-top: var(--spacing-md);
		padding-top: var(--spacing-md);
		border-top: 1px solid var(--border);
	}

	.proposal-b .envelope-bar-container {
		height: 8px;
		background: var(--border);
		border-radius: var(--radius-sm);
		overflow: hidden;
		margin-bottom: var(--spacing-sm);
	}

	.proposal-b .envelope-bar-fill {
		height: 100%;
		background: var(--positive);
		transition: width 0.3s;
	}

	.proposal-b .envelope-bar-fill.over {
		background: var(--negative);
	}

	.proposal-b .envelope-meta {
		font-size: var(--font-size-sm);
		color: var(--text-secondary);
	}

	.proposal-b .accumulate-badge {
		display: inline-block;
		background: var(--warning);
		color: white;
		font-size: var(--font-size-xs);
		padding: 4px 8px;
		border-radius: var(--radius-sm);
		margin-top: var(--spacing-sm);
	}

	/* Proposal C: Detaljer */
	.proposal-c {
		display: flex;
		flex-direction: column;
		gap: var(--spacing-lg);
	}

	.proposal-c .detail-card {
		background: var(--bg-page);
		border: 1px solid var(--border);
		border-radius: var(--radius-lg);
		padding: var(--spacing-lg);
		cursor: default;
		transition: all 0.2s;
		width: 100%;
		text-align: left;
	}

	.proposal-c .detail-card.drillable {
		cursor: pointer;
	}

	.proposal-c .detail-card.drillable:hover {
		border-color: var(--accent);
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
	}

	.proposal-c .detail-card.parent {
		background: linear-gradient(to bottom, var(--bg-card) 0%, var(--bg-page) 100%);
	}

	.proposal-c .detail-card.leaf {
		background: var(--bg-card);
	}

	.proposal-c .detail-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: var(--spacing-md);
	}

	.proposal-c .detail-name {
		font-size: var(--font-size-xl);
		font-weight: 700;
		color: var(--text-primary);
	}

	.proposal-c .detail-amount-main {
		font-size: var(--font-size-2xl);
		font-weight: 700;
		color: var(--text-primary);
		margin-bottom: var(--spacing-sm);
	}

	.proposal-c .detail-envelope {
		font-size: var(--font-size-sm);
		color: var(--text-secondary);
		margin-bottom: var(--spacing-md);
	}

	.proposal-c .over-text {
		color: var(--negative);
		font-weight: 600;
	}

	.proposal-c .mini-bar {
		display: flex;
		gap: 2px;
		height: 24px;
		background: var(--border);
		border-radius: var(--radius-sm);
		overflow: hidden;
		margin: var(--spacing-md) 0;
		position: relative;
	}

	.proposal-c .bar-segment {
		background: var(--accent);
		transition: all 0.3s;
	}

	.proposal-c .bar-segment:nth-child(1) {
		background: var(--accent);
	}

	.proposal-c .bar-segment:nth-child(2) {
		background: var(--positive);
	}

	.proposal-c .bar-segment:nth-child(3) {
		background: var(--warning);
	}

	.proposal-c .bar-more {
		position: absolute;
		right: var(--spacing-xs);
		top: 50%;
		transform: translateY(-50%);
		font-size: var(--font-size-xs);
		color: var(--text-secondary);
		background: var(--bg-card);
		padding: 2px 6px;
		border-radius: var(--radius-sm);
	}

	.proposal-c .detail-meta {
		font-size: var(--font-size-sm);
		color: var(--text-secondary);
	}

	.proposal-c .accumulate-label {
		display: inline-block;
		background: var(--warning);
		color: white;
		font-size: var(--font-size-xs);
		padding: 4px 8px;
		border-radius: var(--radius-sm);
		margin-top: var(--spacing-md);
	}

	/* Proposal D: Hybrid */
	.proposal-d {
		display: flex;
		flex-direction: column;
		gap: var(--spacing-xs);
	}

	.proposal-d .hybrid-item {
		border-bottom: 1px solid var(--border);
	}

	.proposal-d .hybrid-item:last-child {
		border-bottom: none;
	}

	.proposal-d .hybrid-row {
		display: flex;
		align-items: center;
		gap: var(--spacing-sm);
		padding: var(--spacing-sm) 0;
	}

	.proposal-d .expand-btn {
		background: transparent;
		border: none;
		padding: var(--spacing-xs);
		cursor: pointer;
		color: var(--text-secondary);
		flex-shrink: 0;
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.proposal-d .expand-btn:hover {
		color: var(--text-primary);
	}

	.proposal-d .expand-placeholder {
		width: 24px;
		flex-shrink: 0;
	}

	.proposal-d .row-content {
		flex: 1;
		display: flex;
		align-items: center;
		gap: var(--spacing-sm);
		background: transparent;
		border: none;
		padding: var(--spacing-xs);
		cursor: default;
		transition: background 0.2s;
		font-size: var(--font-size-base);
		text-align: left;
	}

	.proposal-d .row-content.drillable {
		cursor: pointer;
	}

	.proposal-d .row-content.drillable:hover {
		background: var(--bg-page);
		border-radius: var(--radius-sm);
	}

	.proposal-d .row-name {
		font-weight: 600;
		color: var(--text-primary);
	}

	.proposal-d .row-spacer {
		flex: 1;
		min-width: var(--spacing-md);
	}

	.proposal-d .row-meta {
		font-size: var(--font-size-sm);
		color: var(--text-secondary);
	}

	.proposal-d .row-amount {
		font-weight: 700;
		color: var(--text-primary);
		white-space: nowrap;
	}

	.proposal-d .chevron-drill {
		color: var(--text-secondary);
		flex-shrink: 0;
	}

	.proposal-d .accumulate-badge-inline {
		background: var(--warning);
		color: white;
		font-size: var(--font-size-xs);
		padding: 2px 6px;
		border-radius: var(--radius-sm);
		white-space: nowrap;
	}

	.proposal-d .hybrid-children {
		padding-left: 40px;
		padding-bottom: var(--spacing-sm);
	}

	.proposal-d .child-preview {
		display: flex;
		justify-content: space-between;
		padding: var(--spacing-xs) var(--spacing-sm);
		font-size: var(--font-size-sm);
		color: var(--text-secondary);
	}

	.proposal-d .child-preview:hover {
		background: var(--bg-page);
		border-radius: var(--radius-sm);
	}

	.proposal-d .child-name {
		color: var(--text-secondary);
	}

	.proposal-d .child-amount {
		font-weight: 600;
		color: var(--text-primary);
	}

	.proposal-d .hybrid-row.leaf {
		color: var(--text-secondary);
	}

	.proposal-d .envelope-indicator {
		font-size: var(--font-size-xs);
		color: var(--positive);
		padding: 2px 6px;
		border-radius: var(--radius-sm);
		background: rgba(var(--positive-rgb, 34, 197, 94), 0.1);
		white-space: nowrap;
	}

	.proposal-d .envelope-indicator.over {
		color: var(--negative);
		background: rgba(var(--negative-rgb, 239, 68, 68), 0.1);
	}

	/* Responsive */
	@media (max-width: 768px) {
		.summary-bar {
			grid-template-columns: 1fr 1fr;
		}

		.breadcrumb {
			flex-wrap: wrap;
		}

		.proposal-a .item-row {
			flex-wrap: wrap;
		}

		.proposal-a .item-spacer {
			display: none;
		}
	}
</style>
