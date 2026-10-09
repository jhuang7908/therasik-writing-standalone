# US Life Hub content-quality checks

## Scope

The newsletter selector and both social content builders share a current-event
gate. It uses America/New_York's calendar date, never an index/discovery timestamp
as proof an event is upcoming. Past events, malformed/conflicting dates, explicit
archives, and year-tagged events without enough date evidence are excluded from
current recommendations. Evergreen policy/service pages remain eligible.

Historical records are not deleted from the hub or search index. They can still
be used in explicitly historical writing. Search index and ingestion title
construction prefer descriptive structured titles, then event-specific URL slugs;
calendar-month headings and CTA labels are not accepted as event titles.

The verified Flushing Library authority is Queens Public Library:
https://www.queenslibrary.org/about-us/locations/flushing
The known incorrect NYPL-Flushing source is rejected rather than silently given
invented service or enrollment details.

Social writing uses an editorial voice with no invented biography. Targeted
checks reject known NYPL/Flushing contradictions and unsupported narrator
residence/firsthand-experience claims in nested copy and image prompts. Checks
run before saving new JSON, before rendering, and across the entire selected
cached batch before the first email, including `--emails-only`. Each image
bundle is bound to its platform content and exact image bytes with a hash
manifest. Full runs rebuild a missing/stale cache; email-only runs fail closed
when any selected image bundle lacks a matching manifest or expected images.

These are targeted regression guards, not a general factual-verification system.
Other source claims still require editorial review. Text checks do not verify
rendered image text/pixels or prove external recipient delivery.

## Offline regression tests

Using Python 3.11+ in an isolated virtual environment:

```sh
python -m pip install requests feedparser PyYAML pytest
python -m pytest -q tests/test_uslifehub_*.py
```

Tests use fixtures and mocked LLM, image and email calls. They do not send mail,
use credentials, generate paid content, or change campaign/subscriber state.
Do not run the ordinary send/generate entry points to test this change.

October 8, 2026 index replay (120 records): the current selector retains 51
eligible records. It excludes the reported 2017/2019/2024 FCBA parade pages and
the contradictory NYPL Flushing entry, while retaining both upcoming galas with
source-grounded descriptive titles. The replay does not claim every retained
record is independently fact-checked or that its schedule has been reconfirmed.

## Rollout boundary

A draft PR does not update production. The private scheduled executor currently
checks out `therasik-writing-standalone` main. After authorized review/merge, the
next authorized generation uses these guards. This patch does not change cron,
recipients, SMTP, API billing/limits or campaign state, and does not resend any
already-delivered package. Existing bad cached packages fail closed and require
review/correction and matching images before any separately authorized resend.
