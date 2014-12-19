# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
    'adb',
    'bot_update',
    'chromium',
    'chromium_android',
    'gclient',
    'json',
    'step',
    'path',
    'properties',
]

REPO_URL = 'https://chromium.googlesource.com/chromium/src.git'

BUILDERS = {
  'chromium.perf': {
    'android_nexus5_oilpan_perf': {
      'perf_id': 'android-nexus5-oilpan',
      'bucket': 'chromium-android',
      'path': lambda api: (
          '%s/build_product_%s.zip' % (
              api.properties['parent_buildername'],
              api.properties['parent_revision'])),
      'num_device_shards': 1,
    },
    'Android Nexus4 Perf': {
      'perf_id': 'android-nexus4',
      'bucket': 'chrome-perf',
      'path': lambda api: ('android_perf_rel/full-build-linux_%s.zip' %
                           api.properties['parent_revision']),
      'num_device_shards': 8,
    },
    'Android Nexus5 Perf': {
      'perf_id': 'android-nexus5',
      'bucket': 'chrome-perf',
      'path': lambda api: ('android_perf_rel/full-build-linux_%s.zip' %
                           api.properties['parent_revision']),
      'num_device_shards': 8,
    },
    'Android Nexus7v2 Perf': {
      'perf_id': 'android-nexus7v2',
      'bucket': 'chrome-perf',
      'path': lambda api: ('android_perf_rel/full-build-linux_%s.zip' %
                           api.properties['parent_revision']),
      'num_device_shards': 8,
    },
    'Android Nexus10 Perf': {
      'perf_id': 'android-nexus10',
      'bucket': 'chrome-perf',
      'path': lambda api: ('android_perf_rel/full-build-linux_%s.zip' %
                           api.properties['parent_revision']),
      'num_device_shards': 8,
    },
    'Android MotoE Perf': {
      'perf_id': 'android-motoe',
      'bucket': 'chrome-perf',
      'path': lambda api: ('android_perf_rel/full-build-linux_%s.zip' %
                           api.properties['parent_revision']),
      'num_device_shards': 8,
    },
  },
  'client.v8': {
    'Android Nexus4 Perf': {
      'gclient_apply_config': [
        'v8_bleeding_edge_git',
        'chromium_lkcr',
        'show_v8_revision',
      ],
      'perf_id': 'v8-android-nexus4',
      'bucket': 'v8-android',
      'path': lambda api: ('v8_android_perf_rel/full-build-linux_%s.zip' %
                           api.properties['parent_revision']),
      'num_device_shards': 1,
      'set_component_rev': {'name': 'src/v8', 'rev_str': '%s'},
    },
  },
}

def GenSteps(api):
  mastername = api.properties['mastername']
  buildername = api.properties['buildername']
  builder = BUILDERS[mastername][buildername]
  api.chromium_android.configure_from_properties('base_config',
                                                 REPO_NAME='src',
                                                 REPO_URL=REPO_URL,
                                                 INTERNAL=False,
                                                 BUILD_CONFIG='Release')
  api.gclient.set_config('perf')
  api.gclient.apply_config('android')
  for c in builder.get('gclient_apply_config', []):
    api.gclient.apply_config(c)

  if builder.get('set_component_rev'):
    # If this is a component build and the main revision is e.g. blink,
    # webrtc, or v8, the custom deps revision of this component must be
    # dynamically set to either:
    # (1) the revision of the builder,
    # (2) 'revision' from the waterfall, or
    # (3) 'HEAD' for forced builds with unspecified 'revision'.
    # TODO(machenbach): Use parent_got_cr_revision on testers with component
    # builds to match also the chromium revision from the builder.
    component_rev = api.properties.get(
        'parent_got_revision', api.properties.get('revision') or 'HEAD')
    dep = builder.get('set_component_rev')
    api.gclient.c.revisions[dep['name']] = dep['rev_str'] % component_rev

  api.bot_update.ensure_checkout()
  api.path['checkout'] = api.path['slave_build'].join('src')
  api.chromium_android.clean_local_files()

  api.chromium_android.download_build(bucket=builder['bucket'],
    path=builder['path'](api))

  api.chromium_android.common_tests_setup_steps()

  api.chromium_android.adb_install_apk(
      'ChromeShell.apk',
      'org.chromium.chrome.shell')

  perf_tests = api.chromium.list_perf_tests(
      browser='android-chrome-shell',
      num_shards=builder['num_device_shards'],
      devices=api.chromium_android.devices[0:1]).json.output

  try:
    api.chromium_android.run_sharded_perf_tests(
      config=api.json.input(data=perf_tests),
      perf_id=builder['perf_id'],
      chartjson_file=True)

  finally:
    api.chromium_android.common_tests_final_steps()

def _sanitize_nonalpha(text):
  return ''.join(c if c.isalnum() else '_' for c in text)

def GenTests(api):
  for mastername, builders in BUILDERS.iteritems():
    for buildername in builders:
      yield (
          api.test('full_%s_%s' % (_sanitize_nonalpha(mastername),
                                   _sanitize_nonalpha(buildername))) +
          api.properties.generic(
              repo_name='src',
              repo_url=REPO_URL,
              mastername=mastername,
              buildername=buildername,
              parent_buildername='parent_buildername',
              parent_buildnumber='1729',
              parent_revision='deadbeef',
              revision='deadbeef',
              slavename='slavename',
              target='Release'))
  yield (api.test('provision_devices') +
      api.properties.generic(
          repo_name='src',
              repo_url=REPO_URL,
              mastername='chromium.perf',
              buildername='Android Nexus5 Perf',
              parent_buildername='parent_buildername',
              parent_buildnumber='1729',
              parent_revision='deadbeef',
              revision='deadbeef',
              slavename='slavename',
              target='Release')
      + api.step_data('provision_devices', retcode=1))
