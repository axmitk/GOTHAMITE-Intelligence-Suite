import type { Entity, Evidence } from "./types";

export const human = (value: string) =>
  value.replaceAll("_", " ").toLowerCase();

// Analyst-facing names for stored entity kinds; keeps "ip" from reading as "Ip".
const kindLabels: Record<string, string> = {
  ip: "IP address",
  url: "URL",
  hash: "File hash",
  threat_actor: "Threat actor",
  darkweb_mention: "Dark-web mention",
  malware: "Malware",
  campaign: "Campaign",
  domain: "Domain",
  email: "Email",
  asset: "Asset",
  organization: "Organization",
  incident: "Incident",
  vulnerability: "Vulnerability",
  forum_thread: "Forum thread",
  market_listing: "Marketplace listing",
  report: "Source report",
  country: "Country",
  tor_relay: "Tor relay",
};
export const kindLabel = (kind: string) =>
  kindLabels[kind] || human(kind).replace(/^./, (c) => c.toUpperCase());

export const plural = (count: number, word: string, many = `${word}s`) =>
  `${count} ${count === 1 ? word : many}`;

const months = [
  "Jan",
  "Feb",
  "Mar",
  "Apr",
  "May",
  "Jun",
  "Jul",
  "Aug",
  "Sep",
  "Oct",
  "Nov",
  "Dec",
];
const pad = (n: number) => String(n).padStart(2, "0");
// Fixed UTC format so every screen and screenshot reads identically ("28 Sep, 08:35 UTC").
export const time = (value: string) => {
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  // The synthetic exercise is a single 2026 day; dataset records span years.
  const year = d.getUTCFullYear() === 2026 ? "" : ` ${d.getUTCFullYear()}`;
  return `${pad(d.getUTCDate())} ${months[d.getUTCMonth()]}${year}, ${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())} UTC`;
};
// Tor Project Onionoo observations carry relay context in their dataset record.
export const isTorExit = (e: Pick<Evidence, "dataset_record">) =>
  e.dataset_record?.details?.observation_type === "tor_exit_node";
export const entityUrl = (entity: Pick<Entity, "kind" | "id">) =>
  entity.kind === "incident"
    ? `/investigations/${entity.id}`
    : `/intelligence/${entity.id}`;
