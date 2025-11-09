from django.core.management.base import BaseCommand
from events.models import Event
from attendance.models import EventReport
from clubs.email_utils import send_event_report_email
from clubs.pdf_utils import generate_event_pdf_report


class Command(BaseCommand):
    help = 'Test email report by sending report for a specific event with PDF'

    def add_arguments(self, parser):
        parser.add_argument('event_id', type=int, help='Event ID to generate report for')

    def handle(self, *args, **options):
        event_id = options['event_id']

        try:
            event = Event.objects.get(event_id=event_id)

            self.stdout.write(f'Event: {event.event_name}')
            self.stdout.write(
                f'Club Head: {event.club.club_head.get_full_name() if event.club.club_head else "Not assigned"}')
            self.stdout.write(f'Email: {event.club.club_head.email if event.club.club_head else "N/A"}')
            self.stdout.write('-' * 60)

            # Generate or get existing report
            report = EventReport.objects.filter(event=event).first()
            if not report:
                self.stdout.write('Generating database report...')
                report = EventReport.generate_report(event)
                self.stdout.write(self.style.SUCCESS('✓ Database report generated'))
            else:
                self.stdout.write(self.style.WARNING('→ Using existing database report'))

            # Generate PDF
            self.stdout.write('Generating PDF with charts...')
            pdf_path = generate_event_pdf_report(event, report)
            self.stdout.write(self.style.SUCCESS(f'✓ PDF generated at: {pdf_path}'))

            # Send email with PDF
            self.stdout.write('Sending email with PDF attachment...')
            success = send_event_report_email(event, report, pdf_path)

            if success:
                self.stdout.write(self.style.SUCCESS(f'✓ Email sent successfully to {event.club.club_head.email}'))
                self.stdout.write(self.style.SUCCESS('✓ PDF was attached to the email'))
            else:
                self.stdout.write(self.style.ERROR('✗ Failed to send email'))

        except Event.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'✗ Event with ID {event_id} not found'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Error: {str(e)}'))
            import traceback
            self.stdout.write(traceback.format_exc())