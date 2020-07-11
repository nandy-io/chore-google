"""
Main module for daemon
"""

import os
import time
import yaml
import json
import datetime
import traceback

import yaml
import requests
import redis
import google.oauth2.credentials
import googleapiclient.discovery


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

        self.cache = {}

    def check(self, event):

        if event['id'] not in self.cache:

            self.cache[event['id']] = time.time()

            exists = self.redis.get(f"{self.prefix}/{event['id']}")

            if not exists:
                self.redis.set(f"{self.prefix}/{event['id']}", True, ex=24*60*60)
                return False

        return True

    def clear(self):

        for event_id, when in list(self.cache.items()):
            if when + 24*60*60 < time.time():
                del self.cache[event_id]

    CLEAN = {
        "<span>": "",
        "</span>": "",
        "<br>": "\n",
        "&nbsp;": " "
    }

    def clean(self, description):

        for old, new in self.CLEAN.items():
            description = description.replace(old, new)

        return description

    def event(self, event):

        if self.check(event):
            return

        for action in yaml.safe_load_all(self.clean(event["description"])):

            if not isinstance(action, dict) or not action:
                continue

            if "routine" in action:

                requests.post(f"{self.chore}/routine", json={"routine": action["routine"]}).raise_for_status()

            elif "todo" in action:

                requests.post(f"{self.chore}/todo", json={"todo": action["todo"]}).raise_for_status()

            elif "todos" in action:

                requests.patch(f"{self.chore}/todo", json={"todos": action["todos"]}).raise_for_status()

    def within(self):

        with open("/opt/service/config/settings.yaml", "r") as settings_file:
            settings = yaml.safe_load(settings_file)

        service = googleapiclient.discovery.build(
            'calendar', 'v3',
            credentials=google.oauth2.credentials.Credentials(**json.loads(settings['calendar']['credentials']))
        )

        after = datetime.datetime.utcnow()
        before = after - datetime.timedelta(seconds=self.range)

        return service.events().list(
            calendarId=settings['calendar']['watch'],
            timeMin=before.isoformat() + 'Z',
            timeMax=after.isoformat() + 'Z',
            singleEvents=True
        ).execute().get('items', [])

    def process(self):
        """
        Processes events within the range
        """

        for event in self.within():

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
