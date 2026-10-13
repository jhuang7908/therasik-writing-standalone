# US Life Hub content-quality checks

## Scope

The newsletter selector and both social content builders share a current-event
gate. It uses America/New_York's calendar date, never an index/discovery timestamp
as proof an event is upcoming. Past events, malformed/conflicting dates, explicit
archives, and year-tagged events without enough date evidence are excluded from
current recommendations. Evergreen policy/service pages remain eligible.
An event-detail URL still needs schedule evidence when upstream labels it a
service. Known calendar/browsing entry points remain services. Source listing
dates survive URL-date normalization in the search index, so contradictory
listing/URL dates, title years, or date aliases fail closed at publication.

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

October 12, 2026 index replay (generated 20:25; 120 records): 49 records remain
eligible as of October 12. The same old parade pages and false NYPL-Flushing
entry are excluded. CACF's undated-in-index `aycan-our-community-our-voices`
event page is excluded too; its official page identifies June 8, 2025. The
October 30 CAREA and November 13 CACF galas retain their actual dates and
descriptive titles. A future event in this week's selection must not be called
an event happening this week.

Pre-merge verification on October 13, 2026: 58 focused offline tests and 128
subtests pass on Python 3.12. New regressions cover mislabeled undated events,
source-date conflicts through ingestion/indexing, and biography wording variants
while permitting ordinary editorial phrases about life in New York. LLM,
image-generation, and delivery calls remain mocked. No production replay was run.

## Rollout boundary

A PR does not update production until merged. The private newsletter and social
executors in `Antibody-Engineer-Suite-MVP` explicitly check out
`therasik-writing-standalone` main (verified October 13, 2026). After merge, the
next scheduled generation uses these guards. No push or pull-request triggers
are configured in the code repository, so merging does not itself send mail
or run CI. This patch does not change cron,
recipients, SMTP, API billing/limits or campaign state, and does not resend any
already-delivered package. Existing bad cached packages fail closed and require
review/correction and matching images before any separately authorized resend.
