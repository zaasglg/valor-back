from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from api.models import HistorialPagos

class Command(BaseCommand):
    help = 'Expire pending withdrawal requests older than 1 minute (set estado to rechazado)'

    def add_arguments(self, parser):
        parser.add_argument('--once', action='store_true', help='Run once and exit')

    def handle(self, *args, **options):
        run_once = options.get('once', False)

        try:
            while True:
                cutoff = timezone.now() - timedelta(minutes=1)
                pending = HistorialPagos.objects.filter(estado='esperando', transacciones_data__lte=cutoff)
                count = pending.count()
                if count:
                    for p in pending:
                        p.estado = 'rechazado'
                        p.save()
                    self.stdout.write(self.style.SUCCESS(f'Set {count} withdrawal(s) to rechazado'))
                else:
                    self.stdout.write('No withdrawals to expire')

                if run_once:
                    break
                # sleep 30 seconds between checks to avoid tight loop
                import time
                time.sleep(30)

        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('Stopped by user'))
