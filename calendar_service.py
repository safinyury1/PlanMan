import os
import json
from datetime import datetime, timezone
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

SCOPES = ['https://www.googleapis.com/auth/calendar.events.readonly']
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_PATH = os.path.join(BASE_DIR, 'credentials.json')

def get_auth_url(user_id):
    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES, redirect_uri='urn:ietf:wg:oauth:2.0:oob')
    auth_url, _ = flow.authorization_url(prompt='consent')
    return auth_url

async def get_credentials_from_code(auth_code):
    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES, redirect_uri='urn:ietf:wg:oauth:2.0:oob')
    flow.fetch_token(code=auth_code)
    return flow.credentials.to_json()

async def get_upcoming_events(token_json):
    creds = Credentials.from_authorized_user_info(json.loads(token_json), SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    service = build('calendar', 'v3', credentials=creds)
    now = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    events_result = service.events().list(
        calendarId='primary', timeMin=now,
        maxResults=10, singleEvents=True, orderBy='startTime'
    ).execute()
    return events_result.get('items', [])

async def get_past_events(token_json):
    creds = Credentials.from_authorized_user_info(json.loads(token_json), SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
    service = build('calendar', 'v3', credentials=creds)
    now = datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    #получаем события, завершившиеся до текущего момента.
    events_result = service.events().list(
        calendarId='primary', timeMax=now,
        maxResults=10, singleEvents=True, orderBy='startTime'
    ).execute()
    items = events_result.get('items', [])
    items.reverse() #чтобы самые свежие их прошедших были первыми
    return items