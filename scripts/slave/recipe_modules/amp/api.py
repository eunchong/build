# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from slave import recipe_api


class AmpApi(recipe_api.RecipeApi):

  def __init__(self, *args, **kwargs):
    super(AmpApi, self).__init__(*args, **kwargs)
    self._trigger_file_dir = None

  @recipe_api.non_step
  def _get_trigger_dir(self):
    if not self._trigger_file_dir:
      self._trigger_file_dir = self.m.path.mkdtemp('amp_trigger')
    return self._trigger_file_dir

  @recipe_api.non_step
  def _get_trigger_file_for_suite(self, suite):
    return self._get_trigger_dir().join('%s.json' % suite)

  @recipe_api.composite_step
  def trigger_test_suite(
      self, suite, test_type, test_type_args, amp_args, verbose=True):
    args = ([test_type] + test_type_args + amp_args
        + ['--trigger', self.m.json.output()])
    if verbose:
      args += ['--verbose']

    step_test_data = lambda: self.m.json.test_api.output({
      'env': {
        'device': {
          'brand': 'Foo',
          'name': 'Fone',
          'os_version': '1.2.3',
        },
      },
    })
    step_result = self.m.python(
        '[trigger] %s' % suite,
        self.m.path['checkout'].join('build', 'android', 'test_runner.py'),
        args=args,
        step_test_data=step_test_data)
    trigger_data = step_result.json.output
    try:
      device_data = trigger_data['env']['device']
      step_result.presentation.step_text = 'on %s %s %s' % (
          device_data['brand'],
          device_data['name'],
          device_data['os_version'])
    except KeyError:
      step_result.presentation.status = self.m.step.WARNING
      step_result.presentation.step_text = 'unable to find device info'

    self.m.file.write(
        '[trigger] save %s data' % suite,
        self._get_trigger_file_for_suite(suite),
        self.m.json.dumps(trigger_data))

  def collect_test_suite(
      self, suite, test_type, test_type_args, amp_args, verbose=True):
    args = ([test_type] + test_type_args + amp_args
        + ['--collect', self._get_trigger_file_for_suite(suite)])
    trigger_data = self.m.json.read(
        '[collect] load %s data' % suite,
        self._get_trigger_file_for_suite(suite),
        step_test_data=lambda: self.m.json.test_api.output({
          'env': {
            'device': {
              'brand': 'Foo',
              'name': 'Fone',
              'os_version': '1.2.3',
            }
          }
        })).json.output
    if verbose:
      args += ['--verbose']
    step_result = self.m.python(
        '[collect] %s' % suite,
        self.m.path['checkout'].join('build', 'android', 'test_runner.py'),
        args=args)
    try:
      device_data = trigger_data['env']['device']
      step_result.presentation.step_text = 'on %s %s %s' % (
          device_data['brand'],
          device_data['name'],
          device_data['os_version'])
    except KeyError:
      step_result.presentation.status = self.m.step.WARNING
      step_result.presentation.step_text = 'unable to find device info'

  @recipe_api.non_step
  def gtest_arguments(
      self, suite, isolate_file_path=None):
    """Generate command-line arguments for running gtests.

    Args:
      suite: The name of the test suite to run.
      isolate_file_path: The path to the .isolate file containing data
        dependency information for the test suite.

    Returns:
      A list of command-line arguments as strings.
    """
    gtest_args = ['-s', suite]
    if isolate_file_path:
      gtest_args += ['--isolate-file-path', isolate_file_path]
    return gtest_args

  @recipe_api.non_step
  def uirobot_arguments(self, app_under_test=None, minutes=5):
    """Generate command-line arguments for running uirobot tests.

    Args:
      app_under_test: The app to run uirobot tests on.
      minutes: The number of minutes for which the uirobot tests should be
        run. Defaults to 5.

    Returns:
      A list of command-line arguments as strings.
    """
    uirobot_args = ['--minutes', minutes]
    if app_under_test:
      uirobot_args += ['--app-under-test', app_under_test]
    return uirobot_args

  @recipe_api.non_step
  def amp_arguments(
      self, device_type='Android', device_name=None, device_os=None,
      api_address=None, api_port=None, api_protocol=None):
    """Generate command-line arguments for running tests on AMP.

    Args:
      device_name: The name of the device to use (e.g. 'Galaxy S4').
        Selects a device at random if unspecified.
      device_os: The OS version to use (e.g. '4.4.2'). Selects an OS version
        at random if unspecified.
      api_address: The IP address of the AMP API endpoint.
      api_port: The port of the AMP API endpoint.
      api_protocol: The protocol to use to connect to the AMP API endpoint.

    Returns:
      A list of command-line arguments as strings.
    """
    if not api_address:
      raise self.m.step.StepFailure('api_address not specified')
    if not api_port:
      raise self.m.step.StepFailure('api_port not specified')
    if not api_protocol:
      raise self.m.step.StepFailure('api_protocol not specified')

    amp_args = [
        '--enable-platform-mode',
        '-e', 'remote_device',
        '--api-key-file',
        self.m.path['build'].join('site_config', '.amp_api_key'),
        '--api-secret-file',
        self.m.path['build'].join('site_config', '.amp_api_secret'),
        '--api-address', api_address,
        '--api-port', api_port,
        '--api-protocol', api_protocol,
        '--device-type', device_type,
    ]
    if device_name:
      for d in device_name:
        amp_args += ['--remote-device', d]

    if device_os:
      for d in device_os:
        amp_args += ['--remote-device-os', d]

    return amp_args

