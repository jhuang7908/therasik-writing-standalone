"""Index/title regressions; no fetches, translation calls, or output writes."""
import unittest
from datetime import date
from scripts.send_community_newsletters import filter_events_for_interests
from scripts.run_nyc_community_live_update import _to_hub_item, build_hub_search_index
from nyc_community_events.models import CommunityEvent


class HubTitleExtractionTests(unittest.TestCase):
    def test_calendar_heading_uses_event_url_title_before_translation(self):
        ev = CommunityEvent(title='Oct 2026', start_date='2026-10-30', source='carea',
            url='https://www.careausa.com/event/33rd-anniversary-gala')
        result = _to_hub_item(ev, 1, {'name_zh': 'CAREA'})
        self.assertEqual('33rd anniversary gala', result['title_zh'])
        self.assertEqual('2026-10-30', result['event_date'])

    def test_index_corrects_old_cta_title_and_preserves_alternate_title(self):
        rows = [{'id': 'cacf', 'title_zh': '查看活动 →',
                 'title_en': '2026 Catalyst for Change Awards Gala',
                 'event_date': '2026-11-13',
                 'url': 'https://www.cacf.org/events/2026-catalyst-for-change-awards-gala'}]
        result = build_hub_search_index(rows, generated_at='2026-10-08 17:59')
        self.assertEqual('2026 Catalyst for Change Awards Gala', result['records'][0]['title_zh'])
        self.assertEqual(rows[0]['title_en'], result['records'][0]['title_en'])
        self.assertEqual('查看活动 →', rows[0]['title_zh'])

    def test_unresolved_generic_index_entry_is_omitted(self):
        result = build_hub_search_index([{'title_zh': '查看活动 →', 'url': 'https://example.org/events/123'}], generated_at='2026-10-08')
        self.assertEqual(0, result['count'])

    def test_ongoing_event_end_survives_index_to_selector(self):
        for end_field in ("event_end_date", "end_date"):
            with self.subTest(end_field=end_field):
                rows = [{"id": "ongoing", "module": "文化·节庆", "title_zh": "社区文化节",
                         "event_date": "2026-10-01", end_field: "2026-10-09",
                         "url": "https://example.org/community-festival"}]
                index = build_hub_search_index(rows, generated_at="2026-10-08")
                selected = filter_events_for_interests(index["records"], [], as_of=date(2026, 10, 8))
                self.assertEqual(1, len(selected))
                self.assertEqual("2026-10-09", selected[0]["event_end_date"])

    def test_archival_title_is_kept_in_search_index(self):
        result = build_hub_search_index([{'title_zh': '2017年春节游行', 'url': 'https://fcbainc.org/2017-lunar-new-year-parade/'}], generated_at='2026-10-08')
        self.assertEqual('2017年春节游行', result['records'][0]['title_zh'])


if __name__ == '__main__':
    unittest.main()
