# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
Recipe for testing with the AndroidWebViewShell using system WebView.
"""

from infra.libs.infra_types import freeze

DEPS = [
  'adb',
  'bot_update',
  'chromium',
  'chromium_android',
  'gclient',
  'json',
  'path',
  'properties',
  'python',
  'step',
]

REPO_URL = 'https://chromium.googlesource.com/chromium/src.git'

WEBVIEW_APK = 'SystemWebView.apk'
WEBVIEW_PACKAGE = 'com.android.webview'

TELEMETRY_SHELL_APK = 'AndroidWebViewShell.apk'
TELEMETRY_SHELL_PACKAGE = 'org.chromium.webview_shell'

BUILDER = freeze({
  'perf_id': 'android-webview',
  'num_device_shards': 5,
})

def GenSteps(api):
  api.chromium_android.configure_from_properties('webview_perf',
                                                 REPO_NAME='src',
                                                 REPO_URL=REPO_URL,
                                                 INTERNAL=False,
                                                 BUILD_CONFIG='Release')

  # Sync code.
  api.gclient.set_config('perf')
  api.gclient.apply_config('android')
  api.bot_update.ensure_checkout(force=True)
  api.chromium_android.clean_local_files()

  # Gyp the chromium checkout.
  api.chromium.runhooks()

  # Build the WebView apk, WebView shell and Android testing tools.
  api.chromium.compile(targets=['system_webview_apk',
                                'android_webview_shell_apk',
                                'android_tools'])

  api.chromium_android.spawn_logcat_monitor()
  api.chromium_android.device_status_check()
  api.chromium_android.provision_devices(
      min_battery_level=95, disable_network=True, disable_java_debug=True,
      reboot_timeout=180)

  # Install WebView
  api.chromium_android.adb_install_apk(WEBVIEW_APK, WEBVIEW_PACKAGE)

  # Install the telemetry shell.
  api.chromium_android.adb_install_apk(TELEMETRY_SHELL_APK,
                                       TELEMETRY_SHELL_PACKAGE)

  # TODO: Run the tests here.
  api.adb.list_devices()

  api.chromium_android.logcat_dump()
  api.chromium_android.stack_tool_steps()
  api.chromium_android.test_report()

def GenTests(api):
  yield api.test('basic') + api.properties.scheduled()