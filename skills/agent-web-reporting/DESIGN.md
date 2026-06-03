---
version: beta
name: Genesis
source: https://designmd.ai/chef/genesis
description: Amit-friendly Genesis-inspired blue/indigo static HTML report style for local agent-web reports.
colors:
  primary: "#6366F1"
  primary-hover: "#4F46E5"
  primary-strong: "#1D4ED8"
  navy: "#111827"
  background: "#FAFAFA"
  surface: "#FFFFFF"
  surface-muted: "#F8FAFC"
  text: "#0A0A0A"
  text-muted: "#6B6B6B"
  border: "#E8E8EC"
  success: "#10B981"
  warning: "#F59E0B"
  danger: "#EF4444"
  code-bg: "#EEF2FF"
typography:
  heading:
    fontFamily: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif
    fontSize: 28px
    fontWeight: 700
    lineHeight: 1.2
  section-heading:
    fontFamily: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif
    fontSize: 20px
    fontWeight: 700
    lineHeight: 1.3
  body:
    fontFamily: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif
    fontSize: 15px
    fontWeight: 400
    lineHeight: 1.45
  mono:
    fontFamily: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace
    fontSize: 13px
    lineHeight: 1.45
rounded:
  sm: 4px
  md: 6px
  card: 12px
spacing:
  xs: 4px
  sm: 8px
  sm2: 12px
  md: 16px
  md2: 20px
  lg: 24px
  xl: 32px
components:
  page:
    backgroundColor: "{colors.background}"
    textColor: "{colors.text}"
  header:
    backgroundColor: "{colors.navy}"
    textColor: "#FFFFFF"
  section:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text}"
    rounded: "{rounded.card}"
  table-header:
    backgroundColor: "{colors.surface-muted}"
    textColor: "{colors.text-muted}"
  border:
    backgroundColor: "{colors.border}"
  link:
    textColor: "{colors.primary}"
  link-hover:
    textColor: "{colors.primary-hover}"
  status-success:
    textColor: "{colors.success}"
  status-warning:
    textColor: "{colors.warning}"
  status-danger:
    textColor: "{colors.danger}"
  code:
    backgroundColor: "{colors.code-bg}"
    textColor: "{colors.text}"
    rounded: "{rounded.sm}"
---

## Overview

Genesis is a quiet, work-focused, blue/indigo design for local operational
reports. It is based on the public Genesis design system and adapted for Amit's
static agent-web reports.

The local adaptation is intentionally more blue than the source system:
indigo is used for primary accents, focus rings, section rails, links, and
selected status metadata. Navy is reserved for page headers and high-level
navigation.

## Colors

Use indigo/blue for report identity, links, active states, focus rings, and
small accent bars. Keep the page mostly white and light gray so the content
stays readable. Use green, amber, and red only for explicit status.

## Typography

Use system fonts only in local reports, even though the public Genesis system
uses General Sans and DM Sans. Do not load external font or icon CDNs. Headings
are strong but not oversized; report pages are tools, not landing pages.

## Layout

Use a constrained main width of about 1100-1200px. Split content into simple
sections with 12px radius and 1px borders. Prefer tables for comparisons,
short lists for decisions, and code blocks for exact commands. Follow a 4px
spacing grid for padding, margins, and gaps.

## Components

- Header: navy band with report title, one-sentence purpose, and blue metadata
  chips.
- Summary metrics: small bordered panels in a responsive grid.
- Sections: white panels with concise headings and optional blue left accent.
- Status pills: green for done/pass, amber for pending/caution, red for blocked.
- Commands and paths: monospace, wrapped in code blocks when multi-line.

## Do's and Don'ts

Do:

- Put the decision or current status in the first section.
- Include exact URLs, source paths, result paths, and next action.
- Use the preserved URL contract: `http://192.168.0.9/<lane>/<file>.html`.
- Keep reports static, self-contained, and readable in desktop Chrome.
- Use indigo for interactive or identity elements, not long body text.
- Keep primary actions visually rare; one primary element per section is enough.

Don't:

- Publish raw logs, whole repos, raw JSON dumps, secrets, `.env`, `.ssh`, keys,
  wallets, or private config.
- Use external assets, JavaScript, decorative gradients, or marketing hero
  layouts.
- Use pure black for large UI surfaces or make the page one-note dark blue.
- Add shadows to static sections; borders are enough for normal reports.
- Mention ignored local `.env` files in routine status unless the report is a
  secret-safety audit or `.env` is tracked/staged.
