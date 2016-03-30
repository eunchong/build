# Copyright 2016 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


# Recipe module for Skia Swarming trigger.


import json


DEPS = [
  'depot_tools/gclient',
  'depot_tools/git',
  'depot_tools/tryserver',
  'file',
  'recipe_engine/path',
  'recipe_engine/properties',
  'recipe_engine/python',
  'recipe_engine/raw_io',
  'skia',
  'skia_swarming',
]


TEST_BUILDERS = {
  'client.skia.fyi': {
    'skiabot-linux-housekeeper-003': [
      'Build-Ubuntu-GCC-x86_64-Debug-Swarming',
      'Test-Mac-Clang-MacMini6.2-CPU-AVX-x86_64-Release-Swarming',
      'Perf-Ubuntu-GCC-GCE-CPU-AVX2-x86_64-Release-Swarming-Trybot',
      'Test-Ubuntu-GCC-GCE-CPU-AVX2-x86_64-Debug-Swarming',
      'Test-Win8-MSVC-ShuttleB-CPU-AVX2-x86_64-Release-Swarming',
    ],
  },
}


def derive_compile_bot_name(builder_name, builder_cfg):
  if builder_cfg['role'] in ('Test', 'Perf'):
    os = builder_cfg['os']
    extra_config = builder_cfg.get('extra_config')
    if os in ('Android', 'ChromeOS'):  # pragma:nocover
      extra_config = os
      os = 'Ubuntu'
    elif os == 'iOS':  # pragma: nocover
      extra_config = os
      os = 'OSX'
    builder_name = 'Build-%s-%s-%s-%s' % (
      os,
      builder_cfg['compiler'],
      builder_cfg['arch'],
      builder_cfg['configuration']
    )
    if extra_config:
      builder_name += '-%s' % extra_config
  return builder_name


def swarm_dimensions(builder_cfg):
  """Return a dict of keys and values to be used as Swarming bot dimensions."""
  dimensions = {
    'pool': 'Skia',
  }
  dimensions['os'] = builder_cfg['os']
  if 'Win' in builder_cfg['os']:
    dimensions['os'] = 'Windows'  # pragma: no cover
  if builder_cfg['role'] in ('Test', 'Perf'):
    if builder_cfg['cpu_or_gpu'] == 'CPU':
      dimensions['gpu'] = 'none'
      # TODO(borenet): Add appropriate CPU dimension(s).
      #dimensions['cpu'] = builder_cfg['cpu_or_gpu_value']
    else:  # pragma: no cover
      dimensions['gpu'] = builder_cfg['cpu_or_gpu_value']
  else:
    dimensions['gpu'] = 'none'
  return dimensions


def isolate_recipes(api):
  """Isolate the recipes."""
  skia_recipes_dir = api.path['build'].join(
      'scripts', 'slave', 'recipes', 'skia')
  api.skia_swarming.create_isolated_gen_json(
      skia_recipes_dir.join('recipes.isolate'),
      skia_recipes_dir,
      'linux',
      'isolate_recipes',
      {})
  return api.skia_swarming.batcharchive(['isolate_recipes'])[0][1]


def trigger_task(api, task_name, builder, builder_cfg, got_revision,
                 infrabots_dir, idempotent=False, store_output=True,
                 extra_isolate_hashes=None):
  """Trigger the given bot to run as a Swarming task."""
  # TODO(borenet): We're using Swarming directly to run the recipe through
  # recipes.py. Once it's possible to track the state of a Buildbucket build,
  # we should switch to use the trigger recipe module instead.

  properties = {
    'buildername': builder,
    'mastername': api.properties['mastername'],
    'buildnumber': api.properties['buildnumber'],
    'reason': 'Triggered by Skia swarm_trigger Recipe',
    'revision': got_revision,
    'slavename': api.properties['slavename'],
    'swarm_out_dir': '${ISOLATED_OUTDIR}',
  }
  if builder_cfg['is_trybot']:
    properties['issue'] = str(api.properties['issue'])
    properties['patchset'] = str(api.properties['patchset'])
    properties['rietveld'] = api.properties['rietveld']

  extra_args = [
      '--workdir', '../../..',
      'skia/swarm_%s' % task_name,
  ]
  for k, v in properties.iteritems():
    extra_args.append('%s=%s' % (k, v))

  isolate_base_dir = api.path['slave_build']
  dimensions = swarm_dimensions(builder_cfg)
  isolate_blacklist = ['.git', 'out', '*.pyc']
  isolate_vars = {
    'BUILD': api.path['build'],
    'WORKDIR': api.path['slave_build'],
  }

  return api.skia_swarming.isolate_and_trigger_task(
      infrabots_dir.join('%s_skia.isolate' % task_name),
      isolate_base_dir,
      '%s_skia' % task_name,
      isolate_vars,
      dimensions,
      isolate_blacklist=isolate_blacklist,
      extra_isolate_hashes=extra_isolate_hashes,
      idempotent=idempotent,
      store_output=store_output,
      extra_args=extra_args)


def checkout_steps(api):
  """Run the steps to obtain a checkout of Skia."""
  gclient_cfg = api.gclient.make_config(CACHE_DIR=None)
  skia = gclient_cfg.solutions.add()
  skia.name = 'skia'
  skia.managed = False
  skia.url = 'https://skia.googlesource.com/skia.git'
  skia.revision = api.properties.get('revision') or 'origin/master'
  api.skia.update_repo(skia)

  # Run 'gclient sync'.
  gclient_cfg.got_revision_mapping['skia'] = 'got_revision'
  gclient_cfg.target_os.add('llvm')
  update_step = api.gclient.checkout(gclient_config=gclient_cfg)

  got_revision = update_step.presentation.properties['got_revision']
  api.tryserver.maybe_apply_issue()
  return got_revision


def compile_steps_swarm(api, builder_cfg, got_revision, infrabots_dir,
                        extra_isolate_hashes):
  builder_name = derive_compile_bot_name(api.properties['buildername'],
                                         builder_cfg)
  # Windows bots require a toolchain.
  extra_hashes = extra_isolate_hashes[:]
  if 'Win' in builder_name:
    test_data = '''{
  "2013": "705384d88f80da637eb367e5acc6f315c0e1db2f",
  "2015": "38380d77eec9164e5818ae45e2915a6f22d60e85"
}'''
    hash_file = infrabots_dir.join('win_toolchain_hash.json')
    j = api.skia._readfile(hash_file,
                           name='Read win_toolchain_hash.json',
                           test_data=test_data).rstrip()
    hashes = json.loads(j)
    extra_hashes.append(hashes['2013'])

  task = trigger_task(
      api,
      'compile',
      builder_name,
      builder_cfg,
      got_revision,
      infrabots_dir,
      idempotent=True,
      store_output=False,
      extra_isolate_hashes=extra_hashes)

  # Wait for compile to finish, record the results hash.
  return api.skia_swarming.collect_swarming_task_isolate_hash(task)


def download_images(api, infrabots_dir):
  api.python('Download images',
             script=infrabots_dir.join('download_images.py'),
             env=api.skia.gsutil_env('chromium-skia-gm.boto'))


def download_skps(api, infrabots_dir):
  api.python('Download SKPs',
             script=infrabots_dir.join('download_skps.py'),
             env=api.skia.gsutil_env('chromium-skia-gm.boto'))


def perf_steps_trigger(api, builder_cfg, got_revision, infrabots_dir,
                       extra_hashes):
  """Trigger perf tests via Swarming."""
  return trigger_task(
      api,
      'perf',
      api.properties['buildername'],
      builder_cfg,
      got_revision,
      infrabots_dir,
      extra_isolate_hashes=extra_hashes)


def perf_steps_collect(api, task, upload_perf_results, got_revision,
                       is_trybot):
  """Wait for perf steps to finish and upload results."""
  # Wait for nanobench to finish, download the results.
  api.file.rmtree('results_dir', task.task_output_dir, infra_step=True)
  api.skia_swarming.collect_swarming_task(task)

  # Upload the results.
  if upload_perf_results:
    perf_data_dir = api.path['slave_build'].join(
        'perfdata', api.properties['buildername'], 'data')
    git_timestamp = api.git.get_timestamp(test_data='1408633190',
                                          infra_step=True)
    api.file.rmtree('perf_dir', perf_data_dir, infra_step=True)
    api.file.makedirs('perf_dir', perf_data_dir, infra_step=True)
    src_results_file = task.task_output_dir.join(
        '0', 'perfdata', api.properties['buildername'], 'data',
        'nanobench_%s.json' % got_revision)
    dst_results_file = perf_data_dir.join(
        'nanobench_%s_%s.json' % (got_revision, git_timestamp))
    api.file.copy('perf_results', src_results_file, dst_results_file,
                  infra_step=True)

    gsutil_path = api.path['depot_tools'].join(
        'third_party', 'gsutil', 'gsutil')
    upload_args = [api.properties['buildername'], api.properties['buildnumber'],
                   perf_data_dir, got_revision, gsutil_path]
    if is_trybot:
      upload_args.append(api.properties['issue'])
    api.python(
             'Upload perf results',
             script=api.skia.resource('upload_bench_results.py'),
             args=upload_args,
             cwd=api.path['checkout'],
             env=api.skia.gsutil_env('chromium-skia-gm.boto'),
             infra_step=True)


def test_steps_trigger(api, builder_cfg, got_revision, infrabots_dir,
                       extra_hashes):
  """Trigger DM via Swarming."""
  return trigger_task(
      api,
      'test',
      api.properties['buildername'],
      builder_cfg,
      got_revision,
      infrabots_dir,
      extra_isolate_hashes=extra_hashes)


def test_steps_collect(api, task, upload_dm_results, got_revision, is_trybot):
  """Collect the DM results from Swarming."""
  # Wait for tests to finish, download the results.
  api.file.rmtree('results_dir', task.task_output_dir, infra_step=True)
  api.skia_swarming.collect_swarming_task(task)

  # Upload the results.
  if upload_dm_results:
    dm_dir = api.path['slave_build'].join('dm')
    dm_src = task.task_output_dir.join('0', 'dm')
    api.file.rmtree('dm_dir', dm_dir, infra_step=True)
    api.file.copytree('dm_dir', dm_src, dm_dir, infra_step=True)

    # Upload them to Google Storage.
    api.python(
        'Upload DM Results',
        script=api.skia.resource('upload_dm_results.py'),
        args=[
          dm_dir,
          got_revision,
          api.properties['buildername'],
          api.properties['buildnumber'],
          api.properties['issue'] if is_trybot else '',
          api.path['slave_build'].join('skia', 'common', 'py', 'utils'),
        ],
        cwd=api.path['checkout'],
        env=api.skia.gsutil_env('chromium-skia-gm.boto'),
        infra_step=True)


def RunSteps(api):
  got_revision = checkout_steps(api)
  builder_spec = api.skia.get_builder_spec(api.path['checkout'],
                                           api.properties['buildername'])
  builder_cfg = builder_spec['builder_cfg']
  infrabots_dir = api.path['checkout'].join('infra', 'bots')

  api.skia_swarming.setup(
      api.path['checkout'].join('infra', 'bots', 'tools', 'luci-go'),
      swarming_rev='')

  recipes_hash = isolate_recipes(api)

  compile_hash = compile_steps_swarm(api, builder_cfg, got_revision,
                                     infrabots_dir, [recipes_hash])
  extra_hashes = [recipes_hash, compile_hash]

  do_test_steps = builder_spec['do_test_steps']
  do_perf_steps = builder_spec['do_perf_steps']

  if not (do_test_steps or do_perf_steps):
    return

  download_skps(api, infrabots_dir)
  download_images(api, infrabots_dir)

  test_task = None
  perf_task = None
  if do_test_steps:
    test_task = test_steps_trigger(api, builder_cfg, got_revision,
                                   infrabots_dir, extra_hashes)
  if do_perf_steps:
    perf_task = perf_steps_trigger(api, builder_cfg, got_revision,
                                   infrabots_dir, extra_hashes)
  is_trybot = builder_cfg['is_trybot']
  if test_task:
    test_steps_collect(api, test_task, builder_spec['upload_dm_results'],
                       got_revision, is_trybot)
  if perf_task:
    perf_steps_collect(api, perf_task, builder_spec['upload_perf_results'],
                       got_revision, is_trybot)


def GenTests(api):
  for mastername, slaves in TEST_BUILDERS.iteritems():
    for slavename, builders_by_slave in slaves.iteritems():
      for builder in builders_by_slave:
        test = (
          api.test(builder) +
          api.properties(buildername=builder,
                         mastername=mastername,
                         slavename=slavename,
                         buildnumber=5,
                         revision='abc123') +
          api.path.exists(
              api.path['slave_build'].join('skia'),
              api.path['slave_build'].join('tmp', 'uninteresting_hashes.txt')
          )
        )
        if 'Trybot' in builder:
          test += api.properties(issue=500,
                                 patchset=1,
                                 rietveld='https://codereview.chromium.org')
        test += api.step_data(
            'upload new .isolated file for compile_skia',
            stdout=api.raw_io.output('def456 XYZ.isolated'))
        if 'Test' in builder:
          test += api.step_data(
              'upload new .isolated file for test_skia',
              stdout=api.raw_io.output('def456 XYZ.isolated'))
        if ('Test' in builder and 'Debug' in builder) or 'Perf' in builder:
          test += api.step_data(
              'upload new .isolated file for perf_skia',
              stdout=api.raw_io.output('def456 XYZ.isolated'))

        yield test
