const MAX_MINOR_UNITS = 9_000_000_000_000n;

export function formatMoney(minorUnits: number, currency: string, minorUnitDigits: number): string {
  const value = minorUnits / 10 ** minorUnitDigits;
  if (currency === "BDT") {
    const absolute = Math.abs(value).toLocaleString("en-BD", {
      minimumFractionDigits: minorUnitDigits,
      maximumFractionDigits: minorUnitDigits,
    });
    return `${value < 0 ? "−" : ""}৳${absolute}`;
  }
  return new Intl.NumberFormat("en", {
    style: "currency",
    currency,
    minimumFractionDigits: minorUnitDigits,
    maximumFractionDigits: minorUnitDigits,
  }).format(value);
}

export function minorUnitsFromDecimal(value: string, digits: number): number {
  const normalized = value.trim();
  if (!/^\d+(?:\.\d+)?$/.test(normalized)) {
    throw new Error("Enter a non-negative amount using digits and an optional decimal point.");
  }
  const [whole = "0", fraction = ""] = normalized.split(".");
  if (fraction.length > digits) {
    throw new Error(`This currency supports at most ${digits} decimal places.`);
  }
  const units = BigInt(whole) * 10n ** BigInt(digits) + BigInt(fraction.padEnd(digits, "0") || "0");
  if (units > MAX_MINOR_UNITS) throw new Error("The amount exceeds the supported limit.");
  return Number(units);
}

export function decimalFromMinorUnits(value: number | null, digits: number): string {
  if (value === null) return "";
  const divisor = 10 ** digits;
  return (value / divisor).toFixed(digits);
}

export function formatFinancialDate(value: string): string {
  return new Intl.DateTimeFormat("en", {
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  }).format(new Date(`${value}T00:00:00Z`));
}

export function formatTimestamp(value: string): string {
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}
