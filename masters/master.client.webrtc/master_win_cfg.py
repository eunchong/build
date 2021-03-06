# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from buildbot.schedulers.basic import SingleBranchScheduler

from master.factory import annotator_factory

m_annotator = annotator_factory.AnnotatorFactory()

def Update(c):
  c['schedulers'].extend([
      SingleBranchScheduler(name='webrtc_windows_scheduler',
                            branch='master',
                            treeStableTimer=30,
                            builderNames=[
          'Win32 Debug',
          'Win32 Release',
          'Win64 Debug',
          'Win64 Release',
          'Win32 Release [large tests]',
          'Win64 Debug (GN)',
          'Win64 Release (GN)',
          'Win32 Debug (Clang)',
          'Win32 Release (Clang)',
          'Win64 Debug (Clang)',
          'Win64 Release (Clang)',
          'Win DrMemory Light',
          'Win DrMemory Full',
          'Win SyzyASan',
      ]),
  ])

  # 'slavebuilddir' below is used to reduce the number of checkouts since some
  # of the builders are pooled over multiple slave machines.
  specs = [
    {'name': 'Win32 Debug'},
    {'name': 'Win32 Release'},
    {'name': 'Win64 Debug'},
    {'name': 'Win64 Release'},
    {
      'name': 'Win32 Release [large tests]',
      'category': 'compile|baremetal|windows',
      'slavebuilddir': 'win_baremetal',
    },
    {'name': 'Win64 Debug (GN)', 'slavebuilddir': 'win64_gn'},
    {'name': 'Win64 Release (GN)', 'slavebuilddir': 'win64_gn'},
    {'name': 'Win32 Debug (Clang)', 'slavebuilddir': 'win_clang'},
    {'name': 'Win32 Release (Clang)', 'slavebuilddir': 'win_clang'},
    {'name': 'Win64 Debug (Clang)', 'slavebuilddir': 'win_clang'},
    {'name': 'Win64 Release (Clang)', 'slavebuilddir': 'win_clang'},
    {
      'name': 'Win DrMemory Light',
      'category': 'compile',
      'slavebuilddir': 'win-drmem',
    },
    {
      'name': 'Win DrMemory Full',
      'category': 'compile',
      'slavebuilddir': 'win-drmem',
    },
    {'name': 'Win SyzyASan', 'slavebuilddir': 'win-syzyasan'},
  ]

  c['builders'].extend([
      {
        'name': spec['name'],
        # TODO(sergiyb): Remove the timeout below after all bots have synched
        # past Blink merge commit.
        'factory': m_annotator.BaseFactory('webrtc/standalone', timeout=3600),
        'notify_on_missing': True,
        'category': spec.get('category', 'compile|testers|windows'),
        'slavebuilddir': spec.get('slavebuilddir', 'win'),
      } for spec in specs
  ])
