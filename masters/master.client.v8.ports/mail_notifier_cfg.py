# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from master.v8.v8_notifier import V8Notifier


def Update(config, active_master, c):
  c['status'].extend([
    V8Notifier(
        config,
        active_master,
        categories_steps={
          's390': ['runhooks', 'compile', 'Check'],
        },
        extraRecipients=[
          'joransiu@ca.ibm.com',
          'jyan@ca.ibm.com',
          'michael_dawson@ca.ibm.com',
        ],
    ),
    V8Notifier(
        config,
        active_master,
        categories_steps={
          'x87': ['runhooks', 'compile', 'Check'],
        },
        extraRecipients=[
          'weiliang.lin@intel.com',
          'chunyang.dai@intel.com',
          'zhengxing.li@intel.com',
        ],
    ),
  ])
