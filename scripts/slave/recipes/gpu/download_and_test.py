# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# This recipe is intended to control all of the GPU testers on the
# following waterfalls:
#   chromium.gpu
#   chromium.gpu.fyi
#   chromium.webkit
#   tryserver.chromium.*
# These testers are triggered by the builders on the same waterfall.

DEPS = [
  'buildbot',
  'chromium',
  'gpu',
  'isolate',
  'json',
  'path',
  'platform',
  'properties',
  'raw_io',
  'step',
  'swarming',
  'swarming_client',
  'test_utils',
  'tryserver',
]

def GenSteps(api):
  api.gpu.setup()
  api.buildbot.prep()

  # The GPU recipes require the use of isolates for transmitting the
  # test binaries and data files from the builder to the tester. The
  # testers do not checkout the full Chromium tree; instead, the
  # swarming_client tools are checked out separately.
  api.swarming_client.checkout()
  api.chromium.get_vs_toolchain_if_necessary()
  api.buildbot.copy_parent_got_revision_to_got_revision()
  api.gpu.run_tests(api, api.gpu.get_build_revision(),
                    api.gpu.get_webkit_revision())

def GenTests(api):
  all_hashes = api.gpu.dummy_swarm_hashes
  props = lambda plat, flavor: api.properties.scheduled(
    mastername='chromium.gpu.testing',
    buildnumber=776,
    parent_buildnumber=571,
    parent_got_revision=160000,
    parent_got_webkit_revision=10000,
    parent_got_swarming_client_revision='feaaabcdef',
    # These would ordinarily be generated by the builder and passed
    # via build properties to the tester.
    swarm_hashes=all_hashes,
    # This is needed to achieve 100% coverage.
    master_class_name_for_testing='ChromiumGPUTesting',

    build_config=flavor,
    buildername='%s %s tester' % (plat, flavor.lower()),
    parent_buildername='%s %s builder' % (plat, flavor.lower()),
  )

  # The majority of the tests are in the build_and_test recipe.

  # Keep the additional properties in sync with the build_and_upload
  # recipe in order to catch regressions.
  for plat in ['win', 'mac', 'linux']:
    for flavor in ['Debug', 'Release']:
      flavor_lower = flavor.lower()
      yield (
        api.test('%s_%s' % (plat, flavor_lower)) +
        props(plat, flavor) +
        api.platform.name(plat)
      )

  yield (
    api.test('failures_keeps_going') +
    props('linux', 'Release') +
    api.platform.name('linux') +
    api.step_data('content_gl_tests', retcode=1) +
    api.step_data('maps_pixel_test', retcode=1)
  )

  # Tests that we only run the gpu_unittests isolate if that's all
  # that analyze said to rebuild.
  angle_unittests_hash = { x: all_hashes[x] for x in ['gpu_unittests'] }
  yield (
    api.test('analyze_runs_only_gpu_unittests') +
    api.properties.tryserver(
      mastername='tryserver.chromium.gpu',
      buildername='mac_gpu',
      parent_got_revision=160000,
      parent_got_webkit_revision=10000,
      parent_got_swarming_client_revision='feaaabcdef',
      swarm_hashes=angle_unittests_hash
    ) +
    api.platform.name('mac')
  )

  # Tests that we run nothing if analyze said we didn't have to run anything.
  yield (
    api.test('analyze_runs_nothing') +
    api.properties.tryserver(
      mastername='tryserver.chromium.gpu',
      buildername='mac_gpu',
      parent_got_revision=160000,
      parent_got_webkit_revision=10000,
      parent_got_swarming_client_revision='feaaabcdef',
      swarm_hashes={}
    ) +
    api.platform.name('mac')
  )

  # Tests that swarm_hashes='' doesn't throw an exception.
  yield (
    api.test('analyze_does_not_throw_exception') +
    api.properties.tryserver(
      mastername='tryserver.chromium.gpu',
      buildername='mac_gpu',
      parent_got_revision=160000,
      parent_got_webkit_revision=10000,
      parent_got_swarming_client_revision='feaaabcdef',
      swarm_hashes=''
    ) +
    api.platform.name('mac')
  )