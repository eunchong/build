# Copyright 2013 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import datetime

from buildbot.changes import base
from buildbot.util import deferredLocked
from twisted.python import log
from twisted.internet import defer

from common.gerrit_agent import GerritAgent


class GerritPoller(base.PollingChangeSource):
  """A poller which queries a gerrit server for new changes and patchsets."""

  change_category = 'patchset-created'

  def __init__(self, gerrit_host, gerrit_projects=None, pollInterval=None):
    if isinstance(gerrit_projects, basestring):
      gerrit_projects = [gerrit_projects]
    self.gerrit_projects = gerrit_projects
    if pollInterval:
      self.pollInterval = pollInterval
    self.initLock = defer.DeferredLock()
    self.last_timestamp = None
    self.agent = GerritAgent(gerrit_host)

  @staticmethod
  def _parse_timestamp(tm):
    tm = tm[:tm.index('.')+7]
    return datetime.datetime.strptime(tm, '%Y-%m-%d %H:%M:%S.%f')

  def startService(self):
    self.initLastTimeStamp()
    base.PollingChangeSource.startService(self)

  def getChangeQuery(self):  # pylint: disable=R0201
    return 'status:open'

  @deferredLocked('initLock')
  def initLastTimeStamp(self):
    log.msg('GerritPoller: Getting latest timestamp from gerrit server.')
    path = '/changes/?q=%s&n=1' % self.getChangeQuery()
    d = self.agent.request('GET', path)
    def _get_timestamp(j):
      if len(j) == 0:
        self.last_timestamp = datetime.datetime.now()
      else:
        self.last_timestamp = self._parse_timestamp(j[0]['updated'])
    d.addCallback(_get_timestamp)
    return d

  def getChanges(self, sortkey=None):
    path = '/changes/?q=%s&n=10' % self.getChangeQuery()
    if sortkey:
      path += '&N=%s' % sortkey
    return self.agent.request('GET', path)

  def _is_interesting_message(self, message):  # pylint: disable=R0201
    return message['message'].startswith('Uploaded patch set ')

  def checkForNewPatchset(self, change, since):
    o_params = '&'.join('o=%s' % x for x in (
        'MESSAGES', 'CURRENT_REVISION', 'CURRENT_COMMIT', 'ALL_FILES'))
    path = '/changes/%s?%s' % (change['_number'], o_params)
    d = self.agent.request('GET', path)
    def _parse_messages(j):
      if not j or 'messages' not in j:
        return
      for m in reversed(j['messages']):
        if self._parse_timestamp(m['date']) <= since:
          break
        if self._is_interesting_message(m):
          return j, m
    d.addCallback(_parse_messages)
    return d

  def getChangeUrl(self, change):
    """Generates a URL for a Gerrit change."""
    # GerritAgent stores its URL as protocol and host.
    return '%s://%s/#/c/%s' % (self.agent.gerrit_protocol,
                               self.agent.gerrit_host,
                               change['_number'])

  def addBuildbotChange(self, change, message):
    revision = change['revisions'].values()[0]
    commit = revision['commit']

    properties = {
        'event.change.number': change['_number'],
        'event.change.id': change['id'],
        'event.change.url': self.getChangeUrl(change),
    }
    if change['status'] == 'NEW':
      ref = revision.get('fetch', {}).get('http', {}).get('ref')
      if ref:
        properties['event.patchSet.ref'] = ref
    elif change['status'] in ('SUBMITTED', 'MERGED'):
      properties['event.refUpdate.newRev'] = change['current_revision']
    chdict = {
        'author': '%s <%s>' % (
            commit['author']['name'], commit['author']['email']),
        'project': change['project'],
        'branch': change['branch'],
        'revision': change['current_revision'],
        'comments': commit['subject'],
        'files': revision.get('files', {'UNKNOWN': None}).keys(),
        'category': self.change_category,
        'when_timestamp': self._parse_timestamp(commit['committer']['date']),
        'revlink': '%s://%s/#/c/%s' % (
            self.agent.gerrit_protocol, self.agent.gerrit_host,
            change['_number']),
        'repository': '%s://%s/%s' % (
            self.agent.gerrit_protocol, self.agent.gerrit_host,
            change['project']),
        'properties': properties,
    }
    d = self.master.addChange(**chdict)
    d.addErrback(log.err, 'GerritPoller: Could not add buildbot change for '
                 'gerrit change %s.' % revision['_number'])
    return d

  def addChange(self, change, message):
    return self.addBuildbotChange(change, message)

  def processChanges(self, j, since):
    need_more = bool(j)
    for change in j:
      tm = self._parse_timestamp(change['updated'])
      if tm <= since:
        need_more = False
        break
      if self.gerrit_projects and change['project'] not in self.gerrit_projects:
        continue
      d = self.checkForNewPatchset(change, since)
      d.addCallback(lambda x: self.addChange(*x) if x else None)
    if need_more and j[-1].get('_more_changes'):
      d = self.getChanges(sortkey=j[-1]['_sortkey'])
      d.addCallback(self.processChanges, since=since)
    else:
      d = defer.succeed(None)
    return d

  @deferredLocked('initLock')
  def poll(self):
    log.msg('GerritPoller: getting latest changes...')
    since = self.last_timestamp
    d = self.getChanges()
    def _update_last_timestamp(j):
      if j:
        self.last_timestamp = self._parse_timestamp(j[0]['updated'])
      return j
    d.addCallback(_update_last_timestamp)
    d.addCallback(self.processChanges, since=since)
    return d
