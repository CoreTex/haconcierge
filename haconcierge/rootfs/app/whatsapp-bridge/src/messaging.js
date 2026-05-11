import { getSocket, getConnectionState } from './session.js';

export async function sendMessage(jid, text, quotedId = null) {
  const sock = getSocket();
  if (!sock) throw new Error('WhatsApp not connected');

  const content = { text };
  if (quotedId) {
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
  const state = getConnectionState();
  // Guard: groupFetchAllParticipating hangs until timeout if not connected
  if (!sock || !state.connected) return [];

  try {
    const groups = await sock.groupFetchAllParticipating();
    return Object.entries(groups).map(([id, meta]) => ({
      id,
      name: meta.subject || id,
      participantCount: meta.participants?.length || 0,
      description: meta.desc || null,
    }));
  } catch (err) {
    console.error('getGroups error:', err.message);
    return [];
  }
}

export async function leaveGroup(jid) {
  const sock = getSocket();
  if (!sock) throw new Error('WhatsApp not connected');
  await sock.groupLeave(jid);
}
