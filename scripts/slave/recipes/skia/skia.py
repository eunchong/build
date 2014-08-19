# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


# Recipe module for Skia builders.


DEPS = [
  'path',
  'properties',
  'raw_io',
  'skia',
]


def GenSteps(api):
  api.skia.gen_steps()


def GenTests(api):
  mastername = 'client.skia'
  slavename = 'skiabot-linux-tester-004'
  builders = [
    'Build-Ubuntu13.10-GCC4.8-x86_64-Debug',
    'Perf-ChromeOS-Daisy-MaliT604-Arm7-Release',
    'Test-Android-GalaxyNexus-SGX540-Arm7-Debug',
    'Test-Android-Nexus10-MaliT604-Arm7-Release',
    'Test-Android-Xoom-Tegra2-Arm7-Release',
    'Test-ChromeOS-Alex-GMA3150-x86-Debug',
    'Test-Mac10.8-MacMini4.1-GeForce320M-x86_64-Debug',
    'Test-Ubuntu12-ShuttleA-GTX550Ti-x86_64-Release-Valgrind',
    'Test-Ubuntu12-ShuttleA-GTX550Ti-x86_64-Debug-ZeroGPUCache',
    'Test-Ubuntu13.10-ShuttleA-NoGPU-x86_64-Debug-Recipes',
    'Test-Ubuntu13.10-GCE-NoGPU-x86_64-Release-TSAN',
    'Test-Win7-ShuttleA-HD2000-x86-Release',
    'Test-Win7-ShuttleA-HD2000-x86-Release-ANGLE',
  ]

  def AndroidTestData(builder):
    return (
        api.step_data(
            'get EXTERNAL_STORAGE dir',
            stdout=api.raw_io.output('/storage/emulated/legacy')) +
        api.step_data(
            'exists /storage/emulated/legacy/skiabot/skia_skp/skps',
            stdout=api.raw_io.output('')) +
        api.step_data(
            'exists /storage/emulated/legacy/skiabot/skia_resources',
            stdout=api.raw_io.output('')) +
        api.step_data(
            'exists /storage/emulated/legacy/skiabot/skia_gm_actual',
            stdout=api.raw_io.output('')) +
        api.step_data(
            ('exists /storage/emulated/legacy/skiabot/skia_gm_expected/' +
             builder + '/expected-results.json'),
            stdout=api.raw_io.output('')) +
        api.step_data(
            ('exists /storage/emulated/legacy/skiabot/skia_gm_expected/'
             'ignored-tests.txt'),
            stdout=api.raw_io.output('')) +
        api.step_data('exists /storage/emulated/legacy/skiabot/skia_skimage_in',
                      stdout=api.raw_io.output('')) +
        api.step_data(
            'exists /storage/emulated/legacy/skiabot/skia_skimage_out/images',
            stdout=api.raw_io.output('')) +
        api.step_data(
            'exists /storage/emulated/legacy/skiabot/skia_skimage_out/%s' %
                 builder,
            stdout=api.raw_io.output('')) +
        api.step_data(
            'exists /storage/emulated/legacy/skiabot/skia_skimage_expected',
            stdout=api.raw_io.output(''))
    )

  for builder in builders:
    test = (
      api.test(builder) +
      api.properties(buildername=builder,
                     mastername=mastername,
                     slavename=slavename) +
      api.path.exists(
          api.path['slave_build'].join(
              'skia', 'expectations', 'gm',
              'Test-Ubuntu13.10-ShuttleA-NoGPU-x86_64-Debug-Recipes',
              'expected-results.json'),
          api.path['slave_build'].join('skia', 'expectations', 'gm',
                                       'ignored-tests.txt'),
          api.path['slave_build'].join('skia', 'expectations', 'skimage',
                                       builder, 'expected-results.json'),
          api.path['slave_build'].join('playback', 'skps', 'SKP_VERSION')
      )
    )
    if 'Android' in builder or 'NaCl' in builder:
      test += api.step_data('has ccache?', retcode=1)
    if 'Android' in builder:
      test += AndroidTestData(builder)
    yield test

  builder = 'Test-Ubuntu13.10-ShuttleA-NoGPU-x86_64-Debug-Recipes'
  yield (
    api.test('failed_gm') +
    api.properties(buildername=builder,
                   mastername=mastername,
                   slavename=slavename) +
    api.path.exists(
        api.path['slave_build'].join('skia', 'expectations', 'skimage',
                                     builder, 'expected-results.json')
    ) +
    api.step_data('gm', retcode=1)
  )

  yield (
    api.test('has_ccache_android') +
    api.properties(buildername='Build-Ubuntu13.10-GCC4.8-Arm7-Debug-Android',
                   mastername=mastername,
                   slavename=slavename) +
    api.step_data('has ccache?', retcode=0,
                  stdout=api.raw_io.output('/usr/bin/ccache'))
  )

  yield (
    api.test('has_ccache_nacl') +
    api.properties(buildername='Build-Ubuntu13.10-GCC4.8-NaCl-Debug',
                   mastername=mastername,
                   slavename=slavename) +
    api.step_data('has ccache?', retcode=0,
                  stdout=api.raw_io.output('/usr/bin/ccache'))
  )

  yield (
    api.test('no_skimage_expectations') +
    api.properties(buildername=builder,
                   mastername=mastername,
                   slavename=slavename) +
    api.step_data('assert skimage expectations', retcode=1)
  )
