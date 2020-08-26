# Copyright (C) 2018 Philipp Hörist <philipp AT hoerist.com>
#
# This file is part of nbxmpp.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 3
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; If not, see <http://www.gnu.org/licenses/>.

from nbxmpp.namespaces import Namespace
from nbxmpp.protocol import Node
from nbxmpp.protocol import NodeProcessed
from nbxmpp.structs import StanzaHandler
from nbxmpp.structs import MoodData
from nbxmpp.const import MOODS
from nbxmpp.modules.base import BaseModule


class Mood(BaseModule):
    def __init__(self, client):
        BaseModule.__init__(self, client)

        self._client = client
        self.handlers = [
            StanzaHandler(name='message',
                          callback=self._process_pubsub_mood,
                          ns=Namespace.PUBSUB_EVENT,
                          priority=16),
        ]

    def _process_pubsub_mood(self, _client, stanza, properties):
        if not properties.is_pubsub_event:
            return

        if properties.pubsub_event.node != Namespace.MOOD:
            return

        item = properties.pubsub_event.item
        if item is None:
            # Retract, Deleted or Purged
            return

        mood_node = item.getTag('mood', namespace=Namespace.MOOD)
        if not mood_node.getChildren():
            self._log.info('Received mood: %s - removed mood', properties.jid)
            return

        mood, text = None, None
        for child in mood_node.getChildren():
            name = child.getName().strip()
            if name == 'text':
                text = child.getData()
            elif name in MOODS:
                mood = name

        if mood is None and mood_node.getPayload():
            self._log.warning('No valid mood value found')
            self._log.warning(stanza)
            raise NodeProcessed

        data = MoodData(mood, text)
        pubsub_event = properties.pubsub_event._replace(data=data)
        self._log.info('Received mood: %s - %s', properties.jid, data)

        properties.pubsub_event = pubsub_event

    def set_mood(self, data):
        item = Node('mood', {'xmlns': Namespace.MOOD})
        if data is not None and data.mood:
            item.addChild(data.mood)

            if data.text:
                item.addChild('text', payload=data.text)

        jid = self._client.get_bound_jid().bare
        self._client.get_module('PubSub').publish(
            jid, Namespace.MOOD, item, id_='current')
