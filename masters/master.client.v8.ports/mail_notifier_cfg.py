# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master.v8.v8_notifier import V8Notifier


def Update(config, active_master, c):
  c['status'].extend([])
