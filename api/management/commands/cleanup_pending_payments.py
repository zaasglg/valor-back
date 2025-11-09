from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from api.models import HistorialPagos, Transaction

class Command(BaseCommand):
    help = 'Удаляет или помечает как failed платежи в статусе "esperando" старше 8 минут'

    def add_arguments(self, parser):
        parser.add_argument(
            '--delete',
            action='store_true',
            help='Удалить старые платежи вместо пометки как failed',
        )
        parser.add_argument(
            '--minutes',
            type=int,
            default=8,
            help='Количество минут для таймаута (по умолчанию 8)',
        )

    def handle(self, *args, **options):
        delete_mode = options['delete']
        timeout_minutes = options['minutes']
        
        timeout_time = timezone.now() - timedelta(minutes=timeout_minutes)
        
        self.stdout.write(self.style.WARNING(
            f'Начинаем очистку платежей старше {timeout_minutes} минут...'
        ))
        
        historial_pending = HistorialPagos.objects.filter(
            estado='esperando',
            transacciones_data__lt=timeout_time
        )
        
        historial_count = historial_pending.count()
        
        if delete_mode:
            historial_pending.delete()
            self.stdout.write(self.style.SUCCESS(
                f'Удалено {historial_count} записей из HistorialPagos'
            ))
        else:
            historial_pending.update(estado='failed')
            self.stdout.write(self.style.SUCCESS(
                f'Помечено {historial_count} записей как "failed" в HistorialPagos'
            ))
        
        # Очищаем Transaction
        transaction_pending = Transaction.objects.filter(
            estado='esperando',
            transacciones_data__lt=timeout_time
        )
        
        transaction_count = transaction_pending.count()
        
        if delete_mode:
            transaction_pending.delete()
            self.stdout.write(self.style.SUCCESS(
                f'Удалено {transaction_count} записей из Transaction'
            ))
        else:
            transaction_pending.update(estado='failed')
            self.stdout.write(self.style.SUCCESS(
                f'Помечено {transaction_count} записей как "failed" в Transaction'
            ))
        
        total = historial_count + transaction_count
        
        if total == 0:
            self.stdout.write(self.style.SUCCESS('Старых платежей не найдено'))
        else:
            self.stdout.write(self.style.SUCCESS(
                f'Всего обработано: {total} платежей'
            ))
