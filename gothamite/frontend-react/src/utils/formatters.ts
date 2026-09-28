export type ScoreBand = 'weak' | 'moderate' | 'strong' | 'very-strong';

export interface ScoreBandInfo {
  band: ScoreBand;
  label: string;
  colorClass: string;
  bgClass: string;
  borderClass: string;
}

/**
 * Returns score band thresholds matching DATA_MODEL.md §3 exactly:
 * - weak: < 0.30
 * - moderate: 0.30 - 0.59
 * - strong: 0.60 - 0.79
 * - very strong: >= 0.80
 */
export function getScoreBand(score: number): ScoreBandInfo {
  if (score >= 0.8) {
    return {
      band: 'very-strong',
      label: 'Very Strong',
      colorClass: 'text-emerald-400',
      bgClass: 'bg-emerald-950/40',
      borderClass: 'border-emerald-800/60',
    };
  }
  if (score >= 0.6) {
    return {
      band: 'strong',
      label: 'Strong',
      colorClass: 'text-blue-400',
      bgClass: 'bg-blue-950/40',
      borderClass: 'border-blue-800/60',
    };
  }
  if (score >= 0.3) {
    return {
      band: 'moderate',
      label: 'Moderate',
      colorClass: 'text-amber-400',
      bgClass: 'bg-amber-950/40',
      borderClass: 'border-amber-800/60',
    };
  }
  return {
    band: 'weak',
    label: 'Weak',
    colorClass: 'text-gray-400',
    bgClass: 'bg-gray-900/60',
    borderClass: 'border-gray-700/60',
  };
}

export function getSourceColor(source: string): {
  dot: string;
  text: string;
  bg: string;
  border: string;
} {
  switch (source.toLowerCase()) {
    case 'forum-alpha':
      return {
        dot: 'bg-[#9eb9c9]',
        text: 'text-[#9eb9c9]',
        bg: 'bg-[#9eb9c9]/10',
        border: 'border-[#9eb9c9]/30',
      };
    case 'marketplace-beta':
      return {
        dot: 'bg-[#c9ad86]',
        text: 'text-[#c9ad86]',
        bg: 'bg-[#c9ad86]/10',
        border: 'border-[#c9ad86]/30',
      };
    case 'forum-gamma':
      return {
        dot: 'bg-[#add0c1]',
        text: 'text-[#add0c1]',
        bg: 'bg-[#add0c1]/10',
        border: 'border-[#add0c1]/30',
      };
    default:
      return {
        dot: 'bg-gray-400',
        text: 'text-gray-400',
        bg: 'bg-gray-800/40',
        border: 'border-gray-700/50',
      };
  }
}

/**
 * Truncates middle of strings (useful for PGP fingerprints and Crypto Wallets):
 * e.g., 9F2A4C81D3E5B7069A1C4F82D6E30B57A4C19E8D -> 9F2A4C81...A4C19E8D
 */
export function formatMiddleTruncate(str: string, maxLen = 20): string {
  if (!str || str.length <= maxLen) return str;
  const keep = Math.floor((maxLen - 3) / 2);
  return `${str.slice(0, keep)}...${str.slice(-keep)}`;
}
