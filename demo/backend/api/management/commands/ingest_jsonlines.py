import json
import requests
from django.core.management.base import BaseCommand, CommandError

from concurrent.futures import ThreadPoolExecutor, as_completed


class Command(BaseCommand):
    help = 'Parses a JSON Lines file and sends data as POST requests to the Django API'

    def add_arguments(self, parser):
        parser.add_argument(
            'file_path',
            type=str,
            help='The path to the JSON Lines (.jsonl) file containing the data',
        )
        parser.add_argument(
            '--api-url',
            type=str,
            default='http://localhost/api/add_page/',
            help='The API endpoint URL for posting data',
        )

    def issue_request(self, url, line):
        try:
            data = json.loads(line.strip())

            # Validate necessary fields
            if not all(key in data for key in ['url', 'title', 'content']):
                self.stdout.write(self.style.ERROR("Missing required fields in line: " + line))
                return

            # Send POST request to the API
            response = requests.post(url, json=data)

            # Check the response status
            if response.status_code == 201:
                self.stdout.write(self.style.SUCCESS(f"Successfully ingested: {data['url']}"))
            else:
                error_msg = response.json().get('error', 'Unknown error')
                self.stdout.write(self.style.ERROR(f"Failed to ingest {data['url']}: {error_msg}"))

        except json.JSONDecodeError:
            self.stdout.write(self.style.ERROR("Invalid JSON in line: " + line))



    def handle(self, *args, **options):
        file_path = options['file_path']
        api_url = options['api_url']

        try:
            with open(file_path, 'r') as file:
                with ThreadPoolExecutor(max_workers=2) as executor:
                    futures = []
                    for line in file:
                        futures.append(executor.submit(self.issue_request, api_url, line))
                    for future in as_completed(futures):
                        pass

        except FileNotFoundError:
            raise CommandError(f"The file '{file_path}' does not exist.")

        except Exception as e:
            raise CommandError(f"An error occurred: {str(e)}")
