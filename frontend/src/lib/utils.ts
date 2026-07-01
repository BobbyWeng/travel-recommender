export function formatPrice(price: number, currency = "USD"): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  }).format(price);
}

export function formatDate(dateStr: string): string {
  const d = new Date(dateStr + "T00:00:00");
  return d.toLocaleDateString("zh-CN", {
    month: "short",
    day: "numeric",
  });
}

export function scoreColor(score: number): string {
  if (score >= 80) return "text-emerald-600";
  if (score >= 60) return "text-amber-600";
  return "text-red-600";
}

export function scoreBg(score: number): string {
  if (score >= 80) return "bg-emerald-50 border-emerald-200";
  if (score >= 60) return "bg-amber-50 border-amber-200";
  return "bg-red-50 border-red-200";
}

export function costLevelLabel(level: number): string {
  const labels: Record<number, string> = {
    1: "$",
    2: "$$",
    3: "$$$",
    4: "$$$$",
    5: "$$$$$",
  };
  return labels[level] || "$$$";
}

export function costLevelColor(level: number): string {
  if (level <= 2) return "text-emerald-600";
  if (level <= 3) return "text-amber-600";
  return "text-red-600";
}
