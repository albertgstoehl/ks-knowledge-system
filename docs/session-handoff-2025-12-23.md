# Session Handoff: Knowledge Flow Redesign

## Context

Brainstorming session about incentivizing note production and creating meaningful learning from consumed content.

## The Problem

- Bookmark inbox grows indefinitely with no pressure to process
- Reading without producing notes = consumption without learning
- Archive was just "things I read" not "things I learned from"

## Key Insight (from cognitive science research)

**Fluency illusion**: Reading something and it "making sense" feels like learning, but it isn't. Real learning requires:
- **Generation** (produce, don't just consume)
- **Elaborative interrogation** ("why is this true?" / "how does this connect?")
- **Desirable difficulty** (struggle = encoding)
- **Transfer-appropriate processing** (encode for how you'll use it)

The gate question: **"How does this change or challenge something I already think?"**

## Design Decision

**Processing = creating a Kasten note that references the source**

No note → content expires → and that's okay.

## New Architecture

```
BOOKMARK MANAGER (ephemeral)          KASTEN (permanent)
┌──────────────────────┐              ┌──────────────────────┐
│       INBOX          │              │       SOURCES        │
│  - capture via bot   │──────────────│  - archived bookmarks│
│  - auto-expire 7d    │  on note     │  - linked to notes   │
│                      │  creation    │                      │
└──────────────────────┘              ├──────────────────────┤
         │                            │        NOTES         │
         ▼                            │  - insights          │
     (deleted)                        │  - source_id (FK)    │
                                      └──────────────────────┘
```

**Canvas role**: Where the cognitive work happens. "Archive & Create Note" action triggers:
1. Export bookmark data from BM
2. Create source in Kasten
3. Create note linked to source
4. Delete bookmark from BM inbox

## What Was Done This Session

1. Deployed Telegram bot to K3s (was only running in dev)
2. Migrated videos from dev to prod database
3. Updated `KNOWLEDGE-SYSTEM-OVERVIEW.md` with bot docs
4. Created design doc: `docs/plans/2025-12-23-knowledge-flow-redesign.md`

## Open Questions (need decisions)

1. **Videos** — Same 7-day expiry or longer (14 days)?
2. **Pinned/Papers** — Exempt from expiry or same rules?
3. **RSS feed items** — Same expiry logic?

## Files to Reference

- Design doc: `/home/ags/knowledge-system/docs/plans/2025-12-23-knowledge-flow-redesign.md`
- Overview: `/home/ags/knowledge-system/KNOWLEDGE-SYSTEM-OVERVIEW.md`
- Cognitive research: Search for "elaborative interrogation", "generation effect", "desirable difficulties"

## Next Steps

1. Answer open questions (videos/pinned/RSS expiry)
2. Implement Kasten `sources` table
3. Add `source_id` to Kasten notes
4. Add expiry logic to Bookmark Manager
5. Build "Archive & Create Note" flow in Canvas
6. Migration: move existing archived bookmarks to Kasten sources

## Prompt for Next Session

```
Continue implementing the knowledge flow redesign from docs/plans/2025-12-23-knowledge-flow-redesign.md

Summary: We redesigned the bookmark → note workflow based on cognitive science:
- Bookmark Manager inbox now expires items after 7 days
- To "archive" = create a Kasten note referencing the source
- Kasten gets a new `sources` table (the archive moves there)
- Canvas handles the "archive & create note" action

Open questions to resolve first:
1. Should videos have longer expiry than 7 days?
2. Should pinned/paper bookmarks be exempt from expiry?
3. Should RSS feed items follow the same expiry logic?

Then implement the changes per the design doc.
```
