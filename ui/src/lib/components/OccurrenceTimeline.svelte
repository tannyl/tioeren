<script lang="ts">
  import { scaleTime, scaleSymlog } from "d3-scale";
  import { max, min } from "d3-array";
  import { tweened } from "svelte/motion";
  import { previewOccurrences } from "$lib/api/budgetPosts";
  import { fetchNonBankDays } from "$lib/api/bankDays";
  import type { AmountPattern } from "$lib/api/budgetPosts";
  import { _, locale } from "$lib/i18n";
  import { resolveLocale } from "$lib/utils/dateFormat";

  interface Props {
    budgetId: string;
    patterns: AmountPattern[];
    onColorsReady?: (colorMap: Map<string, string>) => void;
  }
  let { budgetId, patterns, onColorsReady }: Props = $props();

  // Helper function to format a Date object as "month year" (e.g., "februar 2025")
  function formatMonthYearFromDate(
    date: Date,
    loc: string | null | undefined,
  ): string {
    return date.toLocaleDateString(resolveLocale(loc), {
      month: "long",
      year: "numeric",
    });
  }

  // Dynamic color generation using golden angle for maximum separation
  function generatePatternColor(index: number): string {
    const hue = (index * 137.5) % 360; // Golden angle for maximum separation
    return `hsl(${hue}, 65%, 55%)`;
  }

  // Calculate width for a month in pixels
  function getMonthWidth(monthStart: Date, xScale: any): number {
    const monthEnd = new Date(
      monthStart.getFullYear(),
      monthStart.getMonth() + 1,
      1,
    );
    return xScale(monthEnd) - xScale(monthStart);
  }

  // Svelte action: sticky fill attribute (only updates when value is non-null)
  // This allows bars to keep their color during deletion animations even after
  // the color is removed from patternColorMap
  function stickyFill(node: SVGElement, color: string | undefined) {
    if (color != null) {
      node.setAttribute("fill", color);
    }

    return {
      update(newColor: string | undefined) {
        if (newColor != null) {
          node.setAttribute("fill", newColor);
        }
        // If undefined: keep existing fill value (don't touch DOM)
      },
    };
  }

  // Data from API
  let nonBankDays = $state<Date[]>([]);
  let dateBars = $state<
    Array<{ id: string; patternId: string; date: Date; amount: number }>
  >([]);
  let periodBars = $state<
    Array<{ id: string; patternId: string; monthStart: Date; amount: number }>
  >([]);
  // Unique clipPath ID per component instance
  const clipId = `chart-clip-${crypto.randomUUID().slice(0, 8)}`;

  // --- Stable pattern color assignment ---

  // Map pattern client ID → color index
  let patternColorIndices = $state<Map<string, number>>(new Map());
  let nextColorIndex = 0; // Plain variable, not reactive (only used as ID generator)

  // Assign color indices to patterns (effect for mutation)
  $effect(() => {
    // Reset when all patterns cleared (modal reopened)
    if (patterns.length === 0) {
      patternColorIndices.clear();
      nextColorIndex = 0;
      return;
    }

    // Assign color index to new patterns
    for (const pattern of patterns) {
      const clientId = (pattern as any)._clientId;
      if (!clientId) continue;

      // Assign new color index if pattern hasn't been seen before
      if (!patternColorIndices.has(clientId)) {
        patternColorIndices.set(clientId, nextColorIndex);
        nextColorIndex++;
      }
    }
    // Note: No cleanup needed - stickyFill action preserves colors in DOM
    // even when patterns are removed from patternColorMap
  });

  // Map each pattern ID to a color (pure derived, no mutation)
  // Note: Only includes ACTIVE patterns. Deleted patterns are handled by
  // the stickyFill action, which preserves the fill attribute in the DOM.
  const patternColorMap = $derived.by(() => {
    const map = new Map<string, string>();

    for (const pattern of patterns) {
      const clientId = (pattern as any)._clientId;
      if (!clientId) continue;

      const colorIndex = patternColorIndices.get(clientId);
      if (colorIndex !== undefined) {
        map.set(clientId, generatePatternColor(colorIndex));
      }
    }

    return map;
  });

  // Notify parent when colors are ready
  $effect(() => {
    onColorsReady?.(patternColorMap);
  });

  // --- Window state ---

  let windowStart = $state(
    new Date(new Date().getFullYear(), new Date().getMonth(), 1),
  );
  const windowEnd = $derived(
    new Date(windowStart.getFullYear(), windowStart.getMonth() + 3, 1),
  );

  function navigatePrev() {
    windowStart = new Date(
      windowStart.getFullYear(),
      windowStart.getMonth() - 1,
      1,
    );
  }

  function navigateNext() {
    windowStart = new Date(
      windowStart.getFullYear(),
      windowStart.getMonth() + 1,
      1,
    );
  }

  // Range label
  const rangeLabel = $derived.by(() => {
    const endMonth = new Date(
      windowStart.getFullYear(),
      windowStart.getMonth() + 2,
      1,
    );
    return `${formatMonthYearFromDate(windowStart, $locale)} \u2013 ${formatMonthYearFromDate(endMonth, $locale)}`;
  });

  // --- Extended window for slide animation (1 extra month each side) ---

  const extendedStart = $derived(
    new Date(windowStart.getFullYear(), windowStart.getMonth() - 1, 1),
  );
  const extendedEnd = $derived(
    new Date(windowStart.getFullYear(), windowStart.getMonth() + 4, 1),
  );

  // --- Fetch data from API ---

  // Build API patterns object (pure derived, no side effects)
  const apiPatterns = $derived.by(() => {
    const result: Record<string, any> = {};
    for (const p of patterns) {
      const clientId = (p as any)._clientId;
      if (!clientId) continue;
      result[clientId] = {
        amount: p.amount,
        start_date: p.start_date,
        end_date: p.end_date,
        recurrence_pattern: p.recurrence_pattern,
        account_ids: p.account_ids,
      };
    }
    return result;
  });

  let fetchGeneration = 0;

  $effect(() => {
    // Read ALL reactive dependencies synchronously for Svelte tracking
    const currentPatterns = patterns;
    const currentBudgetId = budgetId;
    const currentExtendedStart = extendedStart;
    const currentExtendedEnd = extendedEnd;
    const currentApiPatterns = apiPatterns;

    let timeoutId: number | null = null;

    // Skip if no patterns
    if (currentPatterns.length === 0) {
      dateBars = [];
      periodBars = [];
      nonBankDays = [];
      return;
    }

    // Increment generation to invalidate previous requests
    fetchGeneration++;
    const thisGeneration = fetchGeneration;

    // Debounce: wait 150ms before fetching
    timeoutId = window.setTimeout(async () => {
      try {
        // Format dates as YYYY-MM-DD using captured values
        const startStr = `${currentExtendedStart.getFullYear()}-${String(currentExtendedStart.getMonth() + 1).padStart(2, "0")}-01`;
        const endDate = new Date(
          currentExtendedEnd.getFullYear(),
          currentExtendedEnd.getMonth(),
          0,
        ); // Last day of previous month
        const endStr = `${endDate.getFullYear()}-${String(endDate.getMonth() + 1).padStart(2, "0")}-${String(endDate.getDate()).padStart(2, "0")}`;

        // Fetch both in parallel
        const [occurrences, nonBankDaysData] = await Promise.all([
          previewOccurrences(
            currentBudgetId,
            currentApiPatterns,
            startStr,
            endStr,
          ),
          fetchNonBankDays(startStr, endStr),
        ]);

        // Check if this response is stale (newer request started)
        if (thisGeneration !== fetchGeneration) {
          return;
        }

        // Map API response to chart data
        const newDateBars: typeof dateBars = [];
        const newPeriodBars: typeof periodBars = [];

        // Build pattern lookup by client ID
        const patternById = new Map<string, AmountPattern>();
        for (const p of currentPatterns) {
          const clientId = (p as any)._clientId;
          if (clientId) patternById.set(clientId, p);
        }

        for (let i = 0; i < occurrences.length; i++) {
          const occ = occurrences[i];
          const pattern = patternById.get(occ.pattern_id);
          const isPeriod =
            pattern?.recurrence_pattern?.type?.startsWith("period_");
          const occDate = new Date(occ.date + "T00:00:00"); // Avoid timezone issues
          const amountKr = occ.amount / 100; // Convert øre to kr

          if (isPeriod) {
            // Period-based: monthStart = occurrence date (API returns 1st of month)
            newPeriodBars.push({
              id: `period-${occ.pattern_id}-${occ.date}-${i}`,
              patternId: occ.pattern_id,
              monthStart: occDate,
              amount: amountKr,
            });
          } else {
            // Date-based
            newDateBars.push({
              id: `${occ.pattern_id}-${occ.date}-${i}`,
              patternId: occ.pattern_id,
              date: occDate,
              amount: amountKr,
            });
          }
        }

        // Convert non-bank-days strings to Date objects
        const newNonBankDays = nonBankDaysData.map(
          (d) => new Date(d + "T00:00:00"),
        );

        // Update state
        dateBars = newDateBars;
        periodBars = newPeriodBars;
        nonBankDays = newNonBankDays;
      } catch (err) {
        console.error("Failed to fetch occurrence data:", err);
        // Keep previous data on error (graceful degradation)
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
    nonBankDays.filter((d) => d >= extendedStart && d < extendedEnd),
  );

  const visibleBars = $derived(
    dateBars.filter((b) => b.date >= extendedStart && b.date < extendedEnd),
  );

  const visiblePeriodBars = $derived(
    periodBars.filter((b) => {
      const monthEnd = new Date(
        b.monthStart.getFullYear(),
        b.monthStart.getMonth() + 1,
        1,
      );
      return monthEnd > extendedStart && b.monthStart < extendedEnd;
    }),
  );

  // Bars in visible 3-month window only (for yMax calculation)
  const windowBars = $derived(
    dateBars.filter((b) => b.date >= windowStart && b.date < windowEnd),
  );
  const windowPeriodBars = $derived(
    periodBars.filter((b) => {
      const monthEnd = new Date(
        b.monthStart.getFullYear(),
        b.monthStart.getMonth() + 1,
        1,
      );
      return monthEnd > windowStart && b.monthStart < windowEnd;
    }),
  );

  // --- Chart dimensions ---

  const margin = { top: 10, right: 16, bottom: 32, left: 50 };
  let containerWidth = $state(600);
  const height = 200;
  const innerWidth = $derived(containerWidth - margin.left - margin.right);
  const innerHeight = height - margin.top - margin.bottom;

  // --- Scales ---

  const xScale = $derived(
    scaleTime().domain([windowStart, windowEnd]).range([0, innerWidth]),
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
      patternId: string;
      monthStart: Date;
      monthEnd: Date;
      amount: number;
      y0: number;
      y1: number;
    }> = [];

    for (const [, bars] of groups) {
      bars.sort((a, b) => a.amount - b.amount);
      let cumulative = 0;
      for (const bar of bars) {
        const monthEnd = new Date(
          bar.monthStart.getFullYear(),
          bar.monthStart.getMonth() + 1,
          1,
        );
        result.push({
          id: bar.id,
          patternId: bar.patternId,
          monthStart: bar.monthStart,
          monthEnd,
          amount: bar.amount,
          y0: cumulative,
          y1: cumulative + bar.amount,
        });
        cumulative += bar.amount;
      }
    }

    return result;
  });

  // yMax considers both date bars (per-date stacked totals) and period bars (per-month stacked totals)
  // Uses only bars in visible 3-month window (not extended window)
  const yMaxDateBars = $derived.by(() => {
    const dateTotals = new Map<number, number>();
    for (const bar of windowBars) {
      const key = bar.date.getTime();
      dateTotals.set(key, (dateTotals.get(key) ?? 0) + bar.amount);
    }
    return max(dateTotals.values()) ?? 0;
  });
  const yMaxPeriodBars = $derived.by(() => {
    const monthTotals = new Map<number, number>();
    for (const bar of windowPeriodBars) {
      const key = bar.monthStart.getTime();
      monthTotals.set(key, (monthTotals.get(key) ?? 0) + bar.amount);
    }
    return max(monthTotals.values()) ?? 0;
  });

  // Track last known yMax to prevent reset to 10 during loading
  let lastKnownYMax = $state(10);

  // Compute current max from visible bars (pure derived, no mutation)
  const currentYMax = $derived.by(() => {
    const hasData = windowBars.length > 0 || windowPeriodBars.length > 0;
    if (hasData) {
      return Math.max(yMaxDateBars, yMaxPeriodBars, 10);
    }
    return null; // No data
  });

  // Y-axis target: use current max if available, otherwise last known max
  const yMaxTarget = $derived(currentYMax ?? lastKnownYMax);

  // Tweened yMax for smooth animation in both directions
  const yMaxTweened = tweened(10, { duration: 400 });

  // Update last known max and tweened value when target changes
  $effect(() => {
    if (currentYMax !== null) {
      lastKnownYMax = currentYMax; // Track last valid max
    }
    yMaxTweened.set(yMaxTarget);
  });

  // Minimum non-zero bar value (for log compression detection)
  const yMinNonZero = $derived.by(() => {
    const allAmounts: number[] = [];
    for (const bar of windowBars) {
      if (bar.amount > 0) allAmounts.push(bar.amount);
    }
    for (const bar of windowPeriodBars) {
      if (bar.amount > 0) allAmounts.push(bar.amount);
    }
    return min(allAmounts) ?? 0;
  });

  // Always use symlog, but tween the constant for smooth linear↔log transitions.
  // High constant (~1e6) = effectively linear, low constant (5000) = log compression.
  // Tween in log-space so visual change is distributed evenly across the duration.
  const LOG_CONSTANT_LINEAR = Math.log(1e6);
  const LOG_CONSTANT_LOG = Math.log(5000);
  const logConstantTarget = $derived(
    yMinNonZero > 0 && yMaxTarget / yMinNonZero > 20
      ? LOG_CONSTANT_LOG
      : LOG_CONSTANT_LINEAR,
  );
  const logConstant = tweened(LOG_CONSTANT_LINEAR, { duration: 400 });
  $effect(() => {
    logConstant.set(logConstantTarget);
  });

  const yScale = $derived(
    scaleSymlog()
      .constant(Math.exp($logConstant))
      .domain([0, $yMaxTweened * 1.1])
      .range([innerHeight, 0]),
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
  const monthsEnd = $derived(
    new Date(windowStart.getFullYear(), windowStart.getMonth() + 5, 1),
  );
  const extendedMonths = $derived.by(() => {
    const result: Date[] = [];
    let d = new Date(extendedStart);
    while (d < monthsEnd) {
      result.push(new Date(d));
      d = new Date(d.getFullYear(), d.getMonth() + 1, 1);
    }
    return result;
  });

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
      patternId: string;
      date: Date;
      amount: number;
      y0: number;
      y1: number;
    }> = [];

    for (const [, bars] of groups) {
      bars.sort((a, b) => a.amount - b.amount);
      let cumulative = 0;
      for (const bar of bars) {
        result.push({
          id: bar.id,
          patternId: bar.patternId,
          date: bar.date,
          amount: bar.amount,
          y0: cumulative,
          y1: cumulative + bar.amount,
        });
        cumulative += bar.amount;
      }
    }

    return result;
  });

  const yTicks = $derived(yScale.ticks(4));

  // --- Month grouping for synchronized animations (BUG-028, BUG-030) ---
  // Group all chart elements by month for synchronized animation

  const monthGroups = $derived.by(() => {
    const groups = new Map<
      number,
      {
        monthStart: Date;
        periodBars: typeof stackedPeriodBars;
        dateBars: typeof stackedBars;
        nonBankDays: Date[];
        hasData: boolean;
      }
    >();

    // Populate groups from extended window
    for (
      let m = new Date(extendedStart);
      m < extendedEnd;
      m = new Date(m.getFullYear(), m.getMonth() + 1, 1)
    ) {
      const key = m.getTime();
      groups.set(key, {
        monthStart: new Date(m),
        periodBars: [],
        dateBars: [],
        nonBankDays: [],
        hasData: false,
      });
    }

    // Assign period bars to months
    for (const bar of stackedPeriodBars) {
      const key = bar.monthStart.getTime();
      const group = groups.get(key);
      if (group) {
        group.periodBars.push(bar);
        group.hasData = true;
      }
    }

    // Assign date bars to months
    for (const bar of stackedBars) {
      const monthStart = new Date(
        bar.date.getFullYear(),
        bar.date.getMonth(),
        1,
      );
      const key = monthStart.getTime();
      const group = groups.get(key);
      if (group) {
        group.dateBars.push(bar);
        group.hasData = true;
      }
    }

    // Assign non-bank days to months
    for (const day of visibleNonBankDays) {
      const monthStart = new Date(day.getFullYear(), day.getMonth(), 1);
      const key = monthStart.getTime();
      const group = groups.get(key);
      if (group) {
        group.nonBankDays.push(day);
      }
    }

    return Array.from(groups.values());
  });

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
        requestAnimationFrame(() => {
          ready = true;
        });
      }
    });
    observer.observe(container);
    return () => observer.disconnect();
  });
</script>

<div class="occurrence-timeline" bind:this={container}>
  <div class="timeline-header">
    <button
      type="button"
      class="nav-btn"
      onclick={navigatePrev}
      aria-label={$_("budgetPosts.timeline.previousPeriod")}
    >
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
    <div class="range-label">{rangeLabel}</div>
    <button
      type="button"
      class="nav-btn"
      onclick={navigateNext}
      aria-label={$_("budgetPosts.timeline.nextPeriod")}
    >
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

  <svg width={containerWidth} {height}>
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
          {tick.toLocaleString(resolveLocale($locale))}
        </text>
      {/each}

      <!-- X-axis base line -->
      <line
        x1={0}
        x2={innerWidth}
        y1={innerHeight}
        y2={innerHeight}
        stroke="var(--border)"
      />

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
          {formatMonthYearFromDate(month, $locale)}
        </text>
      {/each}

      <!-- Clipped content: month boundary lines stay flat, month groups for bars and non-bank days -->
      <g
        clip-path="url(#{clipId})"
        class="months-container"
        class:months-ready={ready}
      >
        <!-- Month boundary lines (stay FLAT - do NOT wrap in groups) -->
        {#each extendedMonths as month (month.getTime())}
          <line
            class="sliding-line"
            transform="translate({xScale(month)}, 0)"
            x1={0}
            x2={0}
            y1={0}
            y2={innerHeight}
            stroke="var(--text-secondary)"
            stroke-dasharray="4,3"
            stroke-opacity="0.4"
          />
        {/each}

        <!-- Month content groups (each month as its own SVG viewport) -->
        {#each monthGroups as group (group.monthStart.getTime())}
          {@const monthWidth = getMonthWidth(group.monthStart, xScale)}
          {@const daysInMonth = new Date(
            group.monthStart.getFullYear(),
            group.monthStart.getMonth() + 1,
            0,
          ).getDate()}
          {@const dayWidthPct = 100 / daysInMonth}
          {@const barWidthPct = dayWidthPct * 0.8}

          <svg
            class="month-viewport"
            class:month-has-data={group.hasData}
            width={monthWidth}
            height={innerHeight}
            style="transform: translateX({xScale(group.monthStart)}px)"
          >
            <!-- Non-bank-day background shading -->
            {#each group.nonBankDays as day (day.getTime())}
              <rect
                class="month-bar"
                x="{(day.getDate() - 1) * dayWidthPct}%"
                width="{dayWidthPct}%"
                height={innerHeight}
                fill="var(--text-secondary)"
                opacity="0.06"
              />
            {/each}

            <!-- Period bars -->
            {#each group.periodBars as bar (bar.id)}
              <rect
                class="month-bar"
                y={yScale(bar.y1)}
                width="100%"
                height={yScale(bar.y0) - yScale(bar.y1)}
                use:stickyFill={patternColorMap.get(bar.patternId)}
                opacity="0.35"
              />
            {/each}

            <!-- Date bars -->
            {#each group.dateBars as bar (bar.id)}
              <rect
                class="month-bar"
                x="{(bar.date.getDate() - 1) * dayWidthPct +
                  (dayWidthPct - barWidthPct) / 2}%"
                y={yScale(bar.y1)}
                width="{barWidthPct}%"
                height={yScale(bar.y0) - yScale(bar.y1)}
                use:stickyFill={patternColorMap.get(bar.patternId)}
              />
            {/each}
          </svg>
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

  .months-container {
    opacity: 0;
    transition: opacity 400ms ease-out 1000ms;
  }

  .months-container.months-ready {
    opacity: 1;
  }

  .sliding-line {
    transition: transform 400ms ease-out;
  }

  .month-viewport {
    opacity: 0.3;
    transition:
      transform 400ms ease-out,
      opacity 500ms ease-out;
  }

  .month-viewport.month-has-data {
    opacity: 1;
  }

  .month-bar {
    transition: width 400ms ease-out;
  }
</style>
