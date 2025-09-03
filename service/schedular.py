# service/meeting_scheduler.py
import os
import pickle
import datetime
import pytz
from typing import List, Dict, Any

from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request


SCOPES = ['https://www.googleapis.com/auth/calendar']


class MeetingScheduler:
    def __init__(self):
        self.service = self._get_calendar_service()

    def _get_calendar_service(self):
        """Authenticate and return Google Calendar service."""
        creds = None
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', SCOPES
                )
                creds = flow.run_local_server(port=0)
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)
        return build('calendar', 'v3', credentials=creds)

    def schedule_meeting(self, date_str, start_time_str, end_time_str, attendee_email):
        """Schedules a meeting if no conflict exists."""
        # Parse meeting datetime
        year, month, day = map(int, date_str.split('-'))
        start_hour, start_minute = map(int, start_time_str.split(':'))
        end_hour, end_minute = map(int, end_time_str.split(':'))

        local_timezone = pytz.timezone('Asia/Kolkata')
        start_time = local_timezone.localize(datetime.datetime(year, month, day, start_hour, start_minute))
        end_time = local_timezone.localize(datetime.datetime(year, month, day, end_hour, end_minute))

        # Check for conflicts
        events_result = self.service.events().list(
            calendarId='primary',
            timeMin=start_time.isoformat(),
            timeMax=end_time.isoformat(),
            singleEvents=True,
            orderBy='startTime'
        ).execute()

        conflicts = events_result.get('items', [])
        if conflicts:
            conflict_summaries = [
                {
                    "summary": e.get("summary"),
                    "start": e["start"].get("dateTime"),
                    "end": e["end"].get("dateTime")
                }
                for e in conflicts
            ]
            return {
                "status": "conflict",
                "message": "⚠️ Conflicting meetings found. Cannot schedule.",
                "conflicts": conflict_summaries
            }

        # Create new event
        event = {
            'summary': 'Meeting',
            'start': {'dateTime': start_time.isoformat(), 'timeZone': 'Asia/Kolkata'},
            'end': {'dateTime': end_time.isoformat(), 'timeZone': 'Asia/Kolkata'},
            'attendees': [{'email': attendee_email}],
        }

        created_event = self.service.events().insert(
            calendarId='primary', body=event
        ).execute()

        return {
            "status": "scheduled",
            "message": f"✅ Meeting scheduled with {attendee_email}",
            "meeting_link": created_event.get("htmlLink"),
            "event_id": created_event.get("id"),
        }

    def finish_meeting(self, event_id):
        """Deletes a scheduled meeting."""
        try:
            self.service.events().delete(calendarId='primary', eventId=event_id).execute()
            return {
                "status": "finished",
                "message": f"✅ Meeting {event_id} deleted successfully."
            }
        except Exception as e:
            return {"status": "error", "message": f"Error deleting event: {e}"}

    def list_meetings(self):
        """Fetch upcoming 10 events."""
        now = datetime.datetime.utcnow().isoformat() + 'Z'
        events_result = self.service.events().list(
            calendarId='primary',
            timeMin=now,
            maxResults=10,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        events = events_result.get('items', [])

        return [
            {
                "summary": e.get("summary"),
                "start": e["start"].get("dateTime"),
                "end": e["end"].get("dateTime"),
                "attendees": [a["email"] for a in e.get("attendees", [])]
            }
            for e in events
        ]


# Instantiate scheduler
scheduler = MeetingScheduler()