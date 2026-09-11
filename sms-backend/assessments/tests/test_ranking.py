from decimal import Decimal

from django.test import SimpleTestCase

from assessments.services.ranking import average_totals, competition_ranks


class CompetitionRanksTests(SimpleTestCase):
    def test_empty(self):
        self.assertEqual(competition_ranks([]), {})

    def test_unique_scores(self):
        ranks = competition_ranks([
            ('a', Decimal('70')),
            ('b', Decimal('90')),
            ('c', Decimal('80')),
        ])
        self.assertEqual(ranks, {'b': 1, 'c': 2, 'a': 3})

    def test_ties_share_rank_and_skip(self):
        ranks = competition_ranks([
            ('a', Decimal('90')),
            ('b', Decimal('80')),
            ('c', Decimal('80')),
            ('d', Decimal('70')),
        ])
        self.assertEqual(ranks, {'a': 1, 'b': 2, 'c': 2, 'd': 4})

    def test_average_totals(self):
        self.assertIsNone(average_totals([]))
        self.assertEqual(
            average_totals([Decimal('80'), Decimal('90')]),
            Decimal('85'),
        )
