#!/usr/bin/env python

import shutil
import service

shutil.copy("/opt/service/secret/token.json", "/opt/service/token.json")
service.Daemon().run()
