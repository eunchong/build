#!/usr/bin/env python
# Copyright (c) 2012 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

""" Initialize the environment variables and start the buildbot slave.
"""

import os
import shutil
import subprocess
import sys

SCRIPT_PATH = os.path.dirname(os.path.abspath(__file__))


def remove_all_vars_except(dictionary, keep):
  """Remove all keys from the specified dictionary except those in !keep|"""
  for key in set(dictionary.keys()) - set(keep):
    dictionary.pop(key)


def Reboot():
  print "Rebooting..."
  if sys.platform.startswith('win'):
    subprocess.call(['shutdown', '-r', '-f', '-t', '1'])
  elif sys.platform in ('darwin', 'posix', 'linux2'):
    subprocess.call(['sudo', 'shutdown', '-r', 'now'])
  else:
    raise NotImplementedError('Implement Reboot function')


def HotPatchSlaveBuilder():
  """We could override the SlaveBuilder class but it's way simpler to just
  hotpatch it."""
  # pylint: disable=E0611,F0401
  try:
    # buildbot 0.7.12
    from buildbot.slave.bot import log, Bot, SlaveBuilder
  except ImportError:
    # buildbot 0.8.x
    from buildslave.bot import log, Bot, SlaveBuilder
  old_remote_shutdown = SlaveBuilder.remote_shutdown

  def rebooting_remote_shutdown(self):
    old_remote_shutdown(self)
    Reboot()

  SlaveBuilder.remote_shutdown = rebooting_remote_shutdown

  Bot.old_remote_setBuilderList = Bot.remote_setBuilderList
  def cleanup(self, wanted):
    retval = self.old_remote_setBuilderList(wanted)
    wanted_dirs = ['info', 'cert', '.svn'] + [r[1] for r in wanted]
    for d in os.listdir(self.basedir):
      if d not in wanted_dirs and os.path.isdir(os.path.join(self.basedir, d)):
        log.msg("Deleting unwanted directory %s" % d)
        from common import chromium_utils
        chromium_utils.RemoveDirectory(os.path.join(self.basedir, d))
    return retval
  Bot.new_remote_setBuilderList = cleanup
  Bot.remote_setBuilderList = Bot.new_remote_setBuilderList


def FixSubversionConfig():
  if sys.platform == 'win32':
    dest = os.path.join(os.environ['APPDATA'], 'Subversion', 'config')
  else:
    dest = os.path.join(os.environ['HOME'], '.subversion', 'config')
  shutil.copyfile('config', dest)


def error(msg):
  print >> sys.stderr, msg
  sys.exit(1)


def main():
  # Use adhoc argument parsing because of twisted's twisted argument parsing.
  use_buildbot_8 = False
  if '--use_buildbot_8' in sys.argv:
    sys.argv.remove('--use_buildbot_8')
    use_buildbot_8 = True

  # Change the current directory to the directory of the script.
  os.chdir(SCRIPT_PATH)
  build_dir = os.path.dirname(SCRIPT_PATH)
  # Directory containing build/slave/run_slave.py
  root_dir = os.path.dirname(build_dir)
  depot_tools = os.path.join(root_dir, 'depot_tools')

  if not os.path.isdir(depot_tools):
    error('You must put a copy of depot_tools in %s' % depot_tools)
  bot_password_file = os.path.normpath(
      os.path.join(build_dir, 'site_config', '.bot_password'))
  if not os.path.isfile(bot_password_file):
    error('You forgot to put the password at %s' % bot_password_file)

  # Make sure the current python path is absolute.
  old_pythonpath = os.environ.get('PYTHONPATH', '')
  os.environ['PYTHONPATH']  = ''
  for path in old_pythonpath.split(os.pathsep):
    if path:
      os.environ['PYTHONPATH'] += os.path.abspath(path) + os.pathsep

  # Update the python path.
  python_path = [
    os.path.join(build_dir, 'site_config'),
    os.path.join(build_dir, 'scripts'),
    os.path.join(build_dir, 'scripts', 'release'),
    os.path.join(build_dir, 'third_party'),
    os.path.join(root_dir, 'build_internal', 'site_config'),
    os.path.join(root_dir, 'build_internal', 'symsrc'),
    SCRIPT_PATH,  # Include the current working directory by default.
  ]

  if use_buildbot_8:
    python_path.append(
        os.path.join(build_dir, 'third_party', 'buildbot_slave_8_4'))
    python_path.append(os.path.join(build_dir, 'third_party', 'twisted_10_2'))
  else:
    python_path.append(os.path.join(build_dir, 'third_party', 'buildbot_7_12'))
    python_path.append(os.path.join(build_dir, 'third_party', 'twisted_8_1'))

  os.environ['PYTHONPATH'] = (
      os.pathsep.join(python_path) + os.pathsep + os.environ['PYTHONPATH'])

  # Add these in from of the PATH too.
  sys.path = python_path + sys.path

  os.environ['CHROME_HEADLESS'] = '1'
  os.environ['PAGER'] = 'cat'

  # Platform-specific initialization.

  if sys.platform.startswith('win'):
    # list of all variables that we want to keep
    env_var = [
        'APPDATA',
        'BUILDBOT_ARCHIVE_FORCE_SSH',
        'CHROME_HEADLESS',
        'CHROMIUM_BUILD',
        'COMSPEC',
        'COMPUTERNAME',
        'DXSDK_DIR',
        'HOMEDRIVE',
        'HOMEPATH',
        'LOCALAPPDATA',
        'NUMBER_OF_PROCESSORS',
        'OS',
        'PATH',
        'PATHEXT',
        'PROCESSOR_ARCHITECTURE',
        'PROCESSOR_ARCHITEW6432',
        'PROGRAMFILES',
        'PROGRAMW6432',
        'PYTHONPATH',
        'SYSTEMDRIVE',
        'SYSTEMROOT',
        'TEMP',
        'TESTING_MASTER',
        'TESTING_MASTER_HOST',
        'TESTING_SLAVENAME',
        'TMP',
        'USERNAME',
        'USERDOMAIN',
        'USERPROFILE',
        'VS100COMNTOOLS',
        'WINDIR',
    ]

    remove_all_vars_except(os.environ, env_var)

    # Extend the env variables with the chrome-specific settings.
    slave_path = [
        depot_tools,
        # Reuse the python executable used to start this script.
        os.path.dirname(sys.executable),
        os.path.join(os.environ['SYSTEMROOT'], 'system32'),
        os.path.join(os.environ['SYSTEMROOT'], 'system32', 'WBEM'),
    ]
    # build_internal/tools contains tools we can't redistribute.
    tools = os.path.join(root_dir, 'build_internal', 'tools')
    if os.path.isdir(tools):
      slave_path.append(os.path.abspath(tools))
    os.environ['PATH'] = os.pathsep.join(slave_path)
    os.environ['LOGNAME'] = os.environ['USERNAME']

  elif sys.platform in ('darwin', 'posix', 'linux2'):
    # list of all variables that we want to keep
    env_var = [
        'CCACHE_DIR',
        'CHROME_ALLOCATOR',
        'CHROME_HEADLESS',
        'CHROME_VALGRIND_NUMCPUS',
        'DISPLAY',
        'DISTCC_DIR',
        'HOME',
        'HOSTNAME',
        'LANG',
        'LOGNAME',
        'PAGER',
        'PATH',
        'PWD',
        'PYTHONPATH',
        'SHELL',
        'SSH_AGENT_PID',
        'SSH_AUTH_SOCK',
        'SSH_CLIENT',
        'SSH_CONNECTION',
        'SSH_TTY',
        'TESTING_MASTER',
        'TESTING_MASTER_HOST',
        'TESTING_SLAVENAME',
        'USER',
        'USERNAME',
    ]

    remove_all_vars_except(os.environ, env_var)
    slave_path = [
        depot_tools,
        # Reuse the python executable used to start this script.
        os.path.dirname(sys.executable),
        '/usr/bin', '/bin', '/usr/sbin', '/sbin', '/usr/local/bin'
    ]
    os.environ['PATH'] = os.pathsep.join(slave_path)

  else:
    error('Platform %s is not implemented yet' % sys.platform)

  # This envrionment is defined only when testing the slave on a dev machine.
  if 'TESTING_MASTER' not in os.environ:
    # Don't overwrite the ~/.subversion/config file when TESTING_MASTER is set.
    FixSubversionConfig()
    # Do not reboot the workstation or delete unknown directories in the current
    # directory.
    HotPatchSlaveBuilder()

  import twisted.scripts.twistd as twistd
  twistd.run()


def UpdateScripts():
  if os.environ.get('RUN_SLAVE_UPDATED_SCRIPTS', None):
    os.environ.pop('RUN_SLAVE_UPDATED_SCRIPTS')
    return False
  gclient_path = os.path.join(SCRIPT_PATH, '..', '..', 'depot_tools', 'gclient')
  if sys.platform.startswith('win'):
    gclient_path += '.bat'
  if subprocess.call([gclient_path, 'sync']) != 0:
    msg = '(%s) `gclient sync` failed; proceeding anyway...' % sys.argv[0]
    print >> sys.stderr, msg
  os.environ['RUN_SLAVE_UPDATED_SCRIPTS'] = '1'
  return True


if '__main__' == __name__:
  if UpdateScripts():
    os.execv(sys.executable, [sys.executable] + sys.argv)
  main()
