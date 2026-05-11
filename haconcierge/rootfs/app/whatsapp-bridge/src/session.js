import {
  makeWASocket,
  useMultiFileAuthState,
  DisconnectReason,
  fetchLatestBaileysVersion,
} from '@whiskeysockets/baileys';
import pino from 'pino';
import path from 'path';

const logger = pino({ level: 'warn' });

// Bundled fallback in case WA version fetch fails (updated periodically)
const FALLBACK_VERSION = [2, 3000, 1015901307];

let _socket = null;
let _connectionState = { connected: false, status: 'disconnected', phone: null };
let _sessionDir = null;
let _forwardMessage = null;

export function getSocket() { return _socket; }
export function getConnectionState() { return { ..._connectionState }; }

export async function createWASession(sessionDir, forwardMessage) {
  _sessionDir = sessionDir;
  _forwardMessage = forwardMessage;
  return _connect();
}

async function _connect() {
  const authDir = path.join(_sessionDir, 'baileys_auth');
  const { state, saveCreds } = await useMultiFileAuthState(authDir);

  let version = FALLBACK_VERSION;
  try {
    const v = await fetchLatestBaileysVersion();
    if (v?.version) version = v.version;
  } catch {
    console.log('Could not fetch WA version, using fallback');
  }

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

  _socket.ev.on('connection.update', (update) => {
    const { connection, lastDisconnect } = update;

    if (connection === 'open') {
      const phone = _socket.user?.id?.split(':')[0] || null;
      _connectionState = { connected: true, status: 'connected', phone };
      console.log('WhatsApp connected, phone:', phone);
    } else if (connection === 'close') {
      const code = lastDisconnect?.error?.output?.statusCode;
      const loggedOut = code === DisconnectReason.loggedOut;
      _connectionState = {
        connected: false,
        status: loggedOut ? 'logged_out' : 'reconnecting',
        phone: null,
      };
      if (loggedOut) {
        console.log('Logged out from WhatsApp');
        _socket = null;
      } else {
        console.log('Connection closed, reconnecting in 5s...');
        setTimeout(_connect, 5000);
      }
    } else if (connection) {
      _connectionState = { connected: false, status: 'connecting', phone: null };
    }
  });

  _socket.ev.on('messages.upsert', async ({ messages, type }) => {
    if (type !== 'notify' || !_forwardMessage) return;
    for (const msg of messages) {
      if (msg.key.fromMe || !msg.message) continue;
      const text = extractText(msg);
      if (!text) continue;

      const isGroup = msg.key.remoteJid?.includes('@g.us') || false;
      const chatJid = msg.key.remoteJid || '';
      const senderJid = isGroup ? (msg.key.participant || '') : chatJid;

      try {
        await _forwardMessage({
          id: msg.key.id,
          chatJid,
          senderJid,
          senderName: msg.pushName || null,
          text,
          isGroup,
          timestamp: msg.messageTimestamp,
          quotedId: msg.message?.extendedTextMessage?.contextInfo?.stanzaId || null,
        });
      } catch (err) {
        console.error('Failed to forward message:', err.message);
      }
    }
  });

  return _socket;
}

// ── Registration / pairing – operate on the single shared socket ──────────────
// These only make sense when the socket is NOT yet authenticated (fresh install).

export async function requestOTPCode(phone) {
  if (!_socket) throw new Error('Bridge not ready – call createWASession first');
  const clean = phone.replace(/[\s\-\+]/g, '');
  return _socket.requestRegistrationCode({ phoneNumber: clean, method: 'sms' });
}

export async function confirmOTPCode(code) {
  if (!_socket) throw new Error('Bridge not ready');
  const clean = code.replace(/\D/g, '');
  await _socket.register(clean);
}

export async function requestPairingCode(phone) {
  if (!_socket) throw new Error('Bridge not ready');
  const clean = phone.replace(/[\s\-\+]/g, '');
  const code = await _socket.requestPairingCode(clean);
  return code.match(/.{1,4}/g)?.join('-') || code;
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
