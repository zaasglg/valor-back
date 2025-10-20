from django.core.management.base import BaseCommand
from django.utils import timezone
from api.models import UserProfile, Country
from decimal import Decimal
import time
import logging

logger = logging.getLogger(__name__)

# Thresholds per country (values are in local currency assumed in UserProfile.deposit)
THRESHOLDS = {
    'colombia': Decimal('45000000'),  # 45,000,000 COP
    'ecuador': Decimal('10000'),      # 10,000 USD
    'paraguay': Decimal('70000000'),  # 70,000,000 PYG
}


def country_key(name: str) -> str:
    if not name:
        return ''
    n = name.strip().lower()
    if 'colomb' in n:
        return 'colombia'
    if 'ecuador' in n:
        return 'ecuador'
    if 'paraguay' in n or 'paragu' in n or 'paraguay' in n:
        return 'paraguay'
    return n


class Command(BaseCommand):
    help = 'Continuously check user deposits and set stage to verif2 when thresholds are exceeded.'

    def add_arguments(self, parser):
        parser.add_argument('--once', action='store_true', help='Run the check only once and exit')
        parser.add_argument('--interval', type=int, default=5, help='Interval between checks in seconds (default: 5)')

    def handle(self, *args, **options):
        run_once = options.get('once', False)
        interval = options.get('interval', 5)

        self.stdout.write(self.style.SUCCESS(f'Starting deposit checker (interval={interval}s, once={run_once})'))

        try:
            while True:
                now = timezone.now()
                # Find users who are not yet verified to level 2
                users = UserProfile.objects.exclude(stage='verif2')

                updated = 0
                for u in users:
                    try:
                        key = country_key(u.country)
                        if key in THRESHOLDS:
                            threshold = THRESHOLDS[key]
                            # Compare deposit; ensure Decimal
                            deposit = Decimal(u.deposit or 0)
                            if deposit >= threshold:
                                old_stage = u.stage
                                u.stage = 'verif2'
                                u.save()
                                updated += 1
                                self.stdout.write(f"[{now}] User {u.user_id} ({u.email}) deposit={deposit} >= {threshold} -> stage: {old_stage} -> verif2")
                    except Exception as e:
                        logger.exception(f'Error processing user {u.id}: {e}')

                if updated:
                    self.stdout.write(self.style.SUCCESS(f'Updated {updated} user(s) to verif2'))
                else:
                    self.stdout.write(f'[{now}] No users updated')

                if run_once:
                    break

                time.sleep(max(1, interval))

        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('Deposit checker stopped by user'))
        except Exception as e:
            logger.exception('Deposit checker encountered an error')
            raise
