"""Offline regressions for the October 2026 US Life Hub content incident."""
import copy
import unittest
from datetime import date, datetime, timezone

from scripts.send_community_newsletters import build_personalized_html, filter_events_for_interests
from scripts.uslifehub_event_quality import current_date, descriptive_title, prepare_current_event

TODAY = date(2026, 10, 8)


def record(**kwargs):
    return dict({'id': 'test', 'title_zh': '社区文化活动', 'module': '文化·节庆',
                 'summary_zh': '查看主办方活动说明', 'url': 'https://example.org/program',
                 'date_kind': 'service', 'event_date': '', 'first_indexed_at': '2026-10-08 19:00:00'}, **kwargs)


class EventQualityTests(unittest.TestCase):
    def test_old_parades_are_not_evergreen_even_if_freshly_indexed(self):
        for year in (2017, 2019, 2024):
            with self.subTest(year=year):
                event = record(title_zh=f'{year}年春节游行', url=f'https://fcbainc.org//{year}-lunar-new-year-parade/')
                self.assertIsNone(prepare_current_event(event, as_of=TODAY))

    def test_url_year_catches_generic_archive_subpage_title(self):
        self.assertIsNone(prepare_current_event(record(title_zh='选定演讲者和特别会议',
            url='https://example.org/2018annual-convention/selected-speakers/'), as_of=TODAY))

    def test_old_service_policy_year_is_not_event_expiry(self):
        self.assertIsNotNone(prepare_current_event(record(title_zh='2024住房法案与租客权利',
            url='https://example.org/law/2024-tenant-rights', published_at='2024-01-01'), as_of=TODAY))

    def test_past_event_rejected_even_when_newly_indexed(self):
        self.assertEqual([], filter_events_for_interests([record(event_date='2026-10-07')], ['culture_festival'], as_of=TODAY))

    def test_event_today_and_future_are_kept(self):
        for day in ('2026-10-08', '2026-11-13'):
            self.assertIsNotNone(prepare_current_event(record(event_date=day), as_of=TODAY))

    def test_ongoing_event_kept_until_end(self):
        self.assertIsNotNone(prepare_current_event(record(event_date='2026-10-01', end_date='2026-10-09'), as_of=TODAY))
        self.assertIsNone(prepare_current_event(record(event_date='2026-10-01', end_date='2026-10-07'), as_of=TODAY))

    def test_invalid_or_missing_explicit_event_date_is_excluded(self):
        for fields in ({'event_date': 'invalid'}, {'event_date': '2026-02-30'}, {'date_kind': 'event'},
                       {'event_date': '2026-10-10', 'end_date': '2026-10-01'}):
            with self.subTest(fields=fields):
                self.assertIsNone(prepare_current_event(record(**fields), as_of=TODAY))

    def test_year_alone_does_not_prove_future_event(self):
        self.assertIsNone(prepare_current_event(record(title_zh='2026农历新年游行'), as_of=TODAY))

    def test_dates_in_event_url_work_with_single_digit_month_and_day(self):
        self.assertIsNone(prepare_current_event(record(url='https://example.org/events/2026/9/2/workshop'), as_of=TODAY))
        result = prepare_current_event(record(url='https://example.org/events/2026/11/2/workshop'), as_of=TODAY)
        self.assertEqual('2026-11-02', result['event_date'])

    def test_conflicting_url_and_record_date_fails_closed(self):
        self.assertIsNone(prepare_current_event(record(event_date='2026-10-30',
            url='https://example.org/events/2026/9/2/workshop'), as_of=TODAY))

    def test_carea_month_heading_is_recovered_from_event_slug(self):
        event = record(title_zh='2026年10月', event_date='2026-10-30',
            url='https://www.careausa.com/event/33rd-anniversary-gala')
        result = prepare_current_event(event, as_of=TODAY)
        self.assertEqual('33rd anniversary gala', result['title_zh'])

    def test_cacf_button_heading_is_recovered_from_event_slug(self):
        event = record(title_zh='查看活动 →', event_date='2026-11-13',
            url='https://www.cacf.org/events/2026-catalyst-for-change-awards-gala')
        self.assertEqual('2026 catalyst for change awards gala', prepare_current_event(event, as_of=TODAY)['title_zh'])

    def test_english_month_and_button_use_alternate_title(self):
        for title in ('Oct 2026', 'October 2026', 'View Event →'):
            self.assertEqual('Community Gala', descriptive_title(record(title_zh=title, title_en='Community Gala')))

    def test_generic_title_without_evidence_is_dropped(self):
        self.assertIsNone(prepare_current_event(record(title_zh='查看活动 →', url='https://example.org/events/123'), as_of=TODAY))

    def test_wrong_library_source_is_excluded_without_rewriting_authority(self):
        self.assertIsNone(prepare_current_event(record(title_zh='NYPL法拉盛图书馆（Flushing Library）',
            url='https://www.nypl.org/locations/flushing'), as_of=TODAY))
        self.assertIsNone(prepare_current_event(record(title_zh='纽约公共图书馆法拉盛分馆（皇后区华人社区）',
            url='https://www.nypl.org/events?location=flushing'), as_of=TODAY))
        self.assertIsNotNone(prepare_current_event(record(title_zh='Queens Public Library 法拉盛图书馆'), as_of=TODAY))
        self.assertIsNotNone(prepare_current_event(record(title_zh='NYPL Chatham Square Library'), as_of=TODAY))

    def test_missing_ids_do_not_collapse_unrelated_events(self):
        events = [record(id=None, url='https://example.org/a'), record(id=None, url='https://example.org/b')]
        self.assertEqual(2, len(filter_events_for_interests(events, ['culture_festival'], as_of=TODAY)))

    def test_original_archive_record_is_not_mutated_or_deleted(self):
        original = record(title_zh='2019年春节游行', date_kind='archive')
        snapshot = copy.deepcopy(original)
        self.assertEqual([], filter_events_for_interests([original], [], as_of=TODAY))
        self.assertEqual(snapshot, original)

    def test_eastern_date_boundary(self):
        self.assertEqual(TODAY, current_date(datetime(2026, 10, 9, 1, tzinfo=timezone.utc)))

    def test_source_title_entities_remain_text_in_newsletter(self):
        event = record(title_zh='文化活动 &lt;em&gt;标题&lt;/em&gt;')
        matched = filter_events_for_interests([event], ['culture_festival'], as_of=TODAY)
        output = build_personalized_html('test@example.org', matched, ['culture_festival'], 'test')
        self.assertIn('&lt;em&gt;标题&lt;/em&gt;', output)
        self.assertNotIn('<em>标题</em>', output)

    def test_newsletter_html_uses_only_valid_current_titles(self):
        events = [record(id='old', title_zh='2017年春节游行'), record(id='gala', title_zh='查看活动 →',
            event_date='2026-11-13', url='https://www.cacf.org/events/2026-catalyst-for-change-awards-gala')]
        matched = filter_events_for_interests(events, ['culture_festival'], as_of=TODAY)
        output = build_personalized_html('test@example.org', matched, ['culture_festival'], '2026-W41-Thu')
        self.assertNotIn('2017年春节游行', output)
        self.assertNotIn('查看活动 →', output)
        self.assertIn('2026 catalyst for change awards gala', output)


if __name__ == '__main__':
    unittest.main()
