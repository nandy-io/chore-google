import unittest
import unittest.mock

import os
import copy
import yaml
import datetime

import service

class MockRedis:

    def __init__(self, host, port):

        self.host = host
        self.port = port

        self.data = {}
        self.expires = {}

    def get(self, key):

        if key in self.data:
            return self.data[key]

        return None

    def set(self, key, value, ex=None):

        self.data[key] = value
        self.expires[key] = ex


class TestService(unittest.TestCase):

    @unittest.mock.patch.dict(os.environ, {
        "CHORE_API": "http://toast.com",
        "REDIS_HOST": "most.com",
        "REDIS_PORT": "667",
        "REDIS_PREFIX": "stuff",
        "RANGE": "10",
        "SLEEP": "7"
    })
    @unittest.mock.patch("redis.StrictRedis", MockRedis)
    def setUp(self):

        self.daemon = service.Daemon()

    @unittest.mock.patch.dict(os.environ, {
        "CHORE_API": "http://toast.com",
        "REDIS_HOST": "most.com",
        "REDIS_PORT": "667",
        "REDIS_PREFIX": "stuff",
        "RANGE": "10",
        "SLEEP": "7"
    })
    @unittest.mock.patch("redis.StrictRedis", MockRedis)
    def test___init__(self):

        daemon = service.Daemon()

        self.assertEqual(daemon.chore, "http://toast.com")
        self.assertEqual(daemon.redis.host, "most.com")
        self.assertEqual(daemon.redis.port, 667)
        self.assertEqual(daemon.prefix, "stuff/event")
        self.assertEqual(daemon.range, 10)
        self.assertEqual(daemon.sleep, 7)

    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=7))
    def test_check(self):

        self.assertFalse(self.daemon.check({"id": "meow"}))
        self.assertEqual(self.daemon.cache, {"meow": 7})
        self.assertEqual(self.daemon.redis.data, {"stuff/event/meow": True})
        self.assertEqual(self.daemon.redis.expires, {"stuff/event/meow": 86400})

        self.assertTrue(self.daemon.check({"id": "meow"}))

        self.daemon.cache = {}
        self.assertTrue(self.daemon.check({"id": "meow"}))

    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=86403))
    def test_clear(self):

        self.daemon.cache = {
            "stay": 3,
            "go": 2
        }

        self.daemon.clear()

        self.assertEqual(self.daemon.cache, {"stay": 3})

    @unittest.mock.patch("requests.post")
    @unittest.mock.patch("requests.patch")
    def test_event(self, mock_patch, mock_post):

        self.daemon.cache["done"] = True

        self.daemon.event({
            "id": "nope",
            "description": "nope"
        })
        mock_post.assert_not_called()

        self.daemon.event({
            "id": "empty",
            "description": yaml.safe_dump({}, default_flow_style=False)
        })
        mock_post.assert_not_called()

        self.daemon.event({
            "id": "done",
            "description": yaml.safe_dump_all([
                {"routine": "done"}
            ])
        })
        mock_post.assert_not_called()

        self.daemon.event({
            "id": "do",
            "description": yaml.safe_dump_all([
                {"routine": "now"},
                {"todo": "it"},
                {"todos": "them"}
            ])
        })
        mock_post.assert_has_calls([
            unittest.mock.call("http://toast.com/routine", json={"routine": "now"}),
            unittest.mock.call().raise_for_status(),
            unittest.mock.call("http://toast.com/todo", json={"todo": "it"}),
            unittest.mock.call().raise_for_status()
        ])
        mock_patch.assert_has_calls([
            unittest.mock.call("http://toast.com/todo", json={"todos": "them"}),
            unittest.mock.call().raise_for_status()
        ])

    @unittest.mock.patch("builtins.open", create=True)
    @unittest.mock.patch("googleapiclient.discovery.build")
    @unittest.mock.patch("google.oauth2.credentials.Credentials")
    @unittest.mock.patch("service.datetime")
    def test_within(self, mock_datetime, mock_credentials, mock_build, mock_open):

        mock_open.side_effect = [
            unittest.mock.mock_open(read_data="""calendar:\n  credentials: '{"a": 1}'\n  watch: tv""").return_value
        ]

        mock_credentials.return_value = "legit"

        mock_datetime.timedelta = datetime.timedelta
        mock_datetime.timezone = datetime.timezone
        mock_datetime.datetime.utcnow.return_value = datetime.datetime(2018, 12, 13, 14, 15, 16, tzinfo=datetime.timezone.utc)

        self.daemon.cache["done"] = True

        mock_build.return_value.events.return_value.list.return_value.execute.return_value.get.return_value = [
            {"description": "doh"}
        ]

        self.assertEqual(self.daemon.within(), [{"description": "doh"}])

        mock_open.assert_called_once_with("/opt/service/config/settings.yaml", "r")
        mock_credentials.assert_called_once_with(a=1)
        mock_build.assert_called_once_with('calendar', 'v3', credentials='legit')


        mock_build.return_value.events.return_value.list.assert_called_once_with(
            calendarId="tv",
            timeMin="2018-12-13T14:15:06+00:00Z",
            timeMax="2018-12-13T14:15:16+00:00Z",
            singleEvents=True
        )
        mock_build.return_value.events.return_value.list.return_value.execute.return_value.get.assert_called_once_with("items", [])

    @unittest.mock.patch("traceback.format_exc")
    @unittest.mock.patch('builtins.print')
    def test_process(self, mock_print, mock_traceback):


        self.daemon.cache["done"] = True

        self.daemon.within = unittest.mock.MagicMock(return_value=[
            {"description": "doh"}
        ])

        self.daemon.event = unittest.mock.MagicMock(side_effect=[Exception("whoops")])
        mock_traceback.return_value = "spirograph"

        self.daemon.process()

        mock_print.assert_has_calls([
            unittest.mock.call("whoops"),
            unittest.mock.call("spirograph")
        ])

    @unittest.mock.patch("requests.post")
    @unittest.mock.patch("service.time.sleep")
    @unittest.mock.patch("service.time.time", unittest.mock.MagicMock(return_value=86403))
    def test_run(self, mock_sleep, mock_post):

        self.daemon.range = 2
        self.daemon.cache = {
            "go": 2
        }

        self.daemon.within = unittest.mock.MagicMock(return_value=[
            {
                "id": "do",
                "description": yaml.safe_dump_all([
                    {"routine": "now"}
                ])
            }
        ])

        mock_sleep.side_effect = [Exception("doh")]

        self.assertRaisesRegex(Exception, "doh", self.daemon.run)

        mock_post.assert_has_calls([
            unittest.mock.call("http://toast.com/routine", json={"routine": "now"}),
            unittest.mock.call().raise_for_status()
        ])

        self.assertEqual(self.daemon.cache, {"do": 86403})

        mock_sleep.assert_called_with(7)