import { getSocket } from './session.js';

export async function sendMessage(jid, text, quotedId = null) {
  const sock = getSocket();
  if (!sock) throw new Error('WhatsApp not connected');

  const content = { text };

  if (quotedId) {
    // Build quoted message context for WhatsApp quoting feature
    content.contextInfo = {
      stanzaId: quotedId,
      participant: jid,
      quotedMessage: { conversation: '' },
    };
  }

  await sock.sendMessage(jid, content);
}

export async function getGroups() {
  const sock = getSocket();
  if (!sock) return [];

  const groups = await sock.groupFetchAllParticipating();
  return Object.entries(groups).map(([id, meta]) => ({
    id,
    name: meta.subject || id,
    participantCount: meta.participants?.length || 0,
    description: meta.desc || null,
  }));
}

export async function leaveGroup(jid) {
  const sock = getSocket();
  if (!sock) throw new Error('WhatsApp not connected');
  await sock.groupLeave(jid);
}
