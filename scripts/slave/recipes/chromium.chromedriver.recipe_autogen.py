# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

DEPS = [
  'bot_update',
  'chromium',
  'gclient',
  'recipe_engine/json',
  'recipe_engine/path',
  'recipe_engine/properties',
  'recipe_engine/python',
  'recipe_engine/step',
]

def Linux32_steps(api):
  # update scripts step; implicitly run by recipe engine.
  # bot_update step
  src_cfg = api.gclient.make_config(GIT_MODE=True)
  soln = src_cfg.solutions.add()
  soln.name = "src"
  soln.url = "https://chromium.googlesource.com/chromium/src.git"
  src_cfg.got_revision_mapping.update({'src': 'got_revision',
    'src/third_party/WebKit': 'got_webkit_revision',
    'src/tools/swarming_client': 'got_swarming_client_revision',
    'src/v8': 'got_v8_revision'})
  api.gclient.c = src_cfg
  api.bot_update.ensure_checkout(force=True)
  # gclient update step; made unnecessary by bot_update
  # gclient runhooks wrapper step
  env = {'CHROMIUM_GYP_SYNTAX_CHECK': '1', 'LANDMINES_VERBOSE': '1',
      'DEPOT_TOOLS_UPDATE': '0',
      'GYP_DEFINES':
      'branding=Chrome buildtype=Official component=static_library'}
  api.python("gclient runhooks wrapper", api.path["build"].join("scripts",
    "slave", "runhooks_wrapper.py"), env=env)
  # cleanup_temp step
  api.chromium.cleanup_temp()
  # chromedriver compile.py step
  api.python("compile", api.path["build"].join("scripts", "slave",
    "compile.py"), args=['--target', 'Release',
      'chromium_builder_chromedriver'])
  # annotated_steps step
  api.python("annotated_steps", api.path["build"].join("scripts", "slave",
    "chromium", "chromedriver_buildbot_run.py"),
    args=['--build-properties=%s' % api.json.dumps(api.properties.legacy(),
      separators=(',', ':')), '--factory-properties={"annotated_script":'+\
          '"chromedriver_buildbot_run.py","blink_config":"chromium",'+\
          '"gclient_env":{"CHROMIUM_GYP_SYNTAX_CHECK":"1",'+\
          '"DEPOT_TOOLS_UPDATE"'':"0","GYP_DEFINES":"branding=Chrome '+\
          'buildtype=Official component=static_library","LANDMINES_VERBOSE":'+\
          '"1"},"needs_webdriver_java_tests":true,"use_xvfb_on_linux":true}'],
    allow_subannotations=True)


def Mac_10_6_steps(api):
  # update scripts step; implicitly run by recipe engine.
  # bot_update step
  src_cfg = api.gclient.make_config(GIT_MODE=True)
  soln = src_cfg.solutions.add()
  soln.name = "src"
  soln.url = "https://chromium.googlesource.com/chromium/src.git"
  src_cfg.got_revision_mapping.update({'src': 'got_revision',
    'src/third_party/WebKit': 'got_webkit_revision',
    'src/tools/swarming_client': 'got_swarming_client_revision',
    'src/v8': 'got_v8_revision'})
  api.gclient.c = src_cfg
  api.bot_update.ensure_checkout(force=True)
  # gclient update step; made unnecessary by bot_update
  # gclient runhooks wrapper step
  env = {'CHROMIUM_GYP_SYNTAX_CHECK': '1', 'LANDMINES_VERBOSE': '1',
      'DEPOT_TOOLS_UPDATE': '0', 'GYP_DEFINES': ' component=static_library'}
  api.python("gclient runhooks wrapper", api.path["build"].join("scripts",
    "slave", "runhooks_wrapper.py"), env=env)
  # cleanup_temp step
  api.chromium.cleanup_temp()
  # chromedriver compile.py step
  api.python("compile", api.path["build"].join("scripts", "slave",
    "compile.py"), args=['--target', 'Release', '--', '-project',
      '../build/all.xcodeproj', '-target', 'chromium_builder_chromedriver'])
  # annotated_steps step
  api.python("annotated_steps", api.path["build"].join("scripts", "slave",
    "chromium", "chromedriver_buildbot_run.py"),
    args=['--build-properties=%s' % api.json.dumps(api.properties.legacy(),
      separators=(',', ':')), '--factory-properties={"annotated_script":"c'+\
          'hromedriver_buildbot_run.py","blink_config":"chromium","gclient_e'+\
          'nv":{"CHROMIUM_GYP_SYNTAX_CHECK":"1","DEPOT_TOOLS_UPDATE":"0","GYP'+\
          '_DEFINES":" component=static_library","LANDMINES_VERBOSE":"1"},"ne'+\
          'eds_webdriver_java_tests":true}'], allow_subannotations=True)


def Win7_steps(api):
  # update scripts step; implicitly run by recipe engine.
  # taskkill step
  api.python("taskkill", api.path["build"].join("scripts", "slave",
    "kill_processes.py"))
  # bot_update step
  src_cfg = api.gclient.make_config(GIT_MODE=True)
  soln = src_cfg.solutions.add()
  soln.name = "src"
  soln.url = "https://chromium.googlesource.com/chromium/src.git"
  src_cfg.got_revision_mapping.update({'src': 'got_revision',
    'src/third_party/WebKit': 'got_webkit_revision',
    'src/tools/swarming_client': 'got_swarming_client_revision',
    'src/v8': 'got_v8_revision'})
  api.gclient.c = src_cfg
  api.bot_update.ensure_checkout(force=True)
  # gclient update step; made unnecessary by bot_update
  # gclient runhooks wrapper step
  env = {'CHROMIUM_GYP_SYNTAX_CHECK': '1', 'LANDMINES_VERBOSE': '1',
      'DEPOT_TOOLS_UPDATE': '0','GYP_DEFINES': ' component=static_library'}
  api.python("gclient runhooks wrapper", api.path["build"].join("scripts",
    "slave", "runhooks_wrapper.py"), env=env)
  # cleanup_temp step
  api.chromium.cleanup_temp()
  # chromedriver compile.py step
  api.step("compile", ["python_slave", api.path["build"].join("scripts",
    "slave", "compile.py"), '--solution', 'all.sln', '--project',
    'chromium_builder_chromedriver', '--target', 'Release'])
  # annotated_steps step
  api.step("annotated_steps", ["python_slave", api.path["build"].join("scripts",
    "slave", "chromium", "chromedriver_buildbot_run.py"),
    '--build-properties=%s' % api.json.dumps(api.properties.legacy(),
      separators=(',', ':')), '--factory-properties={"annotated_script":"chro'+\
          'medriver_buildbot_run.py","blink_config":"chromium","gclient_env":'+\
          '{"CHROMIUM_GYP_SYNTAX_CHECK":"1","DEPOT_TOOLS_UPDATE":"0","GYP_DEF'+\
          'INES":" component=static_library","LANDMINES_VERBOSE":"1"},"needs_'+\
          'webdriver_java_tests":true}'], allow_subannotations=True)


def Linux_steps(api):
  # update scripts step; implicitly run by recipe engine.
  # bot_update step
  src_cfg = api.gclient.make_config(GIT_MODE=True)
  soln = src_cfg.solutions.add()
  soln.name = "src"
  soln.url = "https://chromium.googlesource.com/chromium/src.git"
  src_cfg.got_revision_mapping.update({'src': 'got_revision',
    'src/third_party/WebKit': 'got_webkit_revision',
    'src/tools/swarming_client': 'got_swarming_client_revision',
    'src/v8': 'got_v8_revision'})
  api.gclient.c = src_cfg
  api.bot_update.ensure_checkout(force=True)
  # gclient update step; made unnecessary by bot_update
  # gclient runhooks wrapper step
  env = {'CHROMIUM_GYP_SYNTAX_CHECK': '1', 'LANDMINES_VERBOSE': '1',
      'DEPOT_TOOLS_UPDATE': '0', 'GYP_DEFINES':
      'branding=Chrome buildtype=Official component=static_library'}
  api.python("gclient runhooks wrapper", api.path["build"].join("scripts",
    "slave", "runhooks_wrapper.py"), env=env)
  # cleanup_temp step
  api.chromium.cleanup_temp()
  # chromedriver compile.py step
  api.python("compile", api.path["build"].join("scripts", "slave",
    "compile.py"), args=['--target', 'Release',
      'chromium_builder_chromedriver'])
  # annotated_steps step
  api.python("annotated_steps", api.path["build"].join("scripts", "slave",
    "chromium", "chromedriver_buildbot_run.py"),
    args=['--build-properties=%s' % api.json.dumps(api.properties.legacy(),
      separators=(',', ':')), '--factory-properties={"annotated_script":"chro'+\
          'medriver_buildbot_run.py","blink_config":"chromium","gclient_env":'+\
          '{"CHROMIUM_GYP_SYNTAX_CHECK":"1","DEPOT_TOOLS_UPDATE":"0","GYP_DEF'+\
          'INES":"branding=Chrome buildtype=Official component=static_library'+\
          '","LANDMINES_VERBOSE":"1"},"needs_webdriver_java_tests":true,"use_'+\
          'xvfb_on_linux":true}'], allow_subannotations=True)


dispatch_directory = {
  'Linux32': Linux32_steps,
  'Mac 10.6': Mac_10_6_steps,
  'Win7': Win7_steps,
  'Linux': Linux_steps,
}


def RunSteps(api):
  if api.properties["buildername"] not in dispatch_directory:
    raise api.step.StepFailure("Builder unsupported by recipe.")
  else:
    dispatch_directory[api.properties["buildername"]](api)

def GenTests(api):
  yield (api.test('Linux32') +
    api.properties(mastername='chromium.chromedriver') +
    api.properties(buildername='Linux32') +
    api.properties(slavename='TestSlave')
        )
  yield (api.test('Mac_10_6') +
    api.properties(mastername='chromium.chromedriver') +
    api.properties(buildername='Mac 10.6') +
    api.properties(slavename='TestSlave')
        )
  yield (api.test('Win7') +
    api.properties(mastername='chromium.chromedriver') +
    api.properties(buildername='Win7') +
    api.properties(slavename='TestSlave')
        )
  yield (api.test('Linux') +
    api.properties(mastername='chromium.chromedriver') +
    api.properties(buildername='Linux') +
    api.properties(slavename='TestSlave')
        )
  yield (api.test('builder_not_in_dispatch_directory') +
    api.properties(mastername='chromium.chromedriver') +
    api.properties(buildername='nonexistent_builder') +
    api.properties(slavename='TestSlave')
        )
