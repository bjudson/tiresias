# Dream Journal Conventions

## Dream file (`dreams/YYYY-MM-DD - dream-title-slug.md`)

```markdown
---
date: 2025-05-30
title: Dream title slug
symbols: [water, old-house, stranger]
---

Full dream narrative in prose.
```

## Symbol file (`symbols/<slug>.md`)

```markdown
---
title: Water
slug: water
summary: Vast or murky bodies of water appearing as obstacles or environments
associations: []
interpretations: []
---

Free-form notes added by the dreamer over time.
```

- `slug`: lowercase, hyphen-separated filename stem
- `associations`: related symbols, feelings, or contexts (human-authored)
- `interpretations`: personal meaning built up over time (human-authored)
- Body: free prose, human-authored

## Symbol extraction rules

Symbols are image-full figures, places, objects, actions, or atmospheric
qualities drawn from the dream — analyzed using James Hillman's imaginal
psychology. They should be:
- Distinct enough to warrant their own file — do not over-extract
- Matched to an existing symbol if the dream image is the same core concept,
  even if described differently in the new dream
