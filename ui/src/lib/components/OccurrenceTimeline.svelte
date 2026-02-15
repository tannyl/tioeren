<script lang="ts">
	import { _, locale } from '$lib/i18n';
	import type { AmountPattern, PreviewOccurrence } from '$lib/api/budgetPosts';
	import { previewOccurrences } from '$lib/api/budgetPosts';
	import { formatMonthYear } from '$lib/utils/dateFormat';
	import * as echarts from 'echarts';

	let {
		budgetId,
		patterns = []
	}: {
		budgetId: string;
		patterns: AmountPattern[];
	} = $props();

	let chartContainer = $state<HTMLDivElement>();
	let chartInstance: echarts.ECharts | null = null;
	let windowStart = $state<Date>(new Date(new Date().getFullYear(), new Date().getMonth(), 1));
	let resizeHandler: (() => void) | null = null;
	let debounceTimeout: number | null = null;

	// Effect 1: Initialize chart once when container is available
	$effect(() => {
		if (chartContainer && !chartInstance) {
			chartInstance = echarts.init(chartContainer);
			resizeHandler = () => chartInstance?.resize();
			window.addEventListener('resize', resizeHandler);
		}

		return () => {
			if (chartInstance) {
				chartInstance.dispose();
				chartInstance = null;
			}
			if (resizeHandler) {
				window.removeEventListener('resize', resizeHandler);
				resizeHandler = null;
			}
		};
	});

	// Effect 2: Fetch and render when patterns or window changes
	$effect(() => {
		const currentPatterns = patterns;
		const currentWindow = windowStart;

		if (debounceTimeout) {
			clearTimeout(debounceTimeout);
		}

		if (currentPatterns.length === 0) {
			return;
		}

		chartInstance?.showLoading();

		debounceTimeout = window.setTimeout(() => {
			fetchAndRender(currentPatterns, currentWindow);
		}, 300);

		return () => {
			if (debounceTimeout) {
				clearTimeout(debounceTimeout);
			}
		};
	});

	async function fetchAndRender(currentPatterns: AmountPattern[], currentWindow: Date) {
		try {
			// Calculate window: 3 months starting from windowStart
			const fromDate = new Date(currentWindow);
			const toDate = new Date(currentWindow);
			toDate.setMonth(toDate.getMonth() + 3);

			const fromDateStr = fromDate.toISOString().split('T')[0];
			const toDateStr = toDate.toISOString().split('T')[0];

			// Convert patterns to API format (omit fields)
			const apiPatterns = currentPatterns.map((p) => ({
				amount: p.amount,
				start_date: p.start_date,
				end_date: p.end_date,
				recurrence_pattern: p.recurrence_pattern,
				account_ids: p.account_ids
			}));

			const occs = await previewOccurrences(budgetId, apiPatterns, fromDateStr, toDateStr);

			chartInstance?.hideLoading();

			if (occs.length > 0) {
				buildAndSetOption(occs, currentWindow);
			}
		} catch (err) {
			console.error('Failed to load occurrences:', err);
			chartInstance?.hideLoading();
		}
	}

	function buildAndSetOption(occurrences: PreviewOccurrence[], currentWindow: Date) {
		if (!chartInstance) return;

		// Calculate window range
		const fromDate = new Date(currentWindow);
		const toDate = new Date(currentWindow);
		toDate.setMonth(toDate.getMonth() + 3);

		// Calculate total days in window
		const totalDays = Math.floor((toDate.getTime() - fromDate.getTime()) / (1000 * 60 * 60 * 24));

		// Build category data: one entry per day
		const categories: string[] = [];
		const monthBoundaryIndices: number[] = [];

		for (let d = 0; d < totalDays; d++) {
			const date = new Date(fromDate);
			date.setDate(date.getDate() + d);

			// Track month boundaries (1st of each month)
			if (date.getDate() === 1 && d > 0) {
				monthBoundaryIndices.push(d);
			}

			// Show month name at ~15th of month (center of month)
			if (date.getDate() === 15) {
				categories.push(
					formatMonthYear(
						`${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`,
						$locale
					)
				);
			} else {
				categories.push('');
			}
		}

		// Group occurrences by pattern_index
		const patternGroups = new Map<number, PreviewOccurrence[]>();
		for (const occ of occurrences) {
			if (!patternGroups.has(occ.pattern_index)) {
				patternGroups.set(occ.pattern_index, []);
			}
			patternGroups.get(occ.pattern_index)!.push(occ);
		}

		// Color palette
		const styles = getComputedStyle(document.documentElement);
		const colors = [
			styles.getPropertyValue('--accent').trim(),
			styles.getPropertyValue('--positive').trim(),
			styles.getPropertyValue('--warning').trim(),
			styles.getPropertyValue('--negative').trim(),
			'#8b5cf6',
			'#14b8a6'
		];

		// Determine if we should use log scale
		const amounts = occurrences.map((o) => o.amount / 100);
		const maxAmount = Math.max(...amounts);
		const minAmount = Math.min(...amounts.filter((a) => a > 0));
		const useLogScale = maxAmount / minAmount > 10;

		// Build series
		const series: any[] = [];

		Array.from(patternGroups.entries())
			.sort((a, b) => a[0] - b[0])
			.forEach(([patternIndex, occs], seriesIdx) => {
				const pattern = patterns[patternIndex];
				if (!pattern) return;

				const color = colors[patternIndex % colors.length];
				const isPeriodBased = pattern.recurrence_pattern?.type.startsWith('period_');

				if (isPeriodBased) {
					// Use custom series for period-based patterns
					const data = occs.map((occ) => {
						const occDate = new Date(occ.date + 'T00:00:00');
						const dayOffset = Math.floor(
							(occDate.getTime() - fromDate.getTime()) / (1000 * 60 * 60 * 24)
						);

						// Find month boundaries for this occurrence
						const monthStart = new Date(occDate.getFullYear(), occDate.getMonth(), 1);
						const monthEnd = new Date(occDate.getFullYear(), occDate.getMonth() + 1, 0);

						const monthStartDayOffset = Math.floor(
							(monthStart.getTime() - fromDate.getTime()) / (1000 * 60 * 60 * 24)
						);
						const monthEndDayOffset = Math.floor(
							(monthEnd.getTime() - fromDate.getTime()) / (1000 * 60 * 60 * 24)
						);

						return [dayOffset, occ.amount / 100, monthStartDayOffset, monthEndDayOffset];
					});

					series.push({
						type: 'custom',
						name: `Pattern ${patternIndex + 1}`,
						data: data,
						stack: 'total',
						renderItem: (params: any, api: any) => {
							const monthStart = api.value(2);
							const monthEnd = api.value(3);
							const amount = api.value(1);
							const startCoord = api.coord([monthStart, 0]);
							const endCoord = api.coord([monthEnd, amount]);
							const rectWidth = endCoord[0] - startCoord[0];
							const rectHeight = startCoord[1] - endCoord[1]; // y is inverted

							return {
								type: 'rect',
								shape: {
									x: startCoord[0],
									y: endCoord[1],
									width: rectWidth,
									height: rectHeight
								},
								style: {
									fill: color + '4D' // 30% opacity
								}
							};
						},
						// Add markLine on first series only
						...(seriesIdx === 0
							? {
									markLine: {
										silent: true,
										symbol: 'none',
										lineStyle: {
											color: styles.getPropertyValue('--border').trim(),
											type: 'dashed',
											opacity: 0.3
										},
										data: monthBoundaryIndices.map((idx) => ({ xAxis: idx }))
									}
								}
							: {})
					});
				} else {
					// Use bar series for date-based patterns
					const data = occs.map((occ) => {
						const occDate = new Date(occ.date + 'T00:00:00');
						const dayOffset = Math.floor(
							(occDate.getTime() - fromDate.getTime()) / (1000 * 60 * 60 * 24)
						);
						return [dayOffset, occ.amount / 100];
					});

					series.push({
						type: 'bar',
						name: `Pattern ${patternIndex + 1}`,
						data: data,
						barWidth: 6,
						itemStyle: {
							color: color
						},
						stack: 'total',
						// Add markLine on first series only
						...(seriesIdx === 0
							? {
									markLine: {
										silent: true,
										symbol: 'none',
										lineStyle: {
											color: styles.getPropertyValue('--border').trim(),
											type: 'dashed',
											opacity: 0.3
										},
										data: monthBoundaryIndices.map((idx) => ({ xAxis: idx }))
									}
								}
							: {})
					});
				}
			});

		const borderColor = styles.getPropertyValue('--border').trim();
		const textSecondary = styles.getPropertyValue('--text-secondary').trim();

		const option: echarts.EChartsOption = {
			grid: {
				left: '60px',
				right: '20px',
				top: '20px',
				bottom: '40px',
				containLabel: false
			},
			xAxis: {
				type: 'category',
				data: categories,
				axisLabel: {
					show: true,
					interval: 0, // Evaluate all categories
					color: textSecondary,
					hideOverlap: true
				},
				axisLine: {
					lineStyle: {
						color: borderColor
					}
				},
				axisTick: {
					show: false
				},
				splitLine: {
					show: false
				}
			},
			yAxis: {
				type: useLogScale ? 'log' : 'value',
				axisLine: {
					lineStyle: {
						color: borderColor
					}
				},
				axisLabel: {
					color: textSecondary,
					formatter: (value: number) => value.toLocaleString('da-DK')
				},
				splitLine: {
					lineStyle: {
						color: borderColor,
						opacity: 0.1
					}
				}
			},
			series: series,
			tooltip: {
				trigger: 'axis',
				axisPointer: {
					type: 'shadow'
				},
				formatter: (params: any) => {
					if (!Array.isArray(params) || params.length === 0) return '';

					const dayOffset = params[0].value[0];
					const date = new Date(fromDate);
					date.setDate(date.getDate() + dayOffset);
					const dateStr = date.toLocaleDateString('da-DK', {
						day: 'numeric',
						month: 'short',
						year: 'numeric'
					});

					let html = `<div style="font-weight: 600; margin-bottom: 4px;">${dateStr}</div>`;

					params.forEach((param: any) => {
						const amount = param.value[1];
						const formattedAmount = amount.toLocaleString('da-DK', {
							minimumFractionDigits: 0,
							maximumFractionDigits: 0
						});
						html += `<div>${param.marker} ${formattedAmount} kr</div>`;
					});

					return html;
				}
			}
		};

		// Use notMerge=true to clear previous options and avoid stale data
		chartInstance.setOption(option, true);
	}

	function navigatePrev() {
		const newStart = new Date(windowStart);
		newStart.setMonth(newStart.getMonth() - 1);
		windowStart = newStart;
	}

	function navigateNext() {
		const newStart = new Date(windowStart);
		newStart.setMonth(newStart.getMonth() + 1);
		windowStart = newStart;
	}

	function getRangeLabel(): string {
		const start = new Date(windowStart);
		const end = new Date(windowStart);
		end.setMonth(end.getMonth() + 2); // 3 months total, so end is +2

		const startStr = formatMonthYear(
			`${start.getFullYear()}-${String(start.getMonth() + 1).padStart(2, '0')}`,
			$locale
		);
		const endStr = formatMonthYear(
			`${end.getFullYear()}-${String(end.getMonth() + 1).padStart(2, '0')}`,
			$locale
		);

		return `${startStr} - ${endStr}`;
	}
</script>

<div class="occurrence-timeline">
	{#if patterns.length === 0}
		<div class="empty-state">
			<p>{$_('budgetPosts.timeline.empty')}</p>
		</div>
	{:else}
		<div class="timeline-header">
			<button type="button" class="nav-btn" onclick={navigatePrev} aria-label="Previous period">
				<svg
					xmlns="http://www.w3.org/2000/svg"
					width="20"
					height="20"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="2"
					stroke-linecap="round"
					stroke-linejoin="round"
				>
					<path d="m15 18-6-6 6-6" />
				</svg>
			</button>
			<div class="range-label">{getRangeLabel()}</div>
			<button type="button" class="nav-btn" onclick={navigateNext} aria-label="Next period">
				<svg
					xmlns="http://www.w3.org/2000/svg"
					width="20"
					height="20"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="2"
					stroke-linecap="round"
					stroke-linejoin="round"
				>
					<path d="m9 18 6-6-6-6" />
				</svg>
			</button>
		</div>

		<div class="chart-container" bind:this={chartContainer}></div>
	{/if}
</div>

<style>
	.occurrence-timeline {
		margin-top: var(--spacing-md);
	}

	.empty-state {
		text-align: center;
		padding: var(--spacing-xl);
		color: var(--text-secondary);
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

	.chart-container {
		width: 100%;
		height: 200px;
	}
</style>
