<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { _, locale } from '$lib/i18n';
	import { getForecast } from '$lib/api/forecast';
	import type { ForecastData } from '$lib/api/forecast';
	import * as echarts from 'echarts';
	import { formatDate, formatMonthYear, formatMonthYearShort } from '$lib/utils/dateFormat';

	let budgetId: string = $derived($page.params.id as string);
	let forecast = $state<ForecastData | null>(null);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let selectedMonths = $state(12);

	let chartContainer: HTMLDivElement;
	let chartInstance: echarts.ECharts | null = null;

	onMount(async () => {
		await loadForecast();
	});

	async function loadForecast() {
		try {
			loading = true;
			error = null;
			forecast = await getForecast(budgetId, selectedMonths);
		} catch (err) {
			error = err instanceof Error ? $_(err.message) : $_('common.error');
		} finally {
			loading = false;
		}
	}

	let resizeHandler: (() => void) | null = null;

	$effect(() => {
		if (forecast && chartContainer && !loading) {
			renderChart();
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

	$effect(() => {
		// React to selectedMonths changes
		if (selectedMonths) {
			loadForecast();
		}
	});

	function renderChart() {
		if (!forecast || !chartContainer) return;

		// Dispose existing chart and remove old resize listener
		if (chartInstance) {
			chartInstance.dispose();
		}
		if (resizeHandler) {
			window.removeEventListener('resize', resizeHandler);
		}

		chartInstance = echarts.init(chartContainer);

		const months = forecast.projections.map((p) => formatMonthYearShort(p.month, $locale));
		const balances = forecast.projections.map((p) => p.end_balance / 100);

		// Get colors from CSS custom properties
		const styles = getComputedStyle(document.documentElement);
		const borderColor = styles.getPropertyValue('--border').trim();
		const textSecondary = styles.getPropertyValue('--text-secondary').trim();
		const accentColor = styles.getPropertyValue('--accent').trim();

		const option: echarts.EChartsOption = {
			grid: {
				left: '50px',
				right: '20px',
				top: '20px',
				bottom: '40px',
				containLabel: false
			},
			xAxis: {
				type: 'category',
				data: months,
				axisLine: {
					lineStyle: {
						color: borderColor
					}
				},
				axisLabel: {
					color: textSecondary
				}
			},
			yAxis: {
				type: 'value',
				axisLine: {
					lineStyle: {
						color: borderColor
					}
				},
				axisLabel: {
					color: textSecondary,
					formatter: (value: number) => `${Math.round(value / 1000)}k`
				},
				splitLine: {
					lineStyle: {
						color: borderColor
					}
				}
			},
			series: [
				{
					data: balances,
					type: 'line',
					smooth: true,
					lineStyle: {
						width: 3,
						color: accentColor
					},
					itemStyle: {
						color: accentColor
					},
					areaStyle: {
						color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
							{
								offset: 0,
								color: `${accentColor}4D` // 30% opacity (0.3 * 255 = ~4D in hex)
							},
							{
								offset: 1,
								color: `${accentColor}0D` // 5% opacity (0.05 * 255 = ~0D in hex)
							}
						])
					}
				}
			],
			tooltip: {
				trigger: 'axis',
				formatter: (params: any) => {
					const value = params[0].value;
					return `${params[0].axisValue}<br/>${formatCurrency(value * 100)} kr`;
				}
			}
		};

		chartInstance.setOption(option);

		// Handle window resize - store reference for cleanup
		resizeHandler = () => {
			if (chartInstance) {
				chartInstance.resize();
			}
		};
		window.addEventListener('resize', resizeHandler);
	}

	function formatCurrency(amountInOre: number): string {
		return (amountInOre / 100).toLocaleString('da-DK', {
			minimumFractionDigits: 0,
			maximumFractionDigits: 0
		});
	}


	function selectTimeRange(months: number) {
		selectedMonths = months;
	}

	function shouldShowWarning(projection: any): boolean {
		const startBalance = projection.start_balance;
		const endBalance = projection.end_balance;
		return endBalance < 0 || endBalance < startBalance * 0.7;
	}
</script>

<div class="page">
	{#if loading}
		<div class="loading">
			<p>{$_('common.loading')}</p>
		</div>
	{:else if error}
		<div class="error-message">
			<p>{error}</p>
		</div>
	{:else if forecast}
		<div class="forecast">
			<!-- Header with time range selector -->
			<div class="forecast-header">
				<h1 class="page-title">{$_('forecast.title')}</h1>
				<div class="time-range-selector">
					<button
						class="time-range-btn"
						class:active={selectedMonths === 3}
						onclick={() => selectTimeRange(3)}
					>
						{$_('forecast.timeRange.3months')}
					</button>
					<button
						class="time-range-btn"
						class:active={selectedMonths === 6}
						onclick={() => selectTimeRange(6)}
					>
						{$_('forecast.timeRange.6months')}
					</button>
					<button
						class="time-range-btn"
						class:active={selectedMonths === 12}
						onclick={() => selectTimeRange(12)}
					>
						{$_('forecast.timeRange.12months')}
					</button>
				</div>
			</div>

			<!-- Chart Card -->
			<section class="card chart-card">
				<h2 class="card-title">{$_('forecast.balanceDevelopment')}</h2>
				<div class="chart-container" bind:this={chartContainer}></div>
			</section>

			<!-- Info Cards -->
			<div class="two-column">
				<!-- Lowest Point Card -->
				<section class="card info-card">
					<h2 class="card-title">{$_('forecast.lowestPoint.title')}</h2>
					<div class="info-content">
						<div class="info-value">{formatCurrency(forecast.lowest_point.balance)} kr</div>
						<div class="info-label">{formatMonthYear(forecast.lowest_point.month, $locale)}</div>
					</div>
				</section>

				<!-- Next Large Expense Card -->
				<section class="card info-card">
					<h2 class="card-title">{$_('forecast.nextLargeExpense.title')}</h2>
					{#if forecast.next_large_expense}
						<div class="info-content">
							<div class="info-value negative">
								-{formatCurrency(Math.abs(forecast.next_large_expense.amount))} kr
							</div>
							<div class="info-name">{forecast.next_large_expense.name}</div>
							<div class="info-label">{formatDate(forecast.next_large_expense.date, $locale)}</div>
						</div>
					{:else}
						<div class="info-content">
							<div class="info-placeholder">{$_('forecast.nextLargeExpense.notAvailable')}</div>
						</div>
					{/if}
				</section>
			</div>

			<!-- Monthly Breakdown Table -->
			<section class="card table-card">
				<h2 class="card-title">{$_('forecast.monthlyBreakdown.title')}</h2>
				<div class="table-container">
					<table class="breakdown-table">
						<thead>
							<tr>
								<th>{$_('forecast.monthlyBreakdown.month')}</th>
								<th>{$_('forecast.monthlyBreakdown.start')}</th>
								<th>{$_('forecast.monthlyBreakdown.income')}</th>
								<th>{$_('forecast.monthlyBreakdown.expenses')}</th>
								<th>{$_('forecast.monthlyBreakdown.end')}</th>
							</tr>
						</thead>
						<tbody>
							{#each forecast.projections as projection}
								<tr class:warning={shouldShowWarning(projection)}>
									<td>{formatMonthYear(projection.month, $locale)}</td>
									<td>{formatCurrency(projection.start_balance)}</td>
									<td class="positive">+{formatCurrency(projection.expected_income)}</td>
									<td class="negative">-{formatCurrency(Math.abs(projection.expected_expenses))}</td>
									<td class="end-balance" class:negative={projection.end_balance < 0}>
										{formatCurrency(projection.end_balance)}
										{#if shouldShowWarning(projection)}
											<span class="warning-icon">(!)</span>
										{/if}
									</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
			</section>
		</div>
	{/if}
</div>

<style>
	.page {
		max-width: 1200px;
		margin: 0 auto;
		padding: var(--spacing-xl);
	}

	.loading {
		text-align: center;
		padding: var(--spacing-xl);
		color: var(--text-secondary);
	}

	.error-message {
		padding: var(--spacing-md);
		background: rgba(239, 68, 68, 0.1);
		border: 1px solid var(--negative);
		border-radius: var(--radius-md);
		color: var(--negative);
	}

	.forecast {
		display: flex;
		flex-direction: column;
		gap: var(--spacing-lg);
	}

	.forecast-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: var(--spacing-md);
	}

	.page-title {
		font-size: var(--font-size-3xl);
		font-weight: 700;
		color: var(--text-primary);
	}

	.time-range-selector {
		display: flex;
		gap: var(--spacing-sm);
	}

	.time-range-btn {
		padding: var(--spacing-sm) var(--spacing-md);
		background: var(--bg-card);
		border: 1px solid var(--border);
		border-radius: var(--radius-md);
		font-size: var(--font-size-base);
		font-weight: 500;
		color: var(--text-primary);
		cursor: pointer;
		transition: all 0.2s;
	}

	.time-range-btn:hover {
		border-color: var(--accent);
	}

	.time-range-btn.active {
		background: var(--accent);
		color: white;
		border-color: var(--accent);
	}

	.card {
		background: var(--bg-card);
		border: 1px solid var(--border);
		border-radius: var(--radius-lg);
		padding: var(--spacing-xl);
	}

	.card-title {
		font-size: var(--font-size-lg);
		font-weight: 600;
		color: var(--text-primary);
		margin-bottom: var(--spacing-lg);
	}

	/* Chart Card */
	.chart-card {
		min-height: 400px;
	}

	.chart-container {
		width: 100%;
		height: 350px;
	}

	/* Two Column Layout */
	.two-column {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: var(--spacing-lg);
	}

	/* Info Cards */
	.info-content {
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: var(--spacing-sm);
		padding: var(--spacing-lg) 0;
	}

	.info-value {
		font-size: var(--font-size-3xl);
		font-weight: 700;
		color: var(--accent);
	}

	.info-value.negative {
		color: var(--negative);
	}

	.info-name {
		font-size: var(--font-size-lg);
		font-weight: 600;
		color: var(--text-primary);
	}

	.info-label {
		font-size: var(--font-size-base);
		color: var(--text-secondary);
	}

	.info-placeholder {
		font-size: var(--font-size-base);
		color: var(--text-secondary);
		padding: var(--spacing-lg);
	}

	/* Table Card */
	.table-container {
		overflow-x: auto;
	}

	.breakdown-table {
		width: 100%;
		border-collapse: collapse;
	}

	.breakdown-table th {
		text-align: left;
		padding: var(--spacing-sm) var(--spacing-md);
		font-size: var(--font-size-sm);
		font-weight: 600;
		color: var(--text-secondary);
		border-bottom: 2px solid var(--border);
	}

	.breakdown-table td {
		padding: var(--spacing-md);
		font-size: var(--font-size-base);
		border-bottom: 1px solid var(--border);
	}

	.breakdown-table tbody tr:hover {
		background: var(--bg-page);
	}

	.breakdown-table tbody tr.warning {
		background: rgba(245, 158, 11, 0.05);
	}

	.breakdown-table td.positive {
		color: var(--positive);
		font-weight: 500;
	}

	.breakdown-table td.negative {
		color: var(--negative);
		font-weight: 500;
	}

	.breakdown-table td.end-balance {
		font-weight: 600;
	}

	.warning-icon {
		margin-left: var(--spacing-xs);
		color: var(--warning);
		font-weight: 700;
	}

	/* Responsive Design */
	@media (max-width: 768px) {
		.page {
			padding: var(--spacing-md);
		}

		.forecast-header {
			flex-direction: column;
			align-items: flex-start;
			gap: var(--spacing-md);
		}

		.page-title {
			font-size: var(--font-size-2xl);
		}

		.time-range-selector {
			width: 100%;
		}

		.time-range-btn {
			flex: 1;
		}

		.card {
			padding: var(--spacing-lg);
		}

		.chart-container {
			height: 300px;
		}

		.two-column {
			grid-template-columns: 1fr;
		}

		.info-value {
			font-size: var(--font-size-2xl);
		}

		.breakdown-table {
			font-size: var(--font-size-sm);
		}

		.breakdown-table th,
		.breakdown-table td {
			padding: var(--spacing-sm);
		}
	}
</style>
