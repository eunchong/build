# Copyright 2014 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'cronet',
  'path',
  'properties',
]

BUILDERS = {
  'local_test': {
    'recipe_config': 'main_builder',
    'run_tests': True,
    'upload_package': True,
    'kwargs': {
      'BUILD_CONFIG': 'Debug',
      'REPO_URL': 'https://chromium.googlesource.com/chromium/src.git',
      'REPO_NAME': 'src',
    },
    'custom': {
      'deps_file': '.DEPS.git'
    },
    'gyp_defs': {
      'use_goma': 0,
    }
  },
  'Android Cronet Builder (dbg)': {
    'recipe_config': 'main_builder',
    'run_tests': True,
    'upload_package': True,
    'kwargs': {
      'BUILD_CONFIG': 'Debug',
    },
    'custom': {
      'deps_file': 'DEPS'
    },
  },
  'Android Cronet Builder': {
    'recipe_config': 'main_builder',
    'run_tests': False,
    'upload_package': True,
    'kwargs': {
      'BUILD_CONFIG': 'Release',
    },
    'custom': {
      'deps_file': 'DEPS'
    },
  },
  'Android Cronet ARMv6 Builder': {
    'recipe_config': 'main_builder',
    'run_tests': False,
    'upload_package': True,
    'kwargs': {
      'BUILD_CONFIG': 'Release',
    },
    'custom': {
      'deps_file': 'DEPS'
    },
    'gyp_defs': {
      'arm_version': 6
    }
  },
  'Android Cronet x86 Builder': {
    'recipe_config': 'x86_builder',
    'run_tests': False,
    'upload_package': True,
    'kwargs': {
      'BUILD_CONFIG': 'Release',
    },
    'custom': {
      'deps_file': 'DEPS'
    },
  },
  'Android Cronet MIPS Builder': {
    'recipe_config': 'mipsel_builder',
    'run_tests': False,
    'upload_package': True,
    'kwargs': {
      'BUILD_CONFIG': 'Release',
    },
    'custom': {
      'deps_file': 'DEPS'
    },
  },
}

def GenSteps(api):
  buildername = api.properties['buildername']
  builder_config = BUILDERS.get(buildername, {})
  recipe_config = builder_config['recipe_config']
  kwargs = builder_config.get('kwargs', {})
  custom = builder_config.get('custom', {})
  gyp_defs = builder_config.get('gyp_defs', {})

  cronet = api.cronet
  cronet.init_and_sync(recipe_config, kwargs, custom, gyp_defs)
  cronet.clean_and_build()

  if builder_config['upload_package']:
    api.cronet.upload_package(kwargs['BUILD_CONFIG'])

  if builder_config['run_tests']:
    api.cronet.run_tests()

def _sanitize_nonalpha(text):
  return ''.join(c if c.isalnum() else '_' for c in text.lower())

def GenTests(api):
  bot_ids = ['local_test', 'Android Cronet Builder (dbg)',
      'Android Cronet Builder', 'Android Cronet ARMv6 Builder',
      'Android Cronet MIPS Builder', 'Android Cronet x86 Builder']

  for bot_id in bot_ids:
    props = api.properties.generic(
      buildername=bot_id,
      revision='4f4b02f6b7fa20a3a25682c457bbc8ad589c8a00',
      repository='svn://svn-mirror.golo.chromium.org/chrome/trunk',
      branch='src',
    )
    yield api.test(_sanitize_nonalpha(bot_id)) + props
