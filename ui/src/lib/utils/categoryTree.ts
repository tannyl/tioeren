import type { BudgetPost } from '$lib/api/budgetPosts';

export interface CategoryTreeNode {
	name: string;
	fullPath: string[];
	post: BudgetPost | null;
	children: CategoryTreeNode[];
	depth: number;
}

/**
 * Build a hierarchical tree from budget posts based on category_path.
 * Posts are sorted by display_order.
 */
export function buildCategoryTree(posts: BudgetPost[]): CategoryTreeNode[] {
	const root: CategoryTreeNode[] = [];

	// Filter posts with category_path and sort by display_order
	const categorizedPosts = posts
		.filter((p) => p.category_path && p.category_path.length > 0)
		.sort((a, b) => {
			// Sort by display_order lexicographically
			const aOrder = a.display_order || [];
			const bOrder = b.display_order || [];
			for (let i = 0; i < Math.max(aOrder.length, bOrder.length); i++) {
				const aVal = aOrder[i] ?? -1;
				const bVal = bOrder[i] ?? -1;
				if (aVal !== bVal) return aVal - bVal;
			}
			return 0;
		});

	for (const post of categorizedPosts) {
		const path = post.category_path!;
		let currentLevel = root;

		for (let i = 0; i < path.length; i++) {
			const segment = path[i];
			const isLeaf = i === path.length - 1;
			const existingNode = currentLevel.find((n) => n.name === segment);

			if (existingNode) {
				if (isLeaf) {
					existingNode.post = post;
				}
				currentLevel = existingNode.children;
			} else {
				const newNode: CategoryTreeNode = {
					name: segment,
					fullPath: path.slice(0, i + 1),
					post: isLeaf ? post : null,
					children: [],
					depth: i
				};
				currentLevel.push(newNode);
				currentLevel = newNode.children;
			}
		}
	}

	return root;
}
