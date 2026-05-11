import {
  makeWASocket,
  useMultiFileAuthState,
  DisconnectReason,
  fetchLatestBaileysVersion,
} from '@whiskeysockets/baileys';
import pino from 'pino';
import path from 'path';

const logger = pino({ level: 'warn' }); // Baileys is very verbose

let _socket = null;
let _connectionState = { connected: false, status: 'disconnected', phone: null };
let _forwardMessage = null;
let _sessionDir = null;

export function getSocket() { return _socket; }
export function getConnectionState() { return _connectionState; }

export async function createWASession(sessionDir, forwardMessage) {
  _sessionDir = sessionDir;
  _forwardMessage = forwardMessage;
  return _connect(sessionDir, forwardMessage);
}

async function _connect(sessionDir, forwardMessage) {
  const authDir = path.join(sessionDir, 'baileys_auth');
  const { state, saveCreds } = await useMultiFileAuthState(authDir);
  const { version } = await fetchLatestBaileysVersion();

  _socket = makeWASocket({
    version,
    auth: state,
    logger,
    printQRInTerminal: false,
    browser: ['HAConcierge', 'Chrome', '1.0.0'],
    generateHighQualityLinkPreview: false,
    syncFullHistory: false,
  });

  _socket.ev.on('creds.update', saveCreds);

  _socket.ev.on('connection.update', async (update) => {
    const { connection, lastDisconnect, qr } = update;

    if (connection === 'open') {
      const phone = _socket.user?.id?.split(':')[0] || null;
      _connectionState = { connected: true, status: 'connected', phone };
      console.log('WhatsApp connected, phone:', phone);
    } else if (connection === 'close') {
      const code = lastDisconnect?.error?.output?.statusCode;
      const loggedOut = code === DisconnectReason.loggedOut;
      _connectionState = { connected: false, status: loggedOut ? 'logged_out' : 'reconnecting', phone: null };

      if (!loggedOut) {
        console.log('Connection closed, reconnecting in 5s...');
        setTimeout(() => _connect(sessionDir, forwardMessage), 5000);
      } else {
        console.log('Logged out from WhatsApp');
      }
    } else {
      _connectionState = { connected: false, status: 'connecting', phone: null };
    }
  });

  _socket.ev.on('messages.upsert', async ({ messages, type }) => {
    if (type !== 'notify') return;
    for (const msg of messages) {
      if (msg.key.fromMe) continue; // Skip own messages
      if (!msg.message) continue;

      const text = extractText(msg);
      if (!text) continue;

      const isGroup = msg.key.remoteJid?.includes('@g.us') || false;
      const chatJid = msg.key.remoteJid || '';
      const senderJid = isGroup
        ? (msg.key.participant || '')
        : (msg.key.remoteJid || '');

      const senderName = msg.pushName || null;

      await forwardMessage({
        id: msg.key.id,
        chatJid,
        senderJid,
        senderName,
        text,
        isGroup,
        timestamp: msg.messageTimestamp,
        quotedId: msg.message?.extendedTextMessage?.contextInfo?.stanzaId || null,
      });
    }
  });

  return _socket;
}

function extractText(msg) {
  const m = msg.message;
  if (!m) return null;
  return (
    m.conversation ||
    m.extendedTextMessage?.text ||
    m.imageMessage?.caption ||
    m.videoMessage?.caption ||
    null
  );
}
