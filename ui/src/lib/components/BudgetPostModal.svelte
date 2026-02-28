<script lang="ts">
  import { tick, untrack } from "svelte";
  import { fade } from "svelte/transition";
  import { _, locale } from "$lib/i18n";
  import type {
    BudgetPost,
    BudgetPostDirection,
    RecurrencePattern,
    RecurrenceType,
    RelativePosition,
    AmountPattern,
  } from "$lib/api/budgetPosts";
  import type { Container, ContainerType } from "$lib/api/containers";
  import {
    formatDateShort,
    formatMonth,
    formatMonthYear,
    formatMonthYearShort,
    formatList,
  } from "$lib/utils/dateFormat";
  import OccurrenceTimeline from "./OccurrenceTimeline.svelte";

  let {
    show = $bindable(false),
    budgetId,
    budgetPost = undefined,
    existingPosts = [],
    containers = [],
    onSave,
  }: {
    show?: boolean;
    budgetId: string;
    budgetPost?: BudgetPost | undefined;
    existingPosts: BudgetPost[];
    containers: Container[];
    onSave: (data: any) => Promise<void>;
  } = $props();

  // Form state
  let direction = $state<BudgetPostDirection>("expense");
  let categoryPathChips = $state<string[]>([]);
  let categoryInputValue = $state("");
  let accumulate = $state(false);
  let containerIds = $state<string[]>([]);
  let viaContainerId = $state<string | null>(null);
  let containerMode = $state<'cashbox' | 'piggybank' | 'debt'>('cashbox');
  let specialContainerId = $state<string | null>(null);
  let transferFromContainerId = $state<string | null>(null);
  let transferToContainerId = $state<string | null>(null);
  let saving = $state(false);
  let error = $state<string | null>(null);
  let showCascadeConfirmation = $state(false);

  // Autocomplete state
  let showSuggestions = $state(false);
  let highlightedIndex = $state(-1);

  // Amount patterns state
  let amountPatterns = $state<AmountPattern[]>([]);
  let activeView = $state<"main" | "pattern-editor">("main");
  let editingPatternIndex = $state<number | null>(null);
  let patternColors = $state<Map<number, string>>(new Map());

  // Client-side ID counter for stable pattern identification (plain variable, not reactive)
  let patternIdCounter = 0;

  // Pattern form state
  let patternAmount = $state("");
  let patternStartDate = $state("");
  let patternEndDate = $state("");
  let patternHasEndDate = $state(false);
  let patternContainerIds = $state<string[]>([]);
  let patternBasis = $state<"period" | "date">("date");
  let patternRepeats = $state(false);
  let patternFrequency = $state<"daily" | "weekly" | "monthly" | "yearly">(
    "monthly",
  );
  let patternMonthlyType = $state<"fixed" | "relative" | "bank_day">("fixed");
  let patternPeriodFrequency = $state<"monthly" | "yearly">("monthly");
  let patternPeriodYear = $state<number>(new Date().getFullYear());
  let patternPeriodMonth = $state<number>(new Date().getMonth() + 1);
  let patternEndPeriodYear = $state<number>(new Date().getFullYear());
  let patternEndPeriodMonth = $state<number>(12);
  let patternRecurrenceInterval = $state<number>(1);
  let patternRecurrenceWeekday = $state<number>(0);
  let patternRecurrenceDayOfMonth = $state<number>(1);
  let patternRecurrenceRelativePosition = $state<RelativePosition>("first");
  let patternRecurrenceMonth = $state<number>(1);
  let patternRecurrenceMonths = $state<number[]>([]);
  let patternRecurrenceBankDayAdjustment = $state<"none" | "next" | "previous">(
    "none",
  );
  let patternBankDayKeepInMonth = $state(true);
  let patternBankDayNoDedup = $state(false);
  let patternYearlyType = $state<"fixed" | "relative" | "bank_day">("fixed");
  let patternBankDayNumber = $state<number>(1);
  let patternBankDayFromEnd = $state<string>("start");

  // Derived recurrence type from toggles
  let patternRecurrenceType = $derived.by(() => {
    if (patternBasis === "period") {
      if (!patternRepeats) return "period_once";
      return patternPeriodFrequency === "monthly"
        ? "period_monthly"
        : "period_yearly";
    }
    if (!patternRepeats) return "once";
    if (patternFrequency === "daily") return "daily";
    if (patternFrequency === "weekly") return "weekly";
    if (patternFrequency === "monthly") {
      if (patternMonthlyType === "bank_day") return "monthly_bank_day";
      return patternMonthlyType === "fixed"
        ? "monthly_fixed"
        : "monthly_relative";
    }
    if (patternFrequency === "yearly") {
      if (patternYearlyType === "bank_day") return "yearly_bank_day";
      return "yearly";
    }
    return "yearly";
  }) as RecurrenceType;

  // Determine if editing mode
  let isEditMode = $derived(budgetPost !== undefined);

  // Level-aware autocomplete: suggest only the next segment
  let levelAwareSuggestions = $derived.by(() => {
    if (!showSuggestions) return [];

    const currentLevel = categoryPathChips.length;
    const query = categoryInputValue.toLowerCase().trim();
    const suggestions = new Set<string>();

    // Find all posts with matching direction and category_path that starts with our current chips
    for (const post of existingPosts) {
      if (
        post.direction === direction &&
        post.category_path &&
        post.category_path.length > currentLevel
      ) {
        // Check if the path starts with our current chips
        let matches = true;
        for (let i = 0; i < categoryPathChips.length; i++) {
          if (post.category_path[i] !== categoryPathChips[i]) {
            matches = false;
            break;
          }
        }

        // If it matches, extract the next segment
        if (matches) {
          const nextSegment = post.category_path[currentLevel];
          // Filter by query if there's input
          if (!query || nextSegment.toLowerCase().includes(query)) {
            suggestions.add(nextSegment);
          }
        }
      }
    }

    return Array.from(suggestions).sort();
  });

  // Reset highlightedIndex when suggestions change
  $effect(() => {
    levelAwareSuggestions;
    highlightedIndex = -1;
  });

  // Reset accumulate flag when direction is not expense
  $effect(() => {
    if (direction !== "expense") {
      accumulate = false;
    }
  });

  // Reset form when modal opens or budgetPost changes
  $effect(() => {
    if (show) {
      // Capture budgetPost to ensure it's tracked, then use untrack for the rest
      const currentBudgetPost = budgetPost;

      // Use untrack to prevent tracking derived values that change during normal operation
      // We only want to track `show` and `budgetPost`, not containers/availableContainerTypes
      untrack(() => {
        patternIdCounter = 0;
        if (currentBudgetPost) {
          // Edit mode - populate from existing post
          direction = currentBudgetPost.direction;
          categoryPathChips = currentBudgetPost.category_path
            ? [...currentBudgetPost.category_path]
            : [];
          categoryInputValue = "";
          highlightedIndex = -1;
          accumulate = currentBudgetPost.accumulate;

          // Detect container mode from existing data
          const existingIds = currentBudgetPost.container_ids ?? [];
          const existingContainers = containers.filter(c => existingIds.includes(c.id));
          const hasNonCashbox = existingContainers.some(c => c.type !== 'cashbox');

          if (hasNonCashbox) {
            const nonCashboxContainer = existingContainers.find(c => c.type !== 'cashbox');
            containerMode = (nonCashboxContainer?.type as 'piggybank' | 'debt') || 'piggybank';
            specialContainerId = nonCashboxContainer?.id || null;
            containerIds = [];
          } else {
            containerMode = 'cashbox';
            specialContainerId = null;
            containerIds = currentBudgetPost.container_ids || [];
          }

          viaContainerId = currentBudgetPost.via_container_id || null;
          transferFromContainerId = currentBudgetPost.transfer_from_container_id;
          transferToContainerId = currentBudgetPost.transfer_to_container_id;
          amountPatterns = (currentBudgetPost.amount_patterns || []).map(
            (p) =>
              ({
                ...p,
                _clientId:
                  (p as any)._clientId ?? patternIdCounter++,
                _savedContainerIds: p.container_ids ? [...p.container_ids] : null,
              }) as any,
          );
        } else {
          // Create mode - reset to defaults
          direction = "expense";
          categoryPathChips = [];
          categoryInputValue = "";
          highlightedIndex = -1;
          accumulate = false;
          containerIds = [];
          containerMode = availableContainerTypes[0] || 'cashbox';
          specialContainerId = null;
          viaContainerId = null;
          transferFromContainerId = null;
          transferToContainerId = null;
          amountPatterns = [];
        }
        error = null;
        activeView = "main";
        showSuggestions = false;
        showCascadeConfirmation = false;
      });
    }
  });

  function handleClose() {
    activeView = "main";
    show = false;
  }

  async function handleSubmit(event: Event) {
    event.preventDefault();
    if (activeView !== "main") return;
    error = null;

    // Validate based on direction
    if (direction === "transfer") {
      if (!transferFromContainerId || !transferToContainerId) {
        error = $_("budgetPosts.validation.transferAccountsRequired");
        return;
      }
      if (transferFromContainerId === transferToContainerId) {
        error = $_("budgetPosts.validation.transferSameAccount");
        return;
      }
    } else {
      // income or expense
      if (categoryPathChips.length === 0 && !categoryInputValue.trim()) {
        error = $_("budgetPosts.validation.categoryRequired");
        return;
      }
      if (containerMode === 'cashbox') {
        if (containerIds.length === 0) {
          error = $_("budgetPosts.accounts.validation");
          return;
        }
      } else {
        if (!specialContainerId) {
          error = $_("budgetPosts.accounts.specialRequired");
          return;
        }
      }
      // Validate via container if set
      if (viaContainerId) {
        const viaContainer = containers.find(c => c.id === viaContainerId);
        if (!viaContainer || viaContainer.type !== "cashbox") {
          error = $_("budgetPosts.viaAccount.validation");
          return;
        }
      }
    }

    if (amountPatterns.length === 0) {
      error = $_("budgetPosts.validation.atLeastOnePattern");
      return;
    }

    // Check for cascade confirmation if editing and descendants exist
    if (budgetPost && descendantPosts.length > 0 && direction !== 'transfer') {
      const originalContainerIds = budgetPost.container_ids || [];
      const newContainerIds = effectiveContainerIds;
      // Check if container_ids have changed
      const idsChanged =
        originalContainerIds.length !== newContainerIds.length ||
        !originalContainerIds.every(id => newContainerIds.includes(id));

      if (idsChanged && !showCascadeConfirmation) {
        showCascadeConfirmation = true;
        return;
      }
    }

    await performSave();
  }

  async function performSave() {
    error = null;
    saving = true;
    showCascadeConfirmation = false;

    try {
      const data: any = {
        direction,
        accumulate,
        amount_patterns: amountPatterns.map((p) => ({
          amount: p.amount,
          start_date: p.start_date,
          end_date: p.end_date,
          recurrence_pattern: p.recurrence_pattern,
          container_ids: p.container_ids,
        })),
      };

      if (direction === "transfer") {
        data.category_path = null;
        data.display_order = null;
        data.container_ids = null;
        data.via_container_id = null;
        data.transfer_from_container_id = transferFromContainerId;
        data.transfer_to_container_id = transferToContainerId;
      } else {
        const parsedPath = [...categoryPathChips];
        const trailing = categoryInputValue.trim();
        if (trailing) parsedPath.push(trailing);
        data.category_path = parsedPath.length > 0 ? parsedPath : null;
        data.display_order =
          parsedPath.length > 0 ? parsedPath.map(() => 0) : null;
        data.container_ids = effectiveContainerIds;
        data.via_container_id = containerMode !== 'cashbox' ? viaContainerId : null;
        data.transfer_from_container_id = null;
        data.transfer_to_container_id = null;
      }

      await onSave(data);
      show = false;
    } catch (err) {
      error = err instanceof Error ? $_(err.message) : $_("common.error");
    } finally {
      saving = false;
    }
  }

  function handleBackdropClick(event: MouseEvent) {
    if (event.target === event.currentTarget) {
      handleClose();
    }
  }

  function handleCategoryKeydown(event: KeyboardEvent) {
    const value = categoryInputValue.trim();

    if (event.key === "Enter") {
      event.preventDefault();
      if (
        highlightedIndex >= 0 &&
        highlightedIndex < levelAwareSuggestions.length
      ) {
        selectSuggestion(levelAwareSuggestions[highlightedIndex]);
      } else if (value.length > 0) {
        addChip(value);
      }
    } else if (event.key === "/" && value.length > 0) {
      event.preventDefault();
      addChip(value);
    } else if (
      event.key === "Backspace" &&
      categoryInputValue === "" &&
      categoryPathChips.length > 0
    ) {
      event.preventDefault();
      categoryPathChips = categoryPathChips.slice(0, -1);
    } else if (event.key === "ArrowDown") {
      event.preventDefault();
      if (levelAwareSuggestions.length > 0) {
        highlightedIndex = Math.min(
          highlightedIndex + 1,
          levelAwareSuggestions.length - 1,
        );
      }
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      highlightedIndex = Math.max(highlightedIndex - 1, -1);
    } else if (event.key === "Escape") {
      showSuggestions = false;
      highlightedIndex = -1;
    }
  }

  function addChip(text: string) {
    const trimmed = text.trim();
    if (trimmed.length === 0) return;
    categoryPathChips = [...categoryPathChips, trimmed];
    categoryInputValue = "";
    highlightedIndex = -1;
  }

  function removeChipAt(index: number) {
    categoryPathChips = categoryPathChips.slice(0, index);
    showSuggestions = true;
    tick().then(() => {
      document.getElementById("post-category")?.focus();
    });
  }

  function selectSuggestion(suggestion: string) {
    addChip(suggestion);
    showSuggestions = true;
  }

  function toggleContainerId(containerId: string) {
    if (containerIds.includes(containerId)) {
      containerIds = containerIds.filter((id) => id !== containerId);
    } else {
      containerIds = [...containerIds, containerId];
    }
  }

  function switchContainerMode(mode: 'cashbox' | 'piggybank' | 'debt') {
    containerMode = mode;
    if (mode === 'cashbox') {
      specialContainerId = null;
      viaContainerId = null;
    } else {
      containerIds = [];
      specialContainerId = null;
      viaContainerId = null;
    }
  }

  function togglePatternContainer(containerId: string) {
    if (patternContainerIds.includes(containerId)) {
      patternContainerIds = patternContainerIds.filter((id) => id !== containerId);
    } else {
      patternContainerIds = [...patternContainerIds, containerId];
    }
  }

  function getContainerDisplayName(container: Container): string {
    return `${container.name} (${$_(`container.type.${container.type}`)})`;
  }

  function formatPatternContainerText(containerIds: string[]): string {
    const names = containerIds
      .map(id => containers.find(c => c.id === id)?.name)
      .filter(Boolean) as string[];
    if (names.length === 0) return "";

    if (containerMode === "cashbox") {
      // Cashbox mode: can have multiple, use "eller" disjunction
      const list = new Intl.ListFormat($locale ?? "da", { style: "long", type: "disjunction" }).format(names);
      if (direction === "income") {
        return $_("budgetPosts.patternContainerTo", { values: { containers: list } });
      }
      return $_("budgetPosts.patternContainerFrom", { values: { containers: list } });
    }

    // Piggybank/debt mode: always exactly 1 container, optionally with via
    const name = names[0];
    const viaName = viaContainerId ? containers.find(c => c.id === viaContainerId)?.name : null;
    if (viaName) {
      if (direction === "income") {
        return $_("budgetPosts.patternContainerToVia", { values: { container: name, via: viaName } });
      }
      return $_("budgetPosts.patternContainerFromVia", { values: { container: name, via: viaName } });
    }
    if (direction === "income") {
      return $_("budgetPosts.patternContainerTo", { values: { containers: name } });
    }
    return $_("budgetPosts.patternContainerFrom", { values: { containers: name } });
  }

  function arraysEqual(a: string[] | null | undefined, b: string[]): boolean {
    if (!a) return false;
    if (a.length !== b.length) return false;
    return a.every((v, i) => v === b[i]);
  }

  function isPatternAutoAdjusted(pattern: AmountPattern): boolean {
    const saved = (pattern as any)._savedContainerIds;
    if (!saved || !pattern.container_ids) return false;
    if (saved.length !== pattern.container_ids.length) return true;
    return !saved.every((id: string) => pattern.container_ids!.includes(id));
  }

  function formatCurrency(amountInOre: number): string {
    return (amountInOre / 100).toLocaleString("da-DK", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
  }

  function handleAddPattern() {
    error = null;
    editingPatternIndex = null;
    patternAmount = "";
    const today = new Date();
    patternStartDate = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}-${String(today.getDate()).padStart(2, "0")}`;
    patternEndDate = "";
    patternHasEndDate = false;
    patternContainerIds = direction !== "transfer" ? [...effectiveContainerIds] : [];
    patternBasis = "date";
    patternRepeats = false;
    patternFrequency = "monthly";
    patternMonthlyType = "fixed";
    patternPeriodFrequency = "monthly";
    patternPeriodYear = today.getFullYear();
    patternPeriodMonth = today.getMonth() + 1;
    patternEndPeriodYear = today.getFullYear();
    patternEndPeriodMonth = 12;
    patternRecurrenceInterval = 1;
    patternRecurrenceWeekday = 0;
    patternRecurrenceDayOfMonth = 1;
    patternRecurrenceRelativePosition = "first";
    patternRecurrenceMonth = 1;
    patternRecurrenceMonths = [];
    patternRecurrenceBankDayAdjustment = "none";
    patternBankDayKeepInMonth = true;
    patternBankDayNoDedup = false;
    patternYearlyType = "fixed";
    patternBankDayNumber = 1;
    patternBankDayFromEnd = "start";
    activeView = "pattern-editor";
  }

  function handleEditPattern(index: number) {
    error = null;
    const pattern = amountPatterns[index];
    editingPatternIndex = index;
    patternAmount = (pattern.amount / 100).toFixed(2);
    patternStartDate = pattern.start_date;
    patternEndDate = pattern.end_date || "";
    patternHasEndDate = pattern.end_date !== null;
    patternContainerIds = pattern.container_ids || [];

    if (pattern.recurrence_pattern) {
      const rtype = pattern.recurrence_pattern.type;
      // Determine basis
      patternBasis =
        rtype === "period_once" ||
        rtype === "period_monthly" ||
        rtype === "period_yearly"
          ? "period"
          : "date";
      // Determine repeats
      patternRepeats = !["once", "period_once"].includes(rtype);
      // Determine frequency (for date-based patterns)
      if (rtype === "daily") patternFrequency = "daily";
      else if (rtype === "weekly") patternFrequency = "weekly";
      else if (
        rtype === "monthly_fixed" ||
        rtype === "monthly_relative" ||
        rtype === "monthly_bank_day"
      )
        patternFrequency = "monthly";
      else if (rtype === "yearly" || rtype === "yearly_bank_day")
        patternFrequency = "yearly";
      // Determine period frequency (for period-based repeating patterns)
      if (rtype === "period_monthly") patternPeriodFrequency = "monthly";
      else if (rtype === "period_yearly") patternPeriodFrequency = "yearly";
      // Monthly subtype
      if (rtype === "monthly_relative") patternMonthlyType = "relative";
      else if (rtype === "monthly_bank_day") patternMonthlyType = "bank_day";
      else patternMonthlyType = "fixed";
      // Period + no repeat: extract month/year from start_date
      if (rtype === "period_once") {
        const d = new Date(pattern.start_date + "T00:00:00");
        patternPeriodYear = d.getFullYear();
        patternPeriodMonth = d.getMonth() + 1;
      }
      // Period + monthly repeat: extract month/year from start_date
      if (rtype === "period_monthly") {
        const d = new Date(pattern.start_date + "T00:00:00");
        patternPeriodYear = d.getFullYear();
        patternPeriodMonth = d.getMonth() + 1;
      }
      // Period + repeats: extract end periods
      if (rtype === "period_monthly" && pattern.end_date) {
        const endD = new Date(pattern.end_date + "T00:00:00");
        patternEndPeriodYear = endD.getFullYear();
        patternEndPeriodMonth = endD.getMonth() + 1;
      }
      if (rtype === "period_yearly" && pattern.end_date) {
        const endD = new Date(pattern.end_date + "T00:00:00");
        patternEndPeriodYear = endD.getFullYear();
        patternEndPeriodMonth = endD.getMonth() + 1;
      }

      patternRecurrenceInterval = pattern.recurrence_pattern.interval || 1;
      patternRecurrenceWeekday = pattern.recurrence_pattern.weekday || 0;
      patternRecurrenceDayOfMonth =
        pattern.recurrence_pattern.day_of_month || 1;
      patternRecurrenceRelativePosition =
        pattern.recurrence_pattern.relative_position || "first";
      patternRecurrenceMonth = pattern.recurrence_pattern.month || 1;
      patternRecurrenceMonths = pattern.recurrence_pattern.months || [];
      patternRecurrenceBankDayAdjustment =
        pattern.recurrence_pattern.bank_day_adjustment || "none";
      patternBankDayKeepInMonth =
        pattern.recurrence_pattern.bank_day_keep_in_month ?? true;
      patternBankDayNoDedup =
        pattern.recurrence_pattern.bank_day_no_dedup ?? false;
      patternBankDayNumber = pattern.recurrence_pattern.bank_day_number || 1;
      patternBankDayFromEnd = pattern.recurrence_pattern.bank_day_from_end
        ? "end"
        : "start";
      if (rtype === "yearly") {
        patternYearlyType =
          pattern.recurrence_pattern.relative_position !== undefined &&
          pattern.recurrence_pattern.weekday !== undefined
            ? "relative"
            : "fixed";
      } else if (rtype === "yearly_bank_day") {
        patternYearlyType = "bank_day";
      }
    } else {
      patternBasis = "date";
      patternRepeats = false;
      patternFrequency = "monthly";
      patternMonthlyType = "fixed";
      patternPeriodFrequency = "monthly";
      patternPeriodYear = new Date().getFullYear();
      patternPeriodMonth = new Date().getMonth() + 1;
      patternEndPeriodYear = new Date().getFullYear();
      patternEndPeriodMonth = 12;
      patternRecurrenceInterval = 1;
      patternRecurrenceWeekday = 0;
      patternRecurrenceDayOfMonth = 1;
      patternRecurrenceRelativePosition = "first";
      patternRecurrenceMonth = 1;
      patternRecurrenceMonths = [];
      patternRecurrenceBankDayAdjustment = "none";
      patternBankDayKeepInMonth = true;
      patternBankDayNoDedup = false;
      patternYearlyType = "fixed";
      patternBankDayNumber = 1;
      patternBankDayFromEnd = "start";
    }

    activeView = "pattern-editor";
  }

  function handleClonePattern(index: number) {
    error = null;
    const pattern = amountPatterns[index];
    editingPatternIndex = null; // CRITICAL: null means create NEW pattern
    patternAmount = (pattern.amount / 100).toFixed(2);
    patternStartDate = pattern.start_date;
    patternEndDate = pattern.end_date || "";
    patternHasEndDate = pattern.end_date !== null;
    patternContainerIds = pattern.container_ids || [];

    if (pattern.recurrence_pattern) {
      const rtype = pattern.recurrence_pattern.type;
      // Determine basis
      patternBasis =
        rtype === "period_once" ||
        rtype === "period_monthly" ||
        rtype === "period_yearly"
          ? "period"
          : "date";
      // Determine repeats
      patternRepeats = !["once", "period_once"].includes(rtype);
      // Determine frequency (for date-based patterns)
      if (rtype === "daily") patternFrequency = "daily";
      else if (rtype === "weekly") patternFrequency = "weekly";
      else if (
        rtype === "monthly_fixed" ||
        rtype === "monthly_relative" ||
        rtype === "monthly_bank_day"
      )
        patternFrequency = "monthly";
      else if (rtype === "yearly" || rtype === "yearly_bank_day")
        patternFrequency = "yearly";
      // Determine period frequency (for period-based repeating patterns)
      if (rtype === "period_monthly") patternPeriodFrequency = "monthly";
      else if (rtype === "period_yearly") patternPeriodFrequency = "yearly";
      // Monthly subtype
      if (rtype === "monthly_relative") patternMonthlyType = "relative";
      else if (rtype === "monthly_bank_day") patternMonthlyType = "bank_day";
      else patternMonthlyType = "fixed";
      // Period + no repeat: extract month/year from start_date
      if (rtype === "period_once") {
        const d = new Date(pattern.start_date + "T00:00:00");
        patternPeriodYear = d.getFullYear();
        patternPeriodMonth = d.getMonth() + 1;
      }
      // Period + monthly repeat: extract month/year from start_date
      if (rtype === "period_monthly") {
        const d = new Date(pattern.start_date + "T00:00:00");
        patternPeriodYear = d.getFullYear();
        patternPeriodMonth = d.getMonth() + 1;
      }
      // Period + repeats: extract end periods
      if (rtype === "period_monthly" && pattern.end_date) {
        const endD = new Date(pattern.end_date + "T00:00:00");
        patternEndPeriodYear = endD.getFullYear();
        patternEndPeriodMonth = endD.getMonth() + 1;
      }
      if (rtype === "period_yearly" && pattern.end_date) {
        const endD = new Date(pattern.end_date + "T00:00:00");
        patternEndPeriodYear = endD.getFullYear();
        patternEndPeriodMonth = endD.getMonth() + 1;
      }

      patternRecurrenceInterval = pattern.recurrence_pattern.interval || 1;
      patternRecurrenceWeekday = pattern.recurrence_pattern.weekday || 0;
      patternRecurrenceDayOfMonth =
        pattern.recurrence_pattern.day_of_month || 1;
      patternRecurrenceRelativePosition =
        pattern.recurrence_pattern.relative_position || "first";
      patternRecurrenceMonth = pattern.recurrence_pattern.month || 1;
      patternRecurrenceMonths = pattern.recurrence_pattern.months || [];
      patternRecurrenceBankDayAdjustment =
        pattern.recurrence_pattern.bank_day_adjustment || "none";
      patternBankDayKeepInMonth =
        pattern.recurrence_pattern.bank_day_keep_in_month ?? true;
      patternBankDayNoDedup =
        pattern.recurrence_pattern.bank_day_no_dedup ?? false;
      patternBankDayNumber = pattern.recurrence_pattern.bank_day_number || 1;
      patternBankDayFromEnd = pattern.recurrence_pattern.bank_day_from_end
        ? "end"
        : "start";
      if (rtype === "yearly") {
        patternYearlyType =
          pattern.recurrence_pattern.relative_position !== undefined &&
          pattern.recurrence_pattern.weekday !== undefined
            ? "relative"
            : "fixed";
      } else if (rtype === "yearly_bank_day") {
        patternYearlyType = "bank_day";
      }
    } else {
      patternBasis = "date";
      patternRepeats = false;
      patternFrequency = "monthly";
      patternMonthlyType = "fixed";
      patternPeriodFrequency = "monthly";
      patternPeriodYear = new Date().getFullYear();
      patternPeriodMonth = new Date().getMonth() + 1;
      patternEndPeriodYear = new Date().getFullYear();
      patternEndPeriodMonth = 12;
      patternRecurrenceInterval = 1;
      patternRecurrenceWeekday = 0;
      patternRecurrenceDayOfMonth = 1;
      patternRecurrenceRelativePosition = "first";
      patternRecurrenceMonth = 1;
      patternRecurrenceMonths = [];
      patternRecurrenceBankDayAdjustment = "none";
      patternBankDayKeepInMonth = true;
      patternBankDayNoDedup = false;
      patternYearlyType = "fixed";
      patternBankDayNumber = 1;
      patternBankDayFromEnd = "start";
    }

    activeView = "pattern-editor";
  }

  function handleDeletePattern(index: number) {
    amountPatterns = amountPatterns.filter((_, i) => i !== index);
  }

  function handleSavePattern() {
    // Validate pattern
    if (!patternAmount) {
      error = $_("budgetPosts.validation.amountRequired");
      return;
    }

    // Validate based on pattern type
    if (patternBasis === "period") {
      if (patternRecurrenceType === "period_once") {
        // Period + no repeat: validate month/year are set
        if (!patternPeriodMonth || !patternPeriodYear) {
          error = $_("budgetPosts.validation.startDateRequired");
          return;
        }
      } else if (patternRecurrenceType === "period_monthly") {
        // Period + monthly: validate start period
        if (!patternPeriodMonth || !patternPeriodYear) {
          error = $_("budgetPosts.validation.startDateRequired");
          return;
        }
      } else if (patternRecurrenceType === "period_yearly") {
        // Period + yearly: validate start period and months
        if (!patternPeriodMonth || !patternPeriodYear) {
          error = $_("budgetPosts.validation.startDateRequired");
          return;
        }
        if (patternRecurrenceMonths.length === 0) {
          error = $_("budgetPosts.validation.monthsRequired");
          return;
        }
      }
    } else {
      // Date-based: validate start date
      if (!patternStartDate) {
        error = $_("budgetPosts.validation.startDateRequired");
        return;
      }
    }

    // Validate end date is after start date
    if (
      patternHasEndDate &&
      patternEndDate &&
      patternEndDate < patternStartDate
    ) {
      error = $_("budgetPosts.validation.endDateBeforeStartDate");
      return;
    }

    // Validate pattern containers
    if (direction !== "transfer") {
      // Must select at least one container
      if (patternContainerIds.length === 0) {
        error = $_("budgetPosts.validation.patternAccountsRequired");
        return;
      }
      // Must be subset of budget post's container pool
      const invalidContainers = patternContainerIds.filter(id => !effectiveContainerIds.includes(id));
      if (invalidContainers.length > 0) {
        error = $_("budgetPosts.validation.patternAccountsNotInPool");
        return;
      }
    }

    // Build recurrence pattern
    const recurrence: RecurrencePattern = {
      type: patternRecurrenceType,
    };

    // Determine actual start_date and end_date based on type
    let actualStartDate = patternStartDate;
    let actualEndDate = patternHasEndDate ? patternEndDate : null;

    if (patternRecurrenceType === "once") {
      // once: start_date IS the occurrence date, no end_date
      actualStartDate = patternStartDate;
      actualEndDate = null;
      if (patternRecurrenceBankDayAdjustment !== "none") {
        recurrence.bank_day_adjustment = patternRecurrenceBankDayAdjustment;
        recurrence.bank_day_keep_in_month = patternBankDayKeepInMonth;
        recurrence.bank_day_no_dedup = patternBankDayNoDedup;
      }
    } else if (patternRecurrenceType === "period_once") {
      // period_once: auto-derive start_date from month/year
      actualStartDate = `${patternPeriodYear}-${String(patternPeriodMonth).padStart(2, "0")}-01`;
      actualEndDate = null;
    } else if (patternRecurrenceType === "period_monthly") {
      // period_monthly: derive start_date and end_date from period selectors
      actualStartDate = `${patternPeriodYear}-${String(patternPeriodMonth).padStart(2, "0")}-01`;
      if (patternHasEndDate) {
        const lastDay = new Date(
          patternEndPeriodYear,
          patternEndPeriodMonth,
          0,
        ).getDate();
        actualEndDate = `${patternEndPeriodYear}-${String(patternEndPeriodMonth).padStart(2, "0")}-${String(lastDay).padStart(2, "0")}`;
      } else {
        actualEndDate = null;
      }
      recurrence.interval = patternRecurrenceInterval;
    } else if (patternRecurrenceType === "period_yearly") {
      // period_yearly: derive start_date and end_date from period selectors
      actualStartDate = `${patternPeriodYear}-${String(patternPeriodMonth).padStart(2, "0")}-01`;
      if (patternHasEndDate) {
        const lastDay = new Date(
          patternEndPeriodYear,
          patternEndPeriodMonth,
          0,
        ).getDate();
        actualEndDate = `${patternEndPeriodYear}-${String(patternEndPeriodMonth).padStart(2, "0")}-${String(lastDay).padStart(2, "0")}`;
      } else {
        actualEndDate = null;
      }
      recurrence.months = patternRecurrenceMonths;
      recurrence.interval = patternRecurrenceInterval;
    } else if (patternRecurrenceType === "daily") {
      recurrence.interval = patternRecurrenceInterval;
      recurrence.bank_day_adjustment = patternRecurrenceBankDayAdjustment;
      if (patternRecurrenceBankDayAdjustment !== "none") {
        recurrence.bank_day_keep_in_month = patternBankDayKeepInMonth;
        recurrence.bank_day_no_dedup = patternBankDayNoDedup;
      }
    } else if (patternRecurrenceType === "weekly") {
      recurrence.weekday = patternRecurrenceWeekday;
      recurrence.interval = patternRecurrenceInterval;
      recurrence.bank_day_adjustment = patternRecurrenceBankDayAdjustment;
      if (patternRecurrenceBankDayAdjustment !== "none") {
        recurrence.bank_day_keep_in_month = patternBankDayKeepInMonth;
        recurrence.bank_day_no_dedup = patternBankDayNoDedup;
      }
    } else if (patternRecurrenceType === "monthly_fixed") {
      recurrence.day_of_month = patternRecurrenceDayOfMonth;
      recurrence.interval = patternRecurrenceInterval;
      recurrence.bank_day_adjustment = patternRecurrenceBankDayAdjustment;
      if (patternRecurrenceBankDayAdjustment !== "none") {
        recurrence.bank_day_keep_in_month = patternBankDayKeepInMonth;
        recurrence.bank_day_no_dedup = patternBankDayNoDedup;
      }
    } else if (patternRecurrenceType === "monthly_relative") {
      recurrence.weekday = patternRecurrenceWeekday;
      recurrence.relative_position = patternRecurrenceRelativePosition;
      recurrence.interval = patternRecurrenceInterval;
      recurrence.bank_day_adjustment = patternRecurrenceBankDayAdjustment;
      if (patternRecurrenceBankDayAdjustment !== "none") {
        recurrence.bank_day_keep_in_month = patternBankDayKeepInMonth;
        recurrence.bank_day_no_dedup = patternBankDayNoDedup;
      }
    } else if (patternRecurrenceType === "monthly_bank_day") {
      recurrence.bank_day_number = patternBankDayNumber;
      recurrence.bank_day_from_end = patternBankDayFromEnd === "end";
      recurrence.interval = patternRecurrenceInterval;
      // No bank_day_adjustment for bank day types
    } else if (patternRecurrenceType === "yearly") {
      recurrence.month = patternRecurrenceMonth;
      recurrence.interval = patternRecurrenceInterval;
      recurrence.bank_day_adjustment = patternRecurrenceBankDayAdjustment;
      if (patternRecurrenceBankDayAdjustment !== "none") {
        recurrence.bank_day_keep_in_month = patternBankDayKeepInMonth;
        recurrence.bank_day_no_dedup = patternBankDayNoDedup;
      }
      if (patternYearlyType === "relative") {
        recurrence.weekday = patternRecurrenceWeekday;
        recurrence.relative_position = patternRecurrenceRelativePosition;
      } else {
        recurrence.day_of_month = patternRecurrenceDayOfMonth;
      }
    } else if (patternRecurrenceType === "yearly_bank_day") {
      recurrence.month = patternRecurrenceMonth;
      recurrence.bank_day_number = patternBankDayNumber;
      recurrence.bank_day_from_end = patternBankDayFromEnd === "end";
      recurrence.interval = patternRecurrenceInterval;
      // No bank_day_adjustment for bank day types
    }

    const newPattern: AmountPattern & { _clientId: number } = {
      amount: Math.round(parseFloat(patternAmount) * 100),
      start_date: actualStartDate,
      end_date: actualEndDate,
      recurrence_pattern: recurrence,
      container_ids: direction !== "transfer" ? patternContainerIds : null,
      _savedContainerIds: direction !== "transfer" ? [...patternContainerIds] : null,
      _clientId:
        editingPatternIndex !== null
          ? (amountPatterns[editingPatternIndex] as any)._clientId ??
            patternIdCounter++
          : patternIdCounter++,
    } as any;

    if (editingPatternIndex !== null) {
      // Edit existing pattern
      amountPatterns = amountPatterns.map((p, i) =>
        i === editingPatternIndex ? newPattern : p,
      );
    } else {
      // Add new pattern
      amountPatterns = [...amountPatterns, newPattern];
    }

    activeView = "main";
    error = null;
  }

  function handleCancelPattern() {
    activeView = "main";
    error = null;
  }

  function formatPatternRecurrence(
    pattern: AmountPattern,
    currentLocale: string | null | undefined,
  ): string {
    if (!pattern.recurrence_pattern) return "-";

    const recurrence = pattern.recurrence_pattern;
    const interval = recurrence.interval || 1;
    const weekdayKeys = [
      "monday",
      "tuesday",
      "wednesday",
      "thursday",
      "friday",
      "saturday",
      "sunday",
    ];

    let baseText = "";

    // Generate type-specific text
    if (recurrence.type === "once") {
      baseText = $_("budgetPosts.recurrence.description.once");
    } else if (recurrence.type === "daily") {
      baseText =
        interval === 1
          ? $_("budgetPosts.recurrence.description.daily")
          : $_("budgetPosts.recurrence.description.dailyN", {
              values: { n: interval },
            });
    } else if (recurrence.type === "weekly") {
      const weekdayName =
        recurrence.weekday !== undefined
          ? $_(
              `budgetPosts.weekday.${weekdayKeys[recurrence.weekday]}`,
            ).toLowerCase()
          : "";
      baseText =
        interval === 1
          ? $_("budgetPosts.recurrence.description.weekly", {
              values: { weekday: weekdayName },
            })
          : $_("budgetPosts.recurrence.description.weeklyN", {
              values: { n: interval, weekday: weekdayName },
            });
    } else if (recurrence.type === "monthly_fixed") {
      baseText =
        interval === 1
          ? $_("budgetPosts.recurrence.description.monthlyFixed", {
              values: { day: recurrence.day_of_month },
            })
          : $_("budgetPosts.recurrence.description.monthlyFixedN", {
              values: { day: recurrence.day_of_month, n: interval },
            });
    } else if (recurrence.type === "monthly_relative") {
      const position = recurrence.relative_position
        ? $_(`budgetPosts.relativePosition.${recurrence.relative_position}`)
        : "";
      const weekdayName =
        recurrence.weekday !== undefined
          ? $_(
              `budgetPosts.weekday.${weekdayKeys[recurrence.weekday]}`,
            ).toLowerCase()
          : "";
      baseText =
        interval === 1
          ? $_("budgetPosts.recurrence.description.monthlyRelative", {
              values: { position, weekday: weekdayName },
            })
          : $_("budgetPosts.recurrence.description.monthlyRelativeN", {
              values: { position, weekday: weekdayName, n: interval },
            });
    } else if (recurrence.type === "monthly_bank_day") {
      const bankday = recurrence.bank_day_from_end
        ? recurrence.bank_day_number === 1
          ? $_("budgetPosts.recurrence.description.bankDayLast")
          : $_("budgetPosts.recurrence.description.bankDayNthLast", {
              values: { n: recurrence.bank_day_number },
            })
        : recurrence.bank_day_number === 1
          ? $_("budgetPosts.recurrence.description.bankDayFirst")
          : $_("budgetPosts.recurrence.description.bankDayNth", {
              values: { n: recurrence.bank_day_number },
            });
      baseText =
        interval === 1
          ? $_("budgetPosts.recurrence.description.monthlyBankDay", {
              values: { bankday },
            })
          : $_("budgetPosts.recurrence.description.monthlyBankDayN", {
              values: { bankday, interval },
            });
    } else if (recurrence.type === "yearly") {
      // Determine if fixed or relative mode
      if (
        recurrence.day_of_month !== undefined &&
        recurrence.month !== undefined
      ) {
        // Fixed mode: day + month
        const monthName = formatMonth(recurrence.month, currentLocale);
        baseText =
          interval === 1
            ? $_("budgetPosts.recurrence.description.yearlyFixed", {
                values: { day: recurrence.day_of_month, month: monthName },
              })
            : $_("budgetPosts.recurrence.description.yearlyFixedN", {
                values: {
                  day: recurrence.day_of_month,
                  month: monthName,
                  n: interval,
                },
              });
      } else if (
        recurrence.relative_position !== undefined &&
        recurrence.weekday !== undefined &&
        recurrence.month !== undefined
      ) {
        // Relative mode: position + weekday + month
        const position = $_(
          `budgetPosts.relativePosition.${recurrence.relative_position}`,
        );
        const weekdayName = $_(
          `budgetPosts.weekday.${weekdayKeys[recurrence.weekday]}`,
        ).toLowerCase();
        const monthName = formatMonth(recurrence.month, currentLocale);
        baseText =
          interval === 1
            ? $_("budgetPosts.recurrence.description.yearlyRelative", {
                values: { position, weekday: weekdayName, month: monthName },
              })
            : $_("budgetPosts.recurrence.description.yearlyRelativeN", {
                values: {
                  position,
                  weekday: weekdayName,
                  month: monthName,
                  n: interval,
                },
              });
      } else {
        baseText = $_("budgetPosts.recurrence.yearly");
      }
    } else if (recurrence.type === "yearly_bank_day") {
      const bankday = recurrence.bank_day_from_end
        ? recurrence.bank_day_number === 1
          ? $_("budgetPosts.recurrence.description.bankDayLast")
          : $_("budgetPosts.recurrence.description.bankDayNthLast", {
              values: { n: recurrence.bank_day_number },
            })
        : recurrence.bank_day_number === 1
          ? $_("budgetPosts.recurrence.description.bankDayFirst")
          : $_("budgetPosts.recurrence.description.bankDayNth", {
              values: { n: recurrence.bank_day_number },
            });
      const monthName =
        recurrence.month !== undefined
          ? formatMonth(recurrence.month, currentLocale)
          : "";
      baseText =
        interval === 1
          ? $_("budgetPosts.recurrence.description.yearlyBankDay", {
              values: { bankday, month: monthName },
            })
          : $_("budgetPosts.recurrence.description.yearlyBankDayN", {
              values: { bankday, month: monthName, interval },
            });
    } else if (recurrence.type === "period_once") {
      baseText = $_("budgetPosts.recurrence.description.periodOnce");
    } else if (recurrence.type === "period_monthly") {
      baseText =
        interval === 1
          ? $_("budgetPosts.recurrence.description.periodMonthly")
          : $_("budgetPosts.recurrence.description.periodMonthlyN", {
              values: { n: interval },
            });
    } else if (recurrence.type === "period_yearly") {
      const monthNames = formatList(
        (recurrence.months || []).map((m) => formatMonth(m, currentLocale)),
        currentLocale,
      );
      baseText =
        interval === 1
          ? $_("budgetPosts.recurrence.description.periodYearly", {
              values: { months: monthNames },
            })
          : $_("budgetPosts.recurrence.description.periodYearlyN", {
              values: { months: monthNames, n: interval },
            });
    } else {
      return recurrence.type;
    }

    // End primary text with period
    baseText += ".";

    // Append bank day adjustment as separate sentence
    if (
      recurrence.bank_day_adjustment &&
      recurrence.bank_day_adjustment !== "none" &&
      ![
        "monthly_bank_day",
        "yearly_bank_day",
        "period_once",
        "period_monthly",
        "period_yearly",
      ].includes(recurrence.type)
    ) {
      const keepInMonth = recurrence.bank_day_keep_in_month ?? false;
      if (recurrence.bank_day_adjustment === "next") {
        baseText +=
          " " +
          $_(
            keepInMonth
              ? "budgetPosts.recurrence.description.bankDayAdjustedNextKeepMonth"
              : "budgetPosts.recurrence.description.bankDayAdjustedNext",
          );
      } else if (recurrence.bank_day_adjustment === "previous") {
        baseText +=
          " " +
          $_(
            keepInMonth
              ? "budgetPosts.recurrence.description.bankDayAdjustedPreviousKeepMonth"
              : "budgetPosts.recurrence.description.bankDayAdjustedPrevious",
          );
      }

      // Append no_dedup note if enabled
      if (recurrence.bank_day_no_dedup) {
        baseText +=
          " " + $_("budgetPosts.recurrence.description.bankDayNoDedupNote");
      }
    }

    return baseText;
  }

  function togglePatternMonth(month: number) {
    if (patternRecurrenceMonths.includes(month)) {
      patternRecurrenceMonths = patternRecurrenceMonths.filter(
        (m) => m !== month,
      );
    } else {
      patternRecurrenceMonths = [...patternRecurrenceMonths, month].sort(
        (a, b) => a - b,
      );
    }
  }

  // Filter containers by type
  let cashboxContainers = $derived(containers.filter((c) => c.type === "cashbox"));
  let piggybankContainers = $derived(containers.filter((c) => c.type === "piggybank"));
  let debtContainers = $derived(containers.filter((c) => c.type === "debt"));

  // Ancestor detection: find nearest parent in the hierarchy
  let ancestorPost = $derived.by(() => {
    if (direction === 'transfer') return null;
    const chips = [...categoryPathChips];
    if (chips.length < 2) return null;
    // Walk up from chips[:-1] to chips[:1], looking for nearest ancestor
    for (let len = chips.length - 1; len >= 1; len--) {
      const prefix = chips.slice(0, len);
      const match = existingPosts.find(p =>
        p.direction === direction &&
        p.category_path &&
        p.category_path.length === prefix.length &&
        p.category_path.every((seg: string, i: number) => seg === prefix[i])
      );
      // Don't match the post being edited (when editing, not creating)
      if (match && (!budgetPost || match.id !== budgetPost.id)) return match;
    }
    return null;
  });

  let ancestorConstrainedContainerIds = $derived(
    ancestorPost?.container_ids ?? null
  );

  // Determine ancestor's container mode
  let ancestorContainerMode = $derived.by(() => {
    if (!ancestorPost || !ancestorPost.container_ids) return null;
    // Check what type of containers the ancestor uses
    const ancestorContainers = containers.filter(c => ancestorPost!.container_ids!.includes(c.id));
    if (ancestorContainers.length === 0) return null;
    // If any non-cashbox, it's piggybank or debt mode
    const nonCashbox = ancestorContainers.find(c => c.type !== 'cashbox');
    if (nonCashbox) return nonCashbox.type as 'piggybank' | 'debt';
    return 'cashbox';
  });

  // Filter containers based on ancestor constraint
  let filteredCashboxContainers = $derived(
    ancestorConstrainedContainerIds
      ? cashboxContainers.filter(c => ancestorConstrainedContainerIds!.includes(c.id))
      : cashboxContainers
  );

  let filteredPiggybankContainers = $derived(
    ancestorConstrainedContainerIds
      ? piggybankContainers.filter(c => ancestorConstrainedContainerIds!.includes(c.id))
      : piggybankContainers
  );

  let filteredDebtContainers = $derived(
    ancestorConstrainedContainerIds
      ? debtContainers.filter(c => ancestorConstrainedContainerIds!.includes(c.id))
      : debtContainers
  );

  let availableContainerTypes = $derived(
    (['cashbox', 'piggybank', 'debt'] as const).filter(type =>
      type === 'cashbox' ? filteredCashboxContainers.length > 0 :
      type === 'piggybank' ? filteredPiggybankContainers.length > 0 :
      filteredDebtContainers.length > 0
    )
  );

  let effectiveContainerIds = $derived(
    containerMode === 'cashbox' ? containerIds : (specialContainerId ? [specialContainerId] : [])
  );
  let availablePatternContainers = $derived(
    containers.filter((c) => effectiveContainerIds.includes(c.id))
  );
  let allContainers = $derived(containers);
  let patternEditorDisabled = $derived(direction !== "transfer" && effectiveContainerIds.length === 0);

  // Detect descendant posts for cascade confirmation
  let descendantPosts = $derived.by(() => {
    if (direction === 'transfer') return [];
    // Use the post being edited's path, or current chips for new posts
    const myPath = budgetPost?.category_path ?? [...categoryPathChips];
    if (myPath.length === 0) return [];
    return existingPosts.filter(p =>
      p.id !== budgetPost?.id &&
      p.direction === direction &&
      p.category_path &&
      p.category_path.length > myPath.length &&
      myPath.every((seg: string, i: number) => p.category_path![i] === seg)
    );
  });

  // Auto-narrow containers when ancestor constraint changes
  $effect(() => {
    const constraint = ancestorConstrainedContainerIds;
    if (!constraint || direction === 'transfer') return;

    // Force container mode to match ancestor
    if (ancestorContainerMode && containerMode !== ancestorContainerMode) {
      switchContainerMode(ancestorContainerMode as 'cashbox' | 'piggybank' | 'debt');
    }

    if (containerMode === 'cashbox') {
      const filtered = containerIds.filter(id => constraint.includes(id));
      if (filtered.length !== containerIds.length) {
        containerIds = filtered;
      }
    } else if (specialContainerId && !constraint.includes(specialContainerId)) {
      // Current special container not in ancestor's pool - auto-select first available
      specialContainerId = constraint[0] ?? null;
    }
  });

  // Auto-sync pattern container_ids when the post-level container pool changes.
  // Uses _savedContainerIds snapshot to restore user intent when containers are re-added.
  $effect(() => {
    const currentPool = effectiveContainerIds;
    if (direction === "transfer") return;
    if (amountPatterns.length === 0) return;

    let changed = false;
    const updated = amountPatterns.map(p => {
      // Start from the saved snapshot (user's last confirmed selection)
      const saved = (p as any)._savedContainerIds;
      const base = saved && saved.length > 0 ? saved : p.container_ids;

      if (!base || base.length === 0) {
        // No saved or current selection - assign full pool
        if (currentPool.length > 0) {
          const newIds = [...currentPool];
          if (!arraysEqual(p.container_ids, newIds)) {
            changed = true;
            return { ...p, container_ids: newIds };
          }
        }
        return p;
      }

      // Filter saved selection down to what's available in current pool
      const filtered = base.filter((id: string) => currentPool.includes(id));
      const newIds = filtered.length > 0 ? filtered : [...currentPool];

      if (!arraysEqual(p.container_ids, newIds)) {
        changed = true;
        return { ...p, container_ids: newIds };
      }
      return p;
    });
    if (changed) amountPatterns = updated;
  });

  // Month labels for recurrence display
  let monthLabelsFull = $derived(
    Array.from({ length: 12 }, (_, i) => {
      const name = formatMonth(i + 1, $locale, "long");
      return name.charAt(0).toUpperCase() + name.slice(1);
    }),
  );
  let monthLabelsShort = $derived(
    Array.from({ length: 12 }, (_, i) => formatMonth(i + 1, $locale, "short")),
  );
</script>

{#if show}
  <div class="modal-backdrop" onclick={handleBackdropClick} role="presentation">
    <div class="modal" role="dialog" aria-modal="true" onclick={(e) => e.stopPropagation()}>
      <div class="modal-header">
        <h2>
          {#if activeView === "pattern-editor"}
            {editingPatternIndex !== null
              ? $_("budgetPosts.editPattern")
              : $_("budgetPosts.addPattern")}
          {:else}
            {budgetPost ? $_("budgetPosts.edit") : $_("budgetPosts.create")}
          {/if}
        </h2>
        <button
          class="close-button"
          onclick={handleClose}
          type="button"
          aria-label={$_("common.close")}
        >
          <svg
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
          >
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
      </div>

      <form onsubmit={handleSubmit}>
        <div class="modal-body">
          {#if activeView === "main"}
            <!-- Direction Selector -->
            <div class="form-group">
              <label>{$_("budgetPosts.directionType.label")}</label>
              <div class="direction-selector">
                <button
                  type="button"
                  class="direction-btn"
                  class:selected={direction === "income"}
                  onclick={() => (direction = "income")}
                  disabled={isEditMode || saving}
                >
                  {$_("budgetPosts.directionType.income")}
                </button>
                <button
                  type="button"
                  class="direction-btn"
                  class:selected={direction === "expense"}
                  onclick={() => (direction = "expense")}
                  disabled={isEditMode || saving}
                >
                  {$_("budgetPosts.directionType.expense")}
                </button>
                <button
                  type="button"
                  class="direction-btn"
                  class:selected={direction === "transfer"}
                  onclick={() => (direction = "transfer")}
                  disabled={isEditMode || saving}
                >
                  {$_("budgetPosts.directionType.transfer")}
                </button>
              </div>
            </div>

            {#if direction === "transfer"}
              <!-- Transfer: from/to containers -->
              <div class="form-row">
                <div class="form-group">
                  <label for="from-account">
                    {$_("budgetPosts.accounts.from")}
                    <span class="required">*</span>
                  </label>
                  <select
                    id="from-account"
                    bind:value={transferFromContainerId}
                    required
                    disabled={saving}
                  >
                    <option value={null}
                      >{$_("budgetPosts.accounts.selectAccount")}</option
                    >
                    {#each allContainers as container (container.id)}
                      <option value={container.id}
                        >{getContainerDisplayName(container)}</option
                      >
                    {/each}
                  </select>
                </div>
                <div class="form-group">
                  <label for="to-account">
                    {$_("budgetPosts.accounts.to")}
                    <span class="required">*</span>
                  </label>
                  <select
                    id="to-account"
                    bind:value={transferToContainerId}
                    required
                    disabled={saving}
                  >
                    <option value={null}
                      >{$_("budgetPosts.accounts.selectAccount")}</option
                    >
                    {#each allContainers as container (container.id)}
                      <option value={container.id}
                        >{getContainerDisplayName(container)}</option
                      >
                    {/each}
                  </select>
                </div>
              </div>
            {:else}
              <!-- Income/Expense: category + container pool -->
              <div class="form-group">
                <label for="post-category">
                  {$_("budgetPosts.categoryPath")}
                  <span class="required">*</span>
                </label>
                <div class="category-breadcrumb-wrapper">
                  <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
                  <div
                    class="breadcrumb-input-area"
                    onclick={() =>
                      document.getElementById("post-category")?.focus()}
                  >
                    {#each categoryPathChips as chip, index}
                      <div
                        class="breadcrumb-chip"
                        class:has-next={index < categoryPathChips.length - 1}
                      >
                        <span class="chip-text">{chip}</span>
                        <button
                          type="button"
                          class="chip-remove"
                          aria-label={$_("common.remove") + " " + chip}
                          onclick={(e) => {
                            e.stopPropagation();
                            removeChipAt(index);
                          }}
                          disabled={saving}
                        >
                          <svg
                            xmlns="http://www.w3.org/2000/svg"
                            width="14"
                            height="14"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            stroke-width="2"
                            stroke-linecap="round"
                            stroke-linejoin="round"
                            ><line x1="18" y1="6" x2="6" y2="18"></line><line
                              x1="6"
                              y1="6"
                              x2="18"
                              y2="18"
                            ></line></svg
                          >
                        </button>
                      </div>
                    {/each}
                    <input
                      id="post-category"
                      type="text"
                      bind:value={categoryInputValue}
                      placeholder={categoryPathChips.length === 0
                        ? $_("budgetPosts.categoryPathPlaceholder")
                        : ""}
                      disabled={saving}
                      onfocus={() => (showSuggestions = true)}
                      onblur={() => {
                        setTimeout(() => {
                          const input = document.getElementById("post-category");
                          if (input && document.activeElement === input) return;
                          showSuggestions = false;
                          highlightedIndex = -1;
                        }, 200);
                      }}
                      onkeydown={handleCategoryKeydown}
                      autocomplete="off"
                    />
                  </div>
                  {#if showSuggestions && levelAwareSuggestions.length > 0}
                    <div class="autocomplete-dropdown" transition:fade={{ duration: 150 }}>
                      {#each levelAwareSuggestions as suggestion, i}
                        <button
                          type="button"
                          class="autocomplete-option"
                          class:highlighted={i === highlightedIndex}
                          onmousedown={(e) => {
                            e.preventDefault();
                            selectSuggestion(suggestion);
                          }}
                          onmouseenter={() => {
                            highlightedIndex = i;
                          }}
                        >
                          {suggestion}
                        </button>
                      {/each}
                    </div>
                  {/if}
                </div>
                <p class="form-hint">{$_("budgetPosts.categoryPathHint")}</p>
              </div>

              <!-- Container Pool Selection -->
              <div class="form-group">
                <label>
                  {$_("budgetPosts.accounts.label")}
                  <span class="required">*</span>
                </label>

                {#if ancestorPost}
                  <div class="ancestor-info">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <circle cx="12" cy="12" r="10" />
                      <line x1="12" y1="16" x2="12" y2="12" />
                      <line x1="12" y1="8" x2="12.01" y2="8" />
                    </svg>
                    <span>{$_('budgetPosts.inheritance.parentConstraint', { values: { parent: ancestorPost.category_path?.join(' > ') ?? '' } })}</span>
                  </div>
                {/if}

                {#if availableContainerTypes.length > 1}
                  <div class="toggle-selector" class:toggle-selector-3={availableContainerTypes.length === 3}>
                    {#each availableContainerTypes as type}
                      <button
                        type="button"
                        class="toggle-btn"
                        class:selected={containerMode === type}
                        onclick={() => switchContainerMode(type)}
                        disabled={saving || (ancestorContainerMode !== null && type !== ancestorContainerMode)}
                      >
                        {$_(`budgetPosts.accounts.mode.${type}`)}
                      </button>
                    {/each}
                  </div>
                {/if}

                {#if containerMode === 'cashbox'}
                  <p class="form-hint">{$_('budgetPosts.accounts.hint.cashbox')}</p>
                  <div class="account-selector">
                    {#each filteredCashboxContainers as container (container.id)}
                      <label class="account-checkbox">
                        <input
                          type="checkbox"
                          checked={containerIds.includes(container.id)}
                          onchange={() => toggleContainerId(container.id)}
                          disabled={saving}
                        />
                        <span>{getContainerDisplayName(container)}</span>
                      </label>
                    {/each}
                  </div>
                {:else if containerMode === 'piggybank'}
                  <p class="form-hint">{$_('budgetPosts.accounts.hint.piggybank')}</p>
                  <select
                    bind:value={specialContainerId}
                    disabled={saving}
                  >
                    <option value={null}>{$_('budgetPosts.accounts.selectAccount')}</option>
                    {#each filteredPiggybankContainers as container (container.id)}
                      <option value={container.id}>
                        {getContainerDisplayName(container)}
                      </option>
                    {/each}
                  </select>
                {:else}
                  <p class="form-hint">{$_('budgetPosts.accounts.hint.debt')}</p>
                  <select
                    bind:value={specialContainerId}
                    disabled={saving}
                  >
                    <option value={null}>{$_('budgetPosts.accounts.selectAccount')}</option>
                    {#each filteredDebtContainers as container (container.id)}
                      <option value={container.id}>
                        {getContainerDisplayName(container)}
                      </option>
                    {/each}
                  </select>
                {/if}
              </div>

              <!-- Via Container (optional) - only for non-cashbox containers -->
              {#if containerMode !== 'cashbox' && specialContainerId}
                <div class="form-group">
                  <label for="via-account">
                    {$_("budgetPosts.viaAccount.label")}
                  </label>
                  <p class="form-hint">{$_("budgetPosts.viaAccount.hint")}</p>
                  <select
                    id="via-account"
                    bind:value={viaContainerId}
                    disabled={saving}
                  >
                    <option value={null}>{$_("budgetPosts.viaAccount.placeholder")}</option>
                    {#each cashboxContainers as container (container.id)}
                      <option value={container.id}>{getContainerDisplayName(container)}</option>
                    {/each}
                  </select>
                </div>
              {/if}
            {/if}

            <!-- Accumulate -->
            {#if direction === "expense"}
            <div class="form-group">
              <label class="checkbox-label">
                <input
                  type="checkbox"
                  bind:checked={accumulate}
                  disabled={saving}
                />
                <span>{$_("budgetPosts.accumulate")}</span>
              </label>
              <p class="form-hint">{$_("budgetPosts.accumulateHint")}</p>
            </div>
            {/if}

            <!-- Amount Patterns -->
            <div class="form-section">
              <h3>{$_("budgetPosts.amountPatterns")}</h3>
              <p class="form-hint">{$_("budgetPosts.patternsInfo")}</p>

              <OccurrenceTimeline
                {budgetId}
                patterns={amountPatterns}
                onColorsReady={(map) => {
                  patternColors = map;
                }}
              />

              {#if amountPatterns.length === 0}
                <p class="info-message">{$_("budgetPosts.noPatterns")}</p>
              {:else}
                <div class="patterns-list">
                  {#each amountPatterns as pattern, index (index)}
                    <div
                      class="pattern-card"
                      style:--pattern-color={patternColors.get(
                        (pattern as any)._clientId,
                      ) ?? "transparent"}
                      onclick={() => handleEditPattern(index)}
                      role="button"
                      tabindex="0"
                      onkeydown={(e) => {
                        if (e.key === "Enter" || e.key === " ") {
                          e.preventDefault();
                          handleEditPattern(index);
                        }
                      }}
                    >
                      <div class="pattern-info">
                        <div class="pattern-amount-display">
                          {formatCurrency(pattern.amount)} kr
                        </div>
                        <div class="pattern-meta">
                          {#if pattern.recurrence_pattern?.type === "once"}
                            <span
                              >{formatDateShort(
                                pattern.start_date,
                                $locale,
                              )}</span
                            >
                          {:else if pattern.recurrence_pattern?.type === "period_once"}
                            <span
                              >{formatMonthYear(
                                pattern.start_date,
                                $locale,
                              )}</span
                            >
                          {:else if pattern.recurrence_pattern?.type === "period_monthly" || pattern.recurrence_pattern?.type === "period_yearly"}
                            <span
                              >{formatMonthYearShort(
                                pattern.start_date,
                                $locale,
                              )}</span
                            >
                            <span class="separator">→</span>
                            <span
                              >{pattern.end_date
                                ? formatMonthYearShort(
                                    pattern.end_date,
                                    $locale,
                                  )
                                : $_("budgetPosts.noEndDate")}</span
                            >
                          {:else}
                            <span
                              >{formatDateShort(
                                pattern.start_date,
                                $locale,
                              )}</span
                            >
                            <span class="separator">→</span>
                            <span
                              >{pattern.end_date
                                ? formatDateShort(pattern.end_date, $locale)
                                : $_("budgetPosts.noEndDate")}</span
                            >
                          {/if}
                        </div>
                        <div class="pattern-recurrence-display">
                          {formatPatternRecurrence(pattern, $locale)}
                        </div>
                        {#if direction !== "transfer"}
                          <div class="pattern-accounts-display" class:pattern-accounts-missing={!pattern.container_ids || pattern.container_ids.length === 0}>
                            {#if pattern.container_ids && pattern.container_ids.length > 0}
                              {formatPatternContainerText(pattern.container_ids)}
                            {:else}
                              {$_("budgetPosts.patternNoContainers")}
                            {/if}
                          </div>
                          {#if isPatternAutoAdjusted(pattern)}
                            <div class="pattern-auto-adjusted">
                              {$_("budgetPosts.patternAutoAdjusted")}
                            </div>
                          {/if}
                        {/if}
                      </div>
                      <div class="pattern-actions">
                        <button
                          type="button"
                          class="btn-icon"
                          title={$_("budgetPosts.clonePattern")}
                          onclick={(e) => {
                            e.stopPropagation();
                            handleClonePattern(index);
                          }}
                        >
                          <svg
                            xmlns="http://www.w3.org/2000/svg"
                            width="16"
                            height="16"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            stroke-width="2"
                            stroke-linecap="round"
                            stroke-linejoin="round"
                          >
                            <rect width="14" height="14" x="8" y="8" rx="2" ry="2" />
                            <path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2" />
                          </svg>
                        </button>
                        <button
                          type="button"
                          class="btn-icon btn-danger"
                          onclick={(e) => {
                            e.stopPropagation();
                            handleDeletePattern(index);
                          }}
                          title={$_("budgetPosts.deletePattern")}
                        >
                          <svg
                            width="20"
                            height="20"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            stroke-width="2"
                          >
                            <polyline points="3 6 5 6 21 6" />
                            <path
                              d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"
                            />
                          </svg>
                        </button>
                      </div>
                    </div>
                  {/each}
                </div>
              {/if}

              <button
                type="button"
                class="btn-secondary"
                onclick={handleAddPattern}
                disabled={saving || (direction !== "transfer" && effectiveContainerIds.length === 0)}
                title={direction !== "transfer" && effectiveContainerIds.length === 0 ? $_("budgetPosts.selectContainersFirst") : undefined}
              >
                {$_("budgetPosts.addPattern")}
              </button>
              {#if direction !== "transfer" && effectiveContainerIds.length === 0}
                <p class="form-hint" style="margin-top: var(--spacing-xs)">{$_("budgetPosts.selectContainersFirst")}</p>
              {/if}
            </div>

            {#if error}
              <div class="error-message">
                {error}
              </div>
            {/if}
          {:else}
            {#if patternEditorDisabled}
              <div class="warning-message">{$_("budgetPosts.selectContainersFirst")}</div>
            {/if}
            <fieldset class="pattern-fields" disabled={patternEditorDisabled} class:disabled={patternEditorDisabled}>
            <!-- 1. Amount -->
            <div class="form-group">
              <label for="pattern-amount">
                {$_("budgetPosts.patternAmount")} (kr)
                <span class="required">*</span>
              </label>
              <input
                id="pattern-amount"
                type="number"
                step="0.01"
                min="0"
                bind:value={patternAmount}
                required
                placeholder="0.00"
              />
            </div>

            <!-- 2. Pattern Container selector - subset of budget post's container pool -->
            {#if direction !== "transfer" && effectiveContainerIds.length > 1}
              <div class="form-group">
                <label>{$_("budgetPosts.patternAccounts")}</label>
                <p class="form-hint">{$_("budgetPosts.patternAccountsHint")}</p>

                <div class="account-selector">
                  {#each availablePatternContainers as container (container.id)}
                    <label class="account-checkbox">
                      <input
                        type="checkbox"
                        checked={patternContainerIds.includes(container.id)}
                        onchange={() => togglePatternContainer(container.id)}
                      />
                      <span>{getContainerDisplayName(container)}</span>
                    </label>
                  {/each}
                </div>
              </div>
            {/if}

            <!-- 3. Pattern basis toggle -->
            <div class="form-group">
              <label>{$_("budgetPosts.patternBasis.label")}</label>
              <div class="toggle-selector">
                <button
                  type="button"
                  class="toggle-btn"
                  class:selected={patternBasis === "period"}
                  onclick={() => (patternBasis = "period")}
                >
                  {$_("budgetPosts.patternBasis.period")}
                </button>
                <button
                  type="button"
                  class="toggle-btn"
                  class:selected={patternBasis === "date"}
                  onclick={() => (patternBasis = "date")}
                >
                  {$_("budgetPosts.patternBasis.date")}
                </button>
              </div>
            </div>

            <!-- 4. Repeats toggle -->
            <div class="form-group">
              <label>{$_("budgetPosts.patternRepeats.label")}</label>
              <div class="toggle-selector">
                <button
                  type="button"
                  class="toggle-btn"
                  class:selected={!patternRepeats}
                  onclick={() => (patternRepeats = false)}
                >
                  {$_("budgetPosts.patternRepeats.no")}
                </button>
                <button
                  type="button"
                  class="toggle-btn"
                  class:selected={patternRepeats}
                  onclick={() => (patternRepeats = true)}
                >
                  {$_("budgetPosts.patternRepeats.yes")}
                </button>
              </div>
            </div>

            <!-- 5. Conditional fields based on combination -->
            {#if patternBasis === "period" && !patternRepeats}
              <!-- Period + No repeat (period_once) -->
              <div class="form-row">
                <div class="form-group">
                  <label for="pattern-period-month">
                    {$_("budgetPosts.periodSelect.month")}
                    <span class="required">*</span>
                  </label>
                  <select
                    id="pattern-period-month"
                    bind:value={patternPeriodMonth}
                  >
                    {#each monthLabelsFull as month, index}
                      <option value={index + 1}>{month}</option>
                    {/each}
                  </select>
                </div>
                <div class="form-group">
                  <label for="pattern-period-year">
                    {$_("budgetPosts.periodSelect.year")}
                    <span class="required">*</span>
                  </label>
                  <input
                    id="pattern-period-year"
                    type="number"
                    min="2020"
                    max="2099"
                    bind:value={patternPeriodYear}
                  />
                </div>
              </div>
            {:else if patternBasis === "period" && patternRepeats}
              <!-- Period + Repeats (period_monthly or period_yearly) -->
              <div class="form-row">
                <div class="form-group">
                  <label for="pattern-start-month">
                    {$_("budgetPosts.periodSelect.startPeriod")} ({$_(
                      "budgetPosts.periodSelect.month",
                    )})
                    <span class="required">*</span>
                  </label>
                  <select
                    id="pattern-start-month"
                    bind:value={patternPeriodMonth}
                  >
                    {#each monthLabelsFull as month, index}
                      <option value={index + 1}>{month}</option>
                    {/each}
                  </select>
                </div>
                <div class="form-group">
                  <label for="pattern-start-year">
                    {$_("budgetPosts.periodSelect.year")}
                    <span class="required">*</span>
                  </label>
                  <input
                    id="pattern-start-year"
                    type="number"
                    min="2020"
                    max="2099"
                    bind:value={patternPeriodYear}
                  />
                </div>
              </div>

              <div class="form-group">
                <label class="checkbox-label">
                  <input type="checkbox" bind:checked={patternHasEndDate} />
                  <span>{$_("budgetPosts.periodSelect.endPeriod")}</span>
                </label>
                {#if patternHasEndDate}
                  <div class="form-row">
                    <select bind:value={patternEndPeriodMonth}>
                      {#each monthLabelsFull as month, index}
                        <option value={index + 1}>{month}</option>
                      {/each}
                    </select>
                    <input
                      type="number"
                      min="2020"
                      max="2099"
                      bind:value={patternEndPeriodYear}
                    />
                  </div>
                {/if}
              </div>

              <!-- Frequency toggle (monthly vs yearly) -->
              <div class="form-group">
                <label>{$_("budgetPosts.frequency.label")}</label>
                <div class="toggle-selector">
                  <button
                    type="button"
                    class="toggle-btn"
                    class:selected={patternPeriodFrequency === "monthly"}
                    onclick={() => (patternPeriodFrequency = "monthly")}
                  >
                    {$_("budgetPosts.frequency.monthly")}
                  </button>
                  <button
                    type="button"
                    class="toggle-btn"
                    class:selected={patternPeriodFrequency === "yearly"}
                    onclick={() => (patternPeriodFrequency = "yearly")}
                  >
                    {$_("budgetPosts.frequency.yearly")}
                  </button>
                </div>
              </div>

              <!-- Month selector (only for yearly) -->
              {#if patternPeriodFrequency === "yearly"}
                <div class="form-group">
                  <label>{$_("budgetPosts.periodSelect.selectMonths")}</label>
                  <div class="month-selector">
                    {#each monthLabelsShort as month, index}
                      <button
                        type="button"
                        class="month-btn"
                        class:selected={patternRecurrenceMonths.includes(
                          index + 1,
                        )}
                        onclick={() => togglePatternMonth(index + 1)}
                      >
                        {month}
                      </button>
                    {/each}
                  </div>
                </div>
              {/if}

              <!-- Interval (for both monthly and yearly) -->
              <div class="form-group">
                <label for="pattern-period-interval"
                  >{$_("budgetPosts.recurrence.interval")}</label
                >
                <input
                  id="pattern-period-interval"
                  type="number"
                  min="1"
                  bind:value={patternRecurrenceInterval}
                />
              </div>
            {:else if patternBasis === "date" && !patternRepeats}
              <!-- Date + No repeat (once) -->
              <div class="form-group">
                <label for="pattern-once-date">
                  {$_("budgetPosts.recurrence.date")}
                  <span class="required">*</span>
                </label>
                <input
                  id="pattern-once-date"
                  type="date"
                  bind:value={patternStartDate}
                  required
                />
              </div>

              <div class="form-group">
                <label for="pattern-bank-day-adj-once"
                  >{$_("budgetPosts.recurrence.bankDayAdjustment")}</label
                >
                <select
                  id="pattern-bank-day-adj-once"
                  bind:value={patternRecurrenceBankDayAdjustment}
                >
                  <option value="none"
                    >{$_("budgetPosts.recurrence.bankDayNone")}</option
                  >
                  <option value="next"
                    >{$_("budgetPosts.recurrence.bankDayNext")}</option
                  >
                  <option value="previous"
                    >{$_("budgetPosts.recurrence.bankDayPrevious")}</option
                  >
                </select>
              </div>

              {#if patternRecurrenceBankDayAdjustment !== "none"}
                <div class="form-group">
                  <label class="checkbox-label">
                    <input
                      type="checkbox"
                      bind:checked={patternBankDayKeepInMonth}
                    />
                    <span
                      >{$_("budgetPosts.recurrence.bankDayKeepInMonth")}</span
                    >
                  </label>
                  <p class="form-hint">
                    {$_("budgetPosts.recurrence.bankDayKeepInMonthHint")}
                  </p>
                </div>

                <div class="form-group">
                  <label class="checkbox-label">
                    <input
                      type="checkbox"
                      bind:checked={patternBankDayNoDedup}
                    />
                    <span>{$_("budgetPosts.recurrence.bankDayNoDedup")}</span>
                  </label>
                  <p class="form-hint">
                    {$_("budgetPosts.recurrence.bankDayNoDedupHint")}
                  </p>
                </div>
              {/if}
            {:else if patternBasis === "date" && patternRepeats}
              <!-- Date + Repeats -->
              <div class="form-group">
                <label>{$_("budgetPosts.frequency.label")}</label>
                <div class="frequency-selector">
                  <button
                    type="button"
                    class="toggle-btn"
                    class:selected={patternFrequency === "daily"}
                    onclick={() => (patternFrequency = "daily")}
                  >
                    {$_("budgetPosts.frequency.daily")}
                  </button>
                  <button
                    type="button"
                    class="toggle-btn"
                    class:selected={patternFrequency === "weekly"}
                    onclick={() => (patternFrequency = "weekly")}
                  >
                    {$_("budgetPosts.frequency.weekly")}
                  </button>
                  <button
                    type="button"
                    class="toggle-btn"
                    class:selected={patternFrequency === "monthly"}
                    onclick={() => (patternFrequency = "monthly")}
                  >
                    {$_("budgetPosts.frequency.monthly")}
                  </button>
                  <button
                    type="button"
                    class="toggle-btn"
                    class:selected={patternFrequency === "yearly"}
                    onclick={() => (patternFrequency = "yearly")}
                  >
                    {$_("budgetPosts.frequency.yearly")}
                  </button>
                </div>
              </div>

              <!-- Start date -->
              <div class="form-group">
                <label for="pattern-start-date">
                  {$_("budgetPosts.patternStartDate")}
                  <span class="required">*</span>
                </label>
                <input
                  id="pattern-start-date"
                  type="date"
                  bind:value={patternStartDate}
                  required
                />
              </div>

              <!-- Optional end date -->
              <div class="form-group">
                <label class="checkbox-label">
                  <input type="checkbox" bind:checked={patternHasEndDate} />
                  <span>{$_("budgetPosts.patternEndDate")}</span>
                </label>
                {#if patternHasEndDate}
                  <input type="date" bind:value={patternEndDate} />
                {/if}
              </div>

              <!-- Frequency-specific fields -->
              {#if patternFrequency === "daily"}
                <div class="form-group">
                  <label for="pattern-recurrence-interval"
                    >{$_("budgetPosts.recurrence.interval")}</label
                  >
                  <input
                    id="pattern-recurrence-interval"
                    type="number"
                    min="1"
                    bind:value={patternRecurrenceInterval}
                  />
                </div>
              {:else if patternFrequency === "weekly"}
                <div class="form-row">
                  <div class="form-group">
                    <label for="pattern-recurrence-weekday"
                      >{$_("budgetPosts.recurrence.weekday")}</label
                    >
                    <select
                      id="pattern-recurrence-weekday"
                      bind:value={patternRecurrenceWeekday}
                    >
                      <option value={0}
                        >{$_("budgetPosts.weekday.monday")}</option
                      >
                      <option value={1}
                        >{$_("budgetPosts.weekday.tuesday")}</option
                      >
                      <option value={2}
                        >{$_("budgetPosts.weekday.wednesday")}</option
                      >
                      <option value={3}
                        >{$_("budgetPosts.weekday.thursday")}</option
                      >
                      <option value={4}
                        >{$_("budgetPosts.weekday.friday")}</option
                      >
                      <option value={5}
                        >{$_("budgetPosts.weekday.saturday")}</option
                      >
                      <option value={6}
                        >{$_("budgetPosts.weekday.sunday")}</option
                      >
                    </select>
                  </div>
                  <div class="form-group">
                    <label for="pattern-recurrence-interval-weekly"
                      >{$_("budgetPosts.recurrence.interval")}</label
                    >
                    <input
                      id="pattern-recurrence-interval-weekly"
                      type="number"
                      min="1"
                      bind:value={patternRecurrenceInterval}
                    />
                  </div>
                </div>
              {:else if patternFrequency === "monthly"}
                <!-- Monthly type toggle -->
                <div class="form-group">
                  <label>{$_("budgetPosts.recurrence.dayType")}</label>
                  <div class="toggle-selector toggle-selector-3">
                    <button
                      type="button"
                      class="toggle-btn"
                      class:selected={patternMonthlyType === "fixed"}
                      onclick={() => (patternMonthlyType = "fixed")}
                    >
                      {$_("budgetPosts.recurrence.fixedDay")}
                    </button>
                    <button
                      type="button"
                      class="toggle-btn"
                      class:selected={patternMonthlyType === "relative"}
                      onclick={() => (patternMonthlyType = "relative")}
                    >
                      {$_("budgetPosts.recurrence.relativeWeekday")}
                    </button>
                    <button
                      type="button"
                      class="toggle-btn"
                      class:selected={patternMonthlyType === "bank_day"}
                      onclick={() => (patternMonthlyType = "bank_day")}
                    >
                      {$_("budgetPosts.recurrence.bankDay")}
                    </button>
                  </div>
                </div>

                {#if patternMonthlyType === "fixed"}
                  <div class="form-row">
                    <div class="form-group">
                      <label for="pattern-recurrence-day-of-month"
                        >{$_("budgetPosts.recurrence.dayOfMonth")}</label
                      >
                      <input
                        id="pattern-recurrence-day-of-month"
                        type="number"
                        min="1"
                        max="31"
                        bind:value={patternRecurrenceDayOfMonth}
                      />
                    </div>
                    <div class="form-group">
                      <label for="pattern-recurrence-interval-monthly"
                        >{$_("budgetPosts.recurrence.interval")}</label
                      >
                      <input
                        id="pattern-recurrence-interval-monthly"
                        type="number"
                        min="1"
                        bind:value={patternRecurrenceInterval}
                      />
                    </div>
                  </div>
                {:else if patternMonthlyType === "relative"}
                  <div class="form-row">
                    <div class="form-group">
                      <label for="pattern-recurrence-relative-position"
                        >{$_("budgetPosts.recurrence.relativePosition")}</label
                      >
                      <select
                        id="pattern-recurrence-relative-position"
                        bind:value={patternRecurrenceRelativePosition}
                      >
                        <option value="first"
                          >{$_("budgetPosts.relativePosition.first")}</option
                        >
                        <option value="second"
                          >{$_("budgetPosts.relativePosition.second")}</option
                        >
                        <option value="third"
                          >{$_("budgetPosts.relativePosition.third")}</option
                        >
                        <option value="fourth"
                          >{$_("budgetPosts.relativePosition.fourth")}</option
                        >
                        <option value="last"
                          >{$_("budgetPosts.relativePosition.last")}</option
                        >
                      </select>
                    </div>
                    <div class="form-group">
                      <label for="pattern-recurrence-weekday-relative"
                        >{$_("budgetPosts.recurrence.weekday")}</label
                      >
                      <select
                        id="pattern-recurrence-weekday-relative"
                        bind:value={patternRecurrenceWeekday}
                      >
                        <option value={0}
                          >{$_("budgetPosts.weekday.monday")}</option
                        >
                        <option value={1}
                          >{$_("budgetPosts.weekday.tuesday")}</option
                        >
                        <option value={2}
                          >{$_("budgetPosts.weekday.wednesday")}</option
                        >
                        <option value={3}
                          >{$_("budgetPosts.weekday.thursday")}</option
                        >
                        <option value={4}
                          >{$_("budgetPosts.weekday.friday")}</option
                        >
                        <option value={5}
                          >{$_("budgetPosts.weekday.saturday")}</option
                        >
                        <option value={6}
                          >{$_("budgetPosts.weekday.sunday")}</option
                        >
                      </select>
                    </div>
                  </div>
                  <div class="form-group">
                    <label for="pattern-recurrence-interval-monthly-rel"
                      >{$_("budgetPosts.recurrence.interval")}</label
                    >
                    <input
                      id="pattern-recurrence-interval-monthly-rel"
                      type="number"
                      min="1"
                      bind:value={patternRecurrenceInterval}
                    />
                  </div>
                {:else if patternMonthlyType === "bank_day"}
                  <div class="form-row">
                    <div class="form-group">
                      <label for="pattern-bank-day-number"
                        >{$_("budgetPosts.recurrence.bankDayNumber")}</label
                      >
                      <input
                        id="pattern-bank-day-number"
                        type="number"
                        min="1"
                        max="10"
                        bind:value={patternBankDayNumber}
                      />
                    </div>
                    <div class="form-group">
                      <label for="pattern-bank-day-from-end"
                        >{$_("budgetPosts.recurrence.bankDayFromEnd")}</label
                      >
                      <select
                        id="pattern-bank-day-from-end"
                        bind:value={patternBankDayFromEnd}
                      >
                        <option value="start"
                          >{$_(
                            "budgetPosts.recurrence.bankDayFromStart",
                          )}</option
                        >
                        <option value="end"
                          >{$_(
                            "budgetPosts.recurrence.bankDayFromEndOption",
                          )}</option
                        >
                      </select>
                    </div>
                  </div>
                  <div class="form-group">
                    <label for="pattern-recurrence-interval-monthly-bd"
                      >{$_("budgetPosts.recurrence.interval")}</label
                    >
                    <input
                      id="pattern-recurrence-interval-monthly-bd"
                      type="number"
                      min="1"
                      bind:value={patternRecurrenceInterval}
                    />
                  </div>
                {/if}
              {:else if patternFrequency === "yearly"}
                <div class="form-group">
                  <label for="pattern-recurrence-month"
                    >{$_("budgetPosts.recurrence.month")}</label
                  >
                  <select
                    id="pattern-recurrence-month"
                    bind:value={patternRecurrenceMonth}
                  >
                    {#each monthLabelsFull as monthLabel, index}
                      <option value={index + 1}>{monthLabel}</option>
                    {/each}
                  </select>
                </div>

                <div class="form-group">
                  <label>{$_("budgetPosts.recurrence.dayType")}</label>
                  <div class="toggle-selector toggle-selector-3">
                    <button
                      type="button"
                      class="toggle-btn"
                      class:selected={patternYearlyType === "fixed"}
                      onclick={() => (patternYearlyType = "fixed")}
                    >
                      {$_("budgetPosts.recurrence.fixedDay")}
                    </button>
                    <button
                      type="button"
                      class="toggle-btn"
                      class:selected={patternYearlyType === "relative"}
                      onclick={() => (patternYearlyType = "relative")}
                    >
                      {$_("budgetPosts.recurrence.relativeWeekday")}
                    </button>
                    <button
                      type="button"
                      class="toggle-btn"
                      class:selected={patternYearlyType === "bank_day"}
                      onclick={() => (patternYearlyType = "bank_day")}
                    >
                      {$_("budgetPosts.recurrence.bankDay")}
                    </button>
                  </div>
                </div>

                {#if patternYearlyType === "relative"}
                  <div class="form-row">
                    <div class="form-group">
                      <label for="pattern-recurrence-yearly-relative-position"
                        >{$_("budgetPosts.recurrence.relativePosition")}</label
                      >
                      <select
                        id="pattern-recurrence-yearly-relative-position"
                        bind:value={patternRecurrenceRelativePosition}
                      >
                        <option value="first"
                          >{$_("budgetPosts.relativePosition.first")}</option
                        >
                        <option value="second"
                          >{$_("budgetPosts.relativePosition.second")}</option
                        >
                        <option value="third"
                          >{$_("budgetPosts.relativePosition.third")}</option
                        >
                        <option value="fourth"
                          >{$_("budgetPosts.relativePosition.fourth")}</option
                        >
                        <option value="last"
                          >{$_("budgetPosts.relativePosition.last")}</option
                        >
                      </select>
                    </div>
                    <div class="form-group">
                      <label for="pattern-recurrence-yearly-weekday"
                        >{$_("budgetPosts.recurrence.weekday")}</label
                      >
                      <select
                        id="pattern-recurrence-yearly-weekday"
                        bind:value={patternRecurrenceWeekday}
                      >
                        <option value={0}
                          >{$_("budgetPosts.weekday.monday")}</option
                        >
                        <option value={1}
                          >{$_("budgetPosts.weekday.tuesday")}</option
                        >
                        <option value={2}
                          >{$_("budgetPosts.weekday.wednesday")}</option
                        >
                        <option value={3}
                          >{$_("budgetPosts.weekday.thursday")}</option
                        >
                        <option value={4}
                          >{$_("budgetPosts.weekday.friday")}</option
                        >
                        <option value={5}
                          >{$_("budgetPosts.weekday.saturday")}</option
                        >
                        <option value={6}
                          >{$_("budgetPosts.weekday.sunday")}</option
                        >
                      </select>
                    </div>
                  </div>
                {:else if patternYearlyType === "fixed"}
                  <div class="form-group">
                    <label for="pattern-recurrence-day-yearly"
                      >{$_("budgetPosts.recurrence.dayOfMonth")}</label
                    >
                    <input
                      id="pattern-recurrence-day-yearly"
                      type="number"
                      min="1"
                      max="31"
                      bind:value={patternRecurrenceDayOfMonth}
                    />
                  </div>
                {:else if patternYearlyType === "bank_day"}
                  <div class="form-row">
                    <div class="form-group">
                      <label for="pattern-bank-day-number-yearly"
                        >{$_("budgetPosts.recurrence.bankDayNumber")}</label
                      >
                      <input
                        id="pattern-bank-day-number-yearly"
                        type="number"
                        min="1"
                        max="10"
                        bind:value={patternBankDayNumber}
                      />
                    </div>
                    <div class="form-group">
                      <label for="pattern-bank-day-from-end-yearly"
                        >{$_("budgetPosts.recurrence.bankDayFromEnd")}</label
                      >
                      <select
                        id="pattern-bank-day-from-end-yearly"
                        bind:value={patternBankDayFromEnd}
                      >
                        <option value="start"
                          >{$_(
                            "budgetPosts.recurrence.bankDayFromStart",
                          )}</option
                        >
                        <option value="end"
                          >{$_(
                            "budgetPosts.recurrence.bankDayFromEndOption",
                          )}</option
                        >
                      </select>
                    </div>
                  </div>
                {/if}

                <div class="form-group">
                  <label for="pattern-recurrence-interval-yearly"
                    >{$_("budgetPosts.recurrence.interval")}</label
                  >
                  <input
                    id="pattern-recurrence-interval-yearly"
                    type="number"
                    min="1"
                    bind:value={patternRecurrenceInterval}
                  />
                </div>
              {/if}

              <!-- Bank day adjustment selector (hidden for bank day types) -->
              {#if patternRecurrenceType !== "monthly_bank_day" && patternRecurrenceType !== "yearly_bank_day"}
                <div class="form-group">
                  <label for="pattern-bank-day-adj"
                    >{$_("budgetPosts.recurrence.bankDayAdjustment")}</label
                  >
                  <select
                    id="pattern-bank-day-adj"
                    bind:value={patternRecurrenceBankDayAdjustment}
                  >
                    <option value="none"
                      >{$_("budgetPosts.recurrence.bankDayNone")}</option
                    >
                    <option value="next"
                      >{$_("budgetPosts.recurrence.bankDayNext")}</option
                    >
                    <option value="previous"
                      >{$_("budgetPosts.recurrence.bankDayPrevious")}</option
                    >
                  </select>
                </div>

                {#if patternRecurrenceBankDayAdjustment !== "none"}
                  <div class="form-group">
                    <label class="checkbox-label">
                      <input
                        type="checkbox"
                        bind:checked={patternBankDayKeepInMonth}
                      />
                      <span
                        >{$_("budgetPosts.recurrence.bankDayKeepInMonth")}</span
                      >
                    </label>
                    <p class="form-hint">
                      {$_("budgetPosts.recurrence.bankDayKeepInMonthHint")}
                    </p>
                  </div>

                  <div class="form-group">
                    <label class="checkbox-label">
                      <input
                        type="checkbox"
                        bind:checked={patternBankDayNoDedup}
                      />
                      <span>{$_("budgetPosts.recurrence.bankDayNoDedup")}</span>
                    </label>
                    <p class="form-hint">
                      {$_("budgetPosts.recurrence.bankDayNoDedupHint")}
                    </p>
                  </div>
                {/if}
              {/if}
            {/if}

            </fieldset>

            <div class="pattern-form-actions">
              <button
                type="button"
                class="btn-secondary"
                onclick={handleCancelPattern}
              >
                {$_("common.cancel")}
              </button>
              <button
                type="button"
                class="btn-primary"
                onclick={handleSavePattern}
                disabled={patternEditorDisabled}
              >
                {$_("common.save")}
              </button>
            </div>

            {#if error}
              <div class="error-message">
                {error}
              </div>
            {/if}
          {/if}
        </div>

        {#if activeView === "main"}
          <div class="modal-footer">
            <button
              type="button"
              class="btn-secondary"
              onclick={handleClose}
              disabled={saving}
            >
              {$_("common.cancel")}
            </button>
            <button type="submit" class="btn-primary" disabled={saving}>
              {saving ? $_("common.loading") : $_("common.save")}
            </button>
          </div>
        {/if}
      </form>

      {#if showCascadeConfirmation}
        <div class="cascade-overlay">
          <div class="cascade-dialog">
            <h3>{$_('budgetPosts.inheritance.cascadeTitle')}</h3>
            <p>{$_('budgetPosts.inheritance.cascadeMessage', { values: { count: descendantPosts.length } })}</p>
            <ul class="cascade-affected-list">
              {#each descendantPosts as post}
                <li>{post.category_path?.join(' > ')}</li>
              {/each}
            </ul>
            <p class="cascade-detail">{$_('budgetPosts.inheritance.cascadeDetail')}</p>
            <div class="cascade-actions">
              <button class="btn-secondary" onclick={() => showCascadeConfirmation = false} type="button">
                {$_('budgetPosts.inheritance.cascadeCancel')}
              </button>
              <button class="btn-primary" onclick={performSave} type="button">
                {$_('budgetPosts.inheritance.cascadeConfirm')}
              </button>
            </div>
          </div>
        </div>
      {/if}
    </div>
  </div>
{/if}

<style>
  .modal-backdrop {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
    padding: var(--spacing-md);
  }

  .modal {
    position: relative;
    background: var(--bg-card);
    border-radius: var(--radius-lg);
    max-width: 700px;
    width: 100%;
    max-height: 90vh;
    overflow-y: auto;
    box-shadow:
      0 20px 25px -5px rgba(0, 0, 0, 0.1),
      0 10px 10px -5px rgba(0, 0, 0, 0.04);
  }

  .modal-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: var(--spacing-lg) var(--spacing-xl);
    border-bottom: 1px solid var(--border);
  }

  .modal-header h2 {
    font-size: var(--font-size-xl);
    font-weight: 600;
    color: var(--text-primary);
    margin: 0;
  }

  .close-button {
    background: none;
    border: none;
    color: var(--text-secondary);
    cursor: pointer;
    padding: var(--spacing-xs);
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: var(--radius-md);
    transition: all 0.2s;
  }

  .close-button:hover {
    background: var(--bg-page);
    color: var(--text-primary);
  }

  .modal-body {
    padding: var(--spacing-xl);
    display: flex;
    flex-direction: column;
    gap: var(--spacing-lg);
  }

  .form-group {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-xs);
  }

  .form-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: var(--spacing-md);
  }

  .form-section {
    border-top: 1px solid var(--border);
    padding-top: var(--spacing-lg);
    margin-top: var(--spacing-sm);
  }

  .form-section h3 {
    font-size: var(--font-size-lg);
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: var(--spacing-md);
  }

  label {
    font-size: var(--font-size-base);
    font-weight: 500;
    color: var(--text-primary);
    max-width: fit-content;
  }

  .required {
    color: var(--negative);
  }

  .form-hint {
    font-size: var(--font-size-sm);
    color: var(--text-secondary);
    font-style: italic;
  }

  .checkbox-label {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    cursor: pointer;
    font-weight: normal;
  }

  .checkbox-label input[type="checkbox"] {
    cursor: pointer;
  }

  .direction-selector {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: var(--spacing-xs);
  }

  .direction-btn {
    padding: var(--spacing-sm) var(--spacing-md);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    background: var(--bg-page);
    color: var(--text-secondary);
    font-size: var(--font-size-base);
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;
  }

  .direction-btn:hover:not(:disabled) {
    border-color: var(--accent);
    color: var(--accent);
  }

  .direction-btn.selected {
    background: var(--accent);
    color: white;
    border-color: var(--accent);
  }

  .direction-btn:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .toggle-selector {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: var(--spacing-xs);
  }

  .toggle-selector-3 {
    grid-template-columns: repeat(3, 1fr);
  }

  .toggle-btn {
    padding: var(--spacing-sm) var(--spacing-md);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    background: var(--bg-card);
    color: var(--text-secondary);
    cursor: pointer;
    font-size: 0.9rem;
    text-align: center;
    transition: all 0.2s;
  }

  .toggle-btn:hover {
    border-color: var(--accent);
    color: var(--accent);
  }

  .toggle-btn.selected {
    background: var(--accent);
    color: white;
    border-color: var(--accent);
  }

  .frequency-selector {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: var(--spacing-xs);
  }

  input[type="text"],
  input[type="number"],
  input[type="date"],
  select {
    padding: var(--spacing-sm) var(--spacing-md);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    font-size: var(--font-size-base);
    color: var(--text-primary);
    background: var(--bg-page);
    transition: border-color 0.2s;
  }

  input[type="text"]:focus,
  input[type="number"]:focus,
  input[type="date"]:focus,
  select:focus {
    outline: none;
    border-color: var(--accent);
  }

  input[type="text"]:disabled,
  input[type="number"]:disabled,
  input[type="date"]:disabled,
  select:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .month-selector {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: var(--spacing-xs);
  }

  .month-btn {
    padding: var(--spacing-sm);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    background: var(--bg-page);
    color: var(--text-secondary);
    font-size: var(--font-size-sm);
    cursor: pointer;
    transition: all 0.2s;
  }

  .month-btn:hover:not(:disabled) {
    border-color: var(--accent);
    color: var(--accent);
  }

  .month-btn.selected {
    background: var(--accent);
    color: white;
    border-color: var(--accent);
  }

  .month-btn:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .account-selector {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-xs);
    max-height: 200px;
    overflow-y: auto;
    padding: var(--spacing-xs);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    background: var(--bg-page);
  }

  .account-checkbox {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    padding: var(--spacing-xs) var(--spacing-sm);
    cursor: pointer;
    font-weight: normal;
    border-radius: var(--radius-sm);
    transition: background 0.2s;
  }

  .account-checkbox:hover {
    background: rgba(0, 0, 0, 0.05);
  }

  .account-checkbox input[type="checkbox"] {
    cursor: pointer;
  }

  .info-message {
    padding: var(--spacing-sm) var(--spacing-md);
    background: rgba(59, 130, 246, 0.1);
    border: 1px solid var(--accent);
    border-radius: var(--radius-md);
    color: var(--text-secondary);
    font-size: var(--font-size-sm);
    text-align: center;
    margin-bottom: var(--spacing-md);
  }

  .error-message {
    padding: var(--spacing-sm) var(--spacing-md);
    background: rgba(239, 68, 68, 0.1);
    border: 1px solid var(--negative);
    border-radius: var(--radius-md);
    color: var(--negative);
    font-size: var(--font-size-sm);
  }

  .warning-message {
    background-color: var(--bg-warning, #fff3cd);
    color: var(--text-warning, #856404);
    padding: 0.75rem 1rem;
    border-radius: var(--radius-sm, 6px);
    margin-bottom: 1rem;
    font-size: 0.9rem;
  }

  fieldset.pattern-fields {
    display: contents;
  }

  fieldset.pattern-fields.disabled > :global(*) {
    opacity: 0.5;
    pointer-events: none;
  }

  .modal-footer {
    display: flex;
    gap: var(--spacing-md);
    justify-content: flex-end;
    padding: var(--spacing-lg) var(--spacing-xl);
    border-top: 1px solid var(--border);
  }

  .btn-primary,
  .btn-secondary {
    padding: var(--spacing-sm) var(--spacing-lg);
    border-radius: var(--radius-md);
    font-size: var(--font-size-base);
    font-weight: 500;
    cursor: pointer;
    transition: opacity 0.2s;
    border: none;
  }

  .btn-primary {
    background: var(--accent);
    color: white;
  }

  .btn-secondary {
    background: transparent;
    color: var(--accent);
    border: 1px solid var(--accent);
  }

  .btn-primary:disabled,
  .btn-secondary:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .btn-primary:hover:not(:disabled),
  .btn-secondary:hover:not(:disabled) {
    opacity: 0.9;
  }

  .patterns-list {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-sm);
    margin-bottom: var(--spacing-md);
  }

  .pattern-card {
    position: relative;
    background: var(--bg-page);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    padding: var(--spacing-md);
    padding-left: calc(var(--spacing-md) + 8px);
    display: flex;
    align-items: center;
    gap: var(--spacing-md);
    transition: border-color 0.2s;
    cursor: pointer;
  }

  .pattern-card::before {
    content: "";
    position: absolute;
    left: 6px;
    top: 6px;
    bottom: 6px;
    width: 3px;
    border-radius: 2px;
    background: var(--pattern-color, transparent);
  }

  .pattern-card:hover {
    border-color: var(--accent);
  }

  .pattern-info {
    flex: 1;
    min-width: 0;
  }

  .pattern-amount-display {
    font-size: var(--font-size-lg);
    font-weight: 700;
    color: var(--text-primary);
    margin-bottom: var(--spacing-xs);
  }

  .pattern-meta {
    font-size: var(--font-size-sm);
    color: var(--text-secondary);
    display: flex;
    align-items: center;
    gap: var(--spacing-xs);
    margin-bottom: var(--spacing-xs);
  }

  .pattern-recurrence-display {
    font-size: var(--font-size-sm);
    color: var(--text-secondary);
  }

  .pattern-accounts-display {
    font-size: var(--font-size-sm);
    color: var(--text-secondary);
    margin-top: var(--spacing-xs);
  }

  .pattern-accounts-missing {
    color: var(--warning);
    font-style: italic;
  }

  .pattern-auto-adjusted {
    font-size: var(--font-size-xs);
    color: var(--text-secondary);
    font-style: italic;
  }

  .pattern-actions {
    display: flex;
    gap: var(--spacing-xs);
    flex-shrink: 0;
  }

  .pattern-form-actions {
    display: flex;
    gap: var(--spacing-md);
    justify-content: flex-end;
    margin-top: var(--spacing-sm);
  }

  @media (max-width: 768px) {
    .modal {
      max-width: 100%;
      max-height: 100vh;
      border-radius: 0;
    }

    .modal-body {
      padding: var(--spacing-lg);
    }

    .form-row {
      grid-template-columns: 1fr;
    }

    .direction-selector {
      grid-template-columns: 1fr;
    }

    .month-selector {
      grid-template-columns: repeat(3, 1fr);
    }

    .frequency-selector {
      grid-template-columns: repeat(2, 1fr);
    }

    .modal-footer {
      flex-direction: column-reverse;
      padding: var(--spacing-lg);
    }

    .btn-primary,
    .btn-secondary {
      width: 100%;
    }

    .pattern-card {
      flex-direction: column;
      align-items: flex-start;
      padding-left: calc(var(--spacing-md) + 8px);
    }

    .pattern-actions {
      align-self: flex-end;
    }

    .pattern-form-actions {
      flex-direction: column-reverse;
    }

    .pattern-form-actions button {
      width: 100%;
    }
  }

  .btn-icon {
    width: 32px;
    height: 32px;
    padding: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    background: none;
    border: 1px solid var(--border-default);
    border-radius: 4px;
    color: var(--text-secondary);
    cursor: pointer;
    transition: all 0.15s ease;
  }

  .btn-icon:hover {
    background: var(--bg-surface);
    border-color: var(--border-active);
    color: var(--text-primary);
  }

  .btn-icon.btn-danger:hover {
    background: rgba(207, 102, 121, 0.1);
    border-color: var(--negative);
    color: var(--negative);
  }

  .category-breadcrumb-wrapper {
    position: relative;
  }

  .breadcrumb-input-area {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: var(--spacing-xs);
    padding: var(--spacing-xs) var(--spacing-sm);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    background: var(--bg-card);
    min-height: 42px;
    cursor: text;
  }

  .breadcrumb-input-area:focus-within {
    border-color: var(--accent);
    box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.15);
  }

  .breadcrumb-chip {
    display: inline-flex;
    align-items: center;
    gap: var(--spacing-xs);
    padding: 4px 28px 4px 10px;
    background: var(--accent);
    color: white;
    font-size: var(--font-size-sm);
    border-radius: var(--radius-sm);
    position: relative;
    white-space: nowrap;
  }

  .breadcrumb-chip.has-next {
    margin-right: 8px;
    border-top-right-radius: 0;
    border-bottom-right-radius: 0;
  }

  .breadcrumb-chip.has-next::after {
    content: "";
    position: absolute;
    right: -8px;
    top: 0;
    bottom: 0;
    width: 8px;
    background: var(--accent);
    clip-path: polygon(0 0, 100% 50%, 0 100%);
  }

  .chip-text {
    max-width: 150px;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .chip-remove {
    position: absolute;
    right: 4px;
    top: 50%;
    transform: translateY(-50%);
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0;
    background: none;
    border: none;
    color: rgba(255, 255, 255, 0.7);
    cursor: pointer;
    line-height: 1;
  }

  .chip-remove:hover {
    color: white;
  }

  .chip-remove:disabled {
    cursor: not-allowed;
    opacity: 0.5;
  }

  .breadcrumb-input-area input {
    flex: 1;
    min-width: 120px;
    border: none;
    background: none;
    padding: 4px;
    font-size: var(--font-size-base);
    color: var(--text-primary);
    outline: none;
  }

  .breadcrumb-input-area input::placeholder {
    color: var(--text-secondary);
  }

  .autocomplete-dropdown {
    position: absolute;
    top: 100%;
    left: 0;
    right: 0;
    z-index: 10;
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    max-height: 200px;
    overflow-y: auto;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    margin-top: var(--spacing-xs);
  }

  .autocomplete-option {
    width: 100%;
    padding: var(--spacing-sm) var(--spacing-md);
    background: none;
    border: none;
    text-align: left;
    color: var(--text-primary);
    font-size: var(--font-size-base);
    cursor: pointer;
    transition: background 0.15s;
  }

  .autocomplete-option:hover,
  .autocomplete-option.highlighted {
    background: var(--bg-page);
  }

  /* Ancestor constraint indicator */
  .ancestor-info {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    padding: var(--spacing-sm) var(--spacing-md);
    background: var(--bg-page);
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    margin-bottom: var(--spacing-md);
    color: var(--text-secondary);
    font-size: var(--font-size-sm);
  }

  .ancestor-info svg {
    flex-shrink: 0;
    color: var(--accent);
  }

  /* Cascade confirmation dialog */
  .cascade-overlay {
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.7);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 10;
    padding: var(--spacing-xl);
  }

  .cascade-dialog {
    background: var(--bg-card);
    border-radius: var(--radius-lg);
    padding: var(--spacing-xl);
    max-width: 500px;
    width: 100%;
    box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
  }

  .cascade-dialog h3 {
    margin: 0 0 var(--spacing-md) 0;
    font-size: var(--font-size-lg);
    color: var(--text-primary);
  }

  .cascade-dialog p {
    margin: 0 0 var(--spacing-md) 0;
    color: var(--text-secondary);
    line-height: 1.5;
  }

  .cascade-affected-list {
    margin: var(--spacing-md) 0;
    padding-left: var(--spacing-xl);
    max-height: 200px;
    overflow-y: auto;
    background: var(--bg-page);
    border-radius: var(--radius-md);
    padding: var(--spacing-md);
  }

  .cascade-affected-list li {
    color: var(--text-primary);
    padding: var(--spacing-xs) 0;
  }

  .cascade-detail {
    font-size: var(--font-size-sm);
    font-style: italic;
  }

  .cascade-actions {
    display: flex;
    gap: var(--spacing-md);
    justify-content: flex-end;
    margin-top: var(--spacing-lg);
  }
</style>
