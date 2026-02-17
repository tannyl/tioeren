<script lang="ts">
	import { scaleTime, scaleLinear } from 'd3-scale';
	import { timeFormatLocale } from 'd3-time-format';
	import { max } from 'd3-array';
	import { previewOccurrences } from '$lib/api/budgetPosts';
	import { fetchNonBankDays } from '$lib/api/bankDays';
	import type { AmountPattern, PreviewOccurrence } from '$lib/api/budgetPosts';
	import { _ } from '$lib/i18n';

	interface Props {
		budgetId: string;
		patterns: AmountPattern[];
	}
	let { budgetId, patterns }: Props = $props();

	// Danish locale for month names
	const daLocale = timeFormatLocale({
		dateTime: '%A %e. %B %Y %X',
		date: '%d.%m.%Y',
		time: '%H:%M:%S',
		periods: ['AM', 'PM'],
		days: ['søndag', 'mandag', 'tirsdag', 'onsdag', 'torsdag', 'fredag', 'lørdag'],
		shortDays: ['søn', 'man', 'tir', 'ons', 'tor', 'fre', 'lør'],
		months: [
			'januar',
			'februar',
			'marts',
			'april',
			'maj',
			'juni',
			'juli',
			'august',
			'september',
			'oktober',
			'november',
			'december'
		],
		shortMonths: [
			'jan',
			'feb',
			'mar',
			'apr',
			'maj',
			'jun',
			'jul',
			'aug',
			'sep',
			'okt',
			'nov',
			'dec'
		]
	});
	const formatMonth = daLocale.utcFormat('%B %Y');

	// Categorical color palette for patterns
	const patternColors = [
		'var(--accent)',   // blue
		'var(--positive)', // green
		'var(--warning)',  // amber
		'#8B5CF6',         // purple
		'#06B6D4',         // cyan
		'#EC4899',         // pink
		'#F97316',         // orange
		'#14B8A6',         // teal
	];

	// Data from API
	let nonBankDays = $state<Date[]>([]);
	let dateBars = $state<Array<{id: string, pattern: number, date: Date, amount: number}>>([]);
	let periodBars = $state<Array<{id: string, pattern: number, monthStart: Date, amount: number}>>([]);
	let loading = $state(false);

	// Unique clipPath ID per component instance
	const clipId = `chart-clip-${crypto.randomUUID().slice(0, 8)}`;

	// Map each pattern index to a color
	const patternColorMap = $derived.by(() => {
		const map = new Map<number, string>();
		for (let i = 0; i < patterns.length; i++) {
			map.set(i, patternColors[i % patternColors.length]);
		}
		return map;
	});

	// --- Window state ---

	let windowStart = $state(new Date(new Date().getFullYear(), new Date().getMonth(), 1));
	const windowEnd = $derived(new Date(windowStart.getFullYear(), windowStart.getMonth() + 3, 1));

	function navigatePrev() {
		windowStart = new Date(windowStart.getFullYear(), windowStart.getMonth() - 1, 1);
	}

	function navigateNext() {
		windowStart = new Date(windowStart.getFullYear(), windowStart.getMonth() + 1, 1);
	}

	// Range label
	const rangeLabel = $derived.by(() => {
		const endMonth = new Date(windowStart.getFullYear(), windowStart.getMonth() + 2, 1);
		return `${formatMonth(windowStart)} \u2013 ${formatMonth(endMonth)}`;
	});

	// --- Extended window for slide animation (1 extra month each side) ---

	const extendedStart = $derived(new Date(windowStart.getFullYear(), windowStart.getMonth() - 1, 1));
	const extendedEnd = $derived(new Date(windowStart.getFullYear(), windowStart.getMonth() + 4, 1));

	// --- Fetch data from API ---

	let fetchGeneration = 0;

	$effect(() => {
		// Read ALL reactive dependencies synchronously for Svelte tracking
		const currentPatterns = patterns;
		const currentBudgetId = budgetId;
		const currentExtendedStart = extendedStart;
		const currentExtendedEnd = extendedEnd;

		// Deep-read pattern properties so changes to individual patterns trigger re-fetch
		const apiPatterns = currentPatterns.map(p => ({
			amount: p.amount,
			start_date: p.start_date,
			end_date: p.end_date,
			recurrence_pattern: p.recurrence_pattern,
			account_ids: p.account_ids
		}));

		let timeoutId: number | null = null;

		// Skip if no patterns
		if (currentPatterns.length === 0) {
			dateBars = [];
			periodBars = [];
			nonBankDays = [];
			loading = false;
			return;
		}

		// Increment generation to invalidate previous requests
		fetchGeneration++;
		const thisGeneration = fetchGeneration;

		// Debounce: wait 150ms before fetching
		timeoutId = window.setTimeout(async () => {
			loading = true;

			try {
				// Format dates as YYYY-MM-DD using captured values
				const startStr = `${currentExtendedStart.getFullYear()}-${String(currentExtendedStart.getMonth() + 1).padStart(2, '0')}-01`;
				const endDate = new Date(currentExtendedEnd.getFullYear(), currentExtendedEnd.getMonth(), 0); // Last day of previous month
				const endStr = `${endDate.getFullYear()}-${String(endDate.getMonth() + 1).padStart(2, '0')}-${String(endDate.getDate()).padStart(2, '0')}`;

				// Fetch both in parallel
				const [occurrences, nonBankDaysData] = await Promise.all([
					previewOccurrences(currentBudgetId, apiPatterns, startStr, endStr),
					fetchNonBankDays(startStr, endStr)
				]);

				// Check if this response is stale (newer request started)
				if (thisGeneration !== fetchGeneration) {
					return;
				}

				// Map API response to chart data
				const newDateBars: typeof dateBars = [];
				const newPeriodBars: typeof periodBars = [];

				for (const occ of occurrences) {
					const isPeriod = currentPatterns[occ.pattern_index]?.recurrence_pattern?.type?.startsWith('period_');
					const occDate = new Date(occ.date + 'T00:00:00'); // Avoid timezone issues
					const amountKr = occ.amount / 100; // Convert øre to kr

					if (isPeriod) {
						// Period-based: monthStart = occurrence date (API returns 1st of month)
						newPeriodBars.push({
							id: `period-${occ.pattern_index}-${occ.date}`,
							pattern: occ.pattern_index,
							monthStart: occDate,
							amount: amountKr
						});
					} else {
						// Date-based
						newDateBars.push({
							id: `${occ.pattern_index}-${occ.date}`,
							pattern: occ.pattern_index,
							date: occDate,
							amount: amountKr
						});
					}
				}

				// Convert non-bank-days strings to Date objects
				const newNonBankDays = nonBankDaysData.map(d => new Date(d + 'T00:00:00'));

				// Update state
				dateBars = newDateBars;
				periodBars = newPeriodBars;
				nonBankDays = newNonBankDays;
			} catch (err) {
				console.error('Failed to fetch occurrence data:', err);
				// Keep previous data on error (graceful degradation)
			} finally {
				loading = false;
			}
		}, 150);

		// Cleanup
		return () => {
			if (timeoutId !== null) {
				clearTimeout(timeoutId);
			}
		};
	});

	// Filter data to extended window
	const visibleNonBankDays = $derived(
		nonBankDays.filter((d) => d >= extendedStart && d < extendedEnd)
	);

	const visibleBars = $derived(
		dateBars.filter((b) => b.date >= extendedStart && b.date < extendedEnd)
	);

	const visiblePeriodBars = $derived(
		periodBars.filter((b) => {
			const monthEnd = new Date(b.monthStart.getFullYear(), b.monthStart.getMonth() + 1, 1);
			return monthEnd > extendedStart && b.monthStart < extendedEnd;
		})
	);

	// --- Chart dimensions ---

	const margin = { top: 10, right: 16, bottom: 32, left: 50 };
	let containerWidth = $state(600);
	const height = 200;
	const innerWidth = $derived(containerWidth - margin.left - margin.right);
	const innerHeight = height - margin.top - margin.bottom;

	// --- Scales ---

	const xScale = $derived(
		scaleTime().domain([windowStart, windowEnd]).range([0, innerWidth])
	);

	// Stack period bars per month
	const stackedPeriodBars = $derived.by(() => {
		const groups = new Map<number, typeof visiblePeriodBars>();
		for (const bar of visiblePeriodBars) {
			const key = bar.monthStart.getTime();
			if (!groups.has(key)) groups.set(key, []);
			groups.get(key)!.push(bar);
		}

		const result: Array<{
			id: string;
			pattern: number;
			monthStart: Date;
			monthEnd: Date;
			amount: number;
			y0: number;
			y1: number;
		}> = [];

		for (const [, bars] of groups) {
			let cumulative = 0;
			for (const bar of bars) {
				const monthEnd = new Date(bar.monthStart.getFullYear(), bar.monthStart.getMonth() + 1, 1);
				result.push({
					id: bar.id,
					pattern: bar.pattern,
					monthStart: bar.monthStart,
					monthEnd,
					amount: bar.amount,
					y0: cumulative,
					y1: cumulative + bar.amount
				});
				cumulative += bar.amount;
			}
		}

		return result;
	});

	// yMax considers both date bars (per-date stacked totals) and period bars (per-month stacked totals)
	const yMaxDateBars = $derived.by(() => {
		const dateTotals = new Map<number, number>();
		for (const bar of visibleBars) {
			const key = bar.date.getTime();
			dateTotals.set(key, (dateTotals.get(key) ?? 0) + bar.amount);
		}
		return max(dateTotals.values()) ?? 0;
	});
	const yMaxPeriodBars = $derived.by(() => {
		const monthTotals = new Map<number, number>();
		for (const bar of visiblePeriodBars) {
			const key = bar.monthStart.getTime();
			monthTotals.set(key, (monthTotals.get(key) ?? 0) + bar.amount);
		}
		return max(monthTotals.values()) ?? 0;
	});
	const yMax = $derived(Math.max(yMaxDateBars, yMaxPeriodBars, 1000));
	const yScale = $derived(
		scaleLinear()
			.domain([0, yMax * 1.1])
			.range([innerHeight, 0])
	);

	// Month boundaries (visible window - for labels)
	const months = $derived.by(() => {
		const result: Date[] = [];
		let d = new Date(windowStart);
		while (d < windowEnd) {
			result.push(new Date(d));
			d = new Date(d.getFullYear(), d.getMonth() + 1, 1);
		}
		return result;
	});

	// Month boundaries (extended range - for sliding dashed lines inside clip-path)
	// Extra month beyond extendedEnd so the line exists in the DOM before sliding into view
	const monthsEnd = $derived(new Date(windowStart.getFullYear(), windowStart.getMonth() + 5, 1));
	const extendedMonths = $derived.by(() => {
		const result: Date[] = [];
		let d = new Date(extendedStart);
		while (d < monthsEnd) {
			result.push(new Date(d));
			d = new Date(d.getFullYear(), d.getMonth() + 1, 1);
		}
		return result;
	});

	// Day metrics (using DST-safe calendar day calculation)
	function calendarDaysBetween(from: Date, to: Date): number {
		const utcFrom = Date.UTC(from.getFullYear(), from.getMonth(), from.getDate());
		const utcTo = Date.UTC(to.getFullYear(), to.getMonth(), to.getDate());
		return Math.round((utcTo - utcFrom) / (1000 * 60 * 60 * 24));
	}
	const totalDays = $derived(calendarDaysBetween(windowStart, windowEnd));
	const dayWidth = $derived(innerWidth / totalDays);
	const barWidth = $derived(Math.max(4, dayWidth - 2));

	// Stack bars on the same date
	const stackedBars = $derived.by(() => {
		const groups = new Map<number, typeof visibleBars>();
		for (const bar of visibleBars) {
			const key = bar.date.getTime();
			if (!groups.has(key)) groups.set(key, []);
			groups.get(key)!.push(bar);
		}

		const result: Array<{
			id: string;
			pattern: number;
			date: Date;
			amount: number;
			y0: number;
			y1: number;
		}> = [];

		for (const [, bars] of groups) {
			let cumulative = 0;
			for (const bar of bars) {
				result.push({
					id: bar.id,
					pattern: bar.pattern,
					date: bar.date,
					amount: bar.amount,
					y0: cumulative,
					y1: cumulative + bar.amount
				});
				cumulative += bar.amount;
			}
		}

		return result;
	});

	const yTicks = $derived(yScale.ticks(4));

	// Resize observer
	let container = $state<HTMLDivElement>();
	let ready = $state(false);

	$effect(() => {
		if (!container) return;
		const observer = new ResizeObserver((entries) => {
			for (const entry of entries) {
				containerWidth = entry.contentRect.width;
			}
			if (!ready) {
				// Enable transitions only after first layout so elements don't animate from default width
				requestAnimationFrame(() => { ready = true; });
			}
		});
		observer.observe(container);
		return () => observer.disconnect();
	});
</script>

<div class="occurrence-timeline" bind:this={container}>
	<div class="timeline-header">
		<button type="button" class="nav-btn" onclick={navigatePrev} aria-label={$_('budgetPosts.timeline.previousPeriod')}>
			<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24"
				fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
				<path d="m15 18-6-6 6-6" />
			</svg>
		</button>
		<div class="range-label">{rangeLabel}</div>
		<button type="button" class="nav-btn" onclick={navigateNext} aria-label={$_('budgetPosts.timeline.nextPeriod')}>
			<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24"
				fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
				<path d="m9 18 6-6-6-6" />
			</svg>
		</button>
	</div>

	<svg width={containerWidth} {height} style:opacity={loading ? 0.5 : 1} style:transition="opacity 200ms">
		<defs>
			<clipPath id={clipId}>
				<rect x={0} y={0} width={innerWidth} height={innerHeight} />
			</clipPath>
		</defs>

		<g transform="translate({margin.left},{margin.top})">
			<!-- Y-axis grid lines and labels (outside clip, always visible) -->
			{#each yTicks as tick}
				<line
					x1={0}
					x2={innerWidth}
					y1={yScale(tick)}
					y2={yScale(tick)}
					stroke="var(--border)"
					stroke-opacity="0.2"
				/>
				<text
					x={-8}
					y={yScale(tick)}
					dy="0.35em"
					text-anchor="end"
					fill="var(--text-secondary)"
					font-size="11"
				>
					{tick.toLocaleString('da-DK')}
				</text>
			{/each}

			<!-- X-axis base line -->
			<line x1={0} x2={innerWidth} y1={innerHeight} y2={innerHeight} stroke="var(--border)" />

			<!-- Month labels (outside clip, always visible) -->
			{#each months as month, i}
				{@const nextMonth = i < months.length - 1 ? months[i + 1] : windowEnd}
				{@const cx = (xScale(month) + xScale(nextMonth)) / 2}
				<text
					x={cx}
					y={innerHeight + 22}
					text-anchor="middle"
					fill="var(--text-secondary)"
					font-size="12"
					font-weight="500"
				>
					{formatMonth(month)}
				</text>
			{/each}

			<!-- Clipped content: bars, non-bank-days, month lines slide in/out -->
			<g clip-path="url(#{clipId})">
				<!-- Non-bank-day background shading -->
				{#each visibleNonBankDays as day (day.getTime())}
					<rect
						x={xScale(day)}
						y={0}
						width={dayWidth}
						height={innerHeight}
						fill="var(--text-secondary)"
						opacity="0.06"
						class:sliding={ready}
					/>
				{/each}

				<!-- Month boundaries (vertical dashed lines) -->
				{#each extendedMonths as month (month.getTime())}
					<line
						transform="translate({xScale(month)}, 0)"
						x1={0}
						x2={0}
						y1={0}
						y2={innerHeight}
						stroke="var(--text-secondary)"
						stroke-dasharray="4,3"
						stroke-opacity="0.4"
						class:sliding-line={ready}
					/>
				{/each}

				<!-- Period bars (wide, spanning full month) -->
				{#each stackedPeriodBars as bar (bar.id)}
					<rect
						x={xScale(bar.monthStart) + 2}
						y={yScale(bar.y1)}
						width={Math.max(0, xScale(bar.monthEnd) - xScale(bar.monthStart) - 4)}
						height={yScale(bar.y0) - yScale(bar.y1)}
						fill={patternColorMap.get(bar.pattern) ?? 'var(--accent)'}
						opacity="0.35"
						rx="3"
						class="period-bar"
						class:period-bar-animated={ready}
					/>
				{/each}

				<!-- Date bars (narrow, on specific date) -->
				{#each stackedBars as bar (bar.id)}
					<rect
						x={xScale(bar.date) + (dayWidth - barWidth) / 2}
						y={yScale(bar.y1)}
						width={barWidth}
						height={yScale(bar.y0) - yScale(bar.y1)}
						fill={patternColorMap.get(bar.pattern) ?? 'var(--accent)'}
						rx="1"
						class:bar={ready}
					/>
				{/each}
			</g>
		</g>
	</svg>
</div>

<style>
	.occurrence-timeline {
		margin-top: var(--spacing-md);
	}

	.timeline-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: var(--spacing-md);
	}

	.nav-btn {
		padding: var(--spacing-xs);
		background: transparent;
		border: 1px solid var(--border);
		border-radius: var(--radius-sm);
		cursor: pointer;
		display: flex;
		align-items: center;
		justify-content: center;
		color: var(--text-primary);
		transition: all 0.2s;
	}

	.nav-btn:hover {
		background: var(--bg-card);
		border-color: var(--accent);
	}

	.range-label {
		font-size: var(--font-size-sm);
		font-weight: 600;
		color: var(--text-primary);
	}

	.bar {
		transition: x 400ms ease-out, y 400ms ease-out, width 400ms ease-out, height 400ms ease-out;
	}

	.period-bar-animated {
		transition: x 400ms ease-out, y 400ms ease-out, width 400ms ease-out, height 400ms ease-out;
	}

	.sliding {
		transition: x 400ms ease-out;
	}

	.sliding-line {
		transition: transform 400ms ease-out;
	}
</style>
