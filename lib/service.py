"""
Main module for daemon
"""

import os
import time
import json
import datetime
import traceback

import yaml
import requests
import redis
import googleapiclient.discovery
import httplib2
import oauth2client.file


class Daemon(object):
    """
    Main class for daemon
    """

    def __init__(self):

        self.chore = os.environ['CHORE_API']
        self.range = int(os.environ['RANGE'])
        self.sleep = int(os.environ['SLEEP'])

        self.redis = redis.StrictRedis(host=os.environ['REDIS_HOST'], port=int(os.environ['REDIS_PORT']))
        self.prefix = f"{os.environ['REDIS_PREFIX']}/event"

        with open("/opt/service/secret/calendar.json", "r") as calendar_file:
            self.calendar = json.load(calendar_file)["name"]

        self.calendar_api = googleapiclient.discovery.build(
            'calendar', 
            'v3', 
            http=oauth2client.file.Storage('/opt/service/token.json').get().authorize(httplib2.Http())
        )

        for calendar in self.calendar_api.calendarList().list().execute().get('items', []):
            if calendar["summary"] == self.calendar:
                self.calendar_id = calendar["id"]

        self.cache = {}

    def check(self, event):

        if event['id'] not in self.cache:

            self.cache[event['id']] = time.time()

            exists = self.redis.get(f"{self.prefix}/{event['id']}")

            if not exists:
                self.redis.set(f"{self.prefix}/{event['id']}", True, ex=2*self.range)
                return False

        return True

    def clear(self):

        for event_id, when in list(self.cache.items()):
            if when + self.range*2 < time.time():
                del self.cache[event_id]

    def event(self, event):

        if self.check(event):
            return

        for action in yaml.safe_load_all(event["description"]):

            if not isinstance(action, dict) or not action:
                continue

            if "routine" in action:

                requests.post(f"{self.chore}/routine", json={"routine": action["routine"]}).raise_for_status()

            elif "todo" in action:

                requests.post(f"{self.chore}/todo", json={"todo": action["todo"]}).raise_for_status()

            elif "todos" in action:

                requests.patch(f"{self.chore}/todo", json={"todos": action["todos"]}).raise_for_status()

    def process(self):
        """
        Processes events within the range
        """

        after = datetime.datetime.utcnow()
        before = after - datetime.timedelta(seconds=self.range)

        for event in self.calendar_api.events().list(
            calendarId=self.calendar_id, 
            timeMin=before.isoformat() + 'Z', 
            timeMax=after.isoformat() + 'Z', 
            singleEvents=True
        ).execute().get('items', []):

            try:

                self.event(event)

            except Exception as exception:
                print(str(exception))
                print(traceback.format_exc())

    def run(self):
        """
        Runs the daemon
        """

        while True:
            self.process()
            self.clear()
            time.sleep(self.sleep)
