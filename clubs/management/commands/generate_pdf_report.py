from django.core.management.base import BaseCommand
from events.models import Event
from attendance.models import EventReport
from clubs.pdf_utils import generate_event_pdf_report


class Command(BaseCommand):
    help = 'Generate PDF report for a specific event'

    def add_arguments(self, parser):
        parser.add_argument('event_id', type=int, help='Event ID to generate report for')

    def handle(self, *args, **options):
        event_id = options['event_id']

        try:
            event = Event.objects.get(event_id=event_id)

            self.stdout.write(f'Generating PDF report for: {event.event_name}')

            # Generate or get existing report
            report = EventReport.objects.filter(event=event).first()
            if not report:
                report = EventReport.generate_report(event)
                self.stdout.write(self.style.SUCCESS('✓ Database report generated'))
            else:
                self.stdout.write(self.style.WARNING('→ Using existing database report'))

            # Generate PDF
            self.stdout.write('Generating PDF with charts...')
            pdf_path = generate_event_pdf_report(event, report)

            self.stdout.write(self.style.SUCCESS(f'✓ PDF report generated successfully!'))
            self.stdout.write(self.style.SUCCESS(f'📄 Location: {pdf_path}'))

        except Event.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'✗ Event with ID {event_id} not found'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Error: {str(e)}'))