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

import klotio

class Daemon(object):
    """
    Main class for daemon
    """

    def __init__(self):

        self.chore_api = os.environ['CHORE_API']
        self.range = int(os.environ['RANGE'])
        self.sleep = int(os.environ['SLEEP'])

        self.redis = redis.Redis(host=os.environ['REDIS_HOST'], port=int(os.environ['REDIS_PORT']))
        self.prefix = f"{os.environ['REDIS_PREFIX']}/event"

        self.cache = {}

        self.logger = klotio.logger("nandy-io-chore-google-daemon")

        self.logger.debug("init", extra={
            "init": {
                "sleep": self.sleep,
                "range": self.range,
                "redis": {
                    "connection": str(self.redis),
                    "prefix": self.prefix
                },
                "chore_api": self.chore_api
            }
        })

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

        self.logger.info("event", extra={"event": event})

        for action in yaml.safe_load_all(self.clean(event["description"])):

            self.logger.info("action", extra={"action": action})

            if not isinstance(action, dict) or not action:
                continue

            if "routine" in action:

                self.logger.info("routine")
                requests.post(f"{self.chore_api}/routine", json={"routine": action["routine"]}).raise_for_status()

            elif "todo" in action:

                self.logger.info("todo")
                requests.post(f"{self.chore_api}/todo", json={"todo": action["todo"]}).raise_for_status()

            elif "todos" in action:

                self.logger.info("todos")
                requests.patch(f"{self.chore_api}/todo", json={"todos": action["todos"]}).raise_for_status()

    def within(self):

        with open("/opt/service/config/settings.yaml", "r") as settings_file:
            settings = yaml.safe_load(settings_file)

        service = googleapiclient.discovery.build(
            'calendar', 'v3',
            credentials=google.oauth2.credentials.Credentials(**json.loads(settings['calendar']['credentials'])),
            cache_discovery=False
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
