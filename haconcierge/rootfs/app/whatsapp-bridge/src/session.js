import {
  makeWASocket,
  useMultiFileAuthState,
  DisconnectReason,
  fetchLatestBaileysVersion,
} from '@whiskeysockets/baileys';
import pino from 'pino';
import path from 'path';
import { readdir, unlink } from 'fs/promises';

const logger = pino({ level: 'warn' });

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

async function _clearCredentials() {
  try {
    const authDir = path.join(_sessionDir, 'baileys_auth');
    const files = await readdir(authDir).catch(() => []);
    await Promise.all(files.map(f => unlink(path.join(authDir, f)).catch(() => {})));
    console.log('Cleared stale WA credentials');
  } catch { /* ignore */ }
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

  // mobile: true enables the OTP registration API (requestRegistrationCode /
  // register). Without it makeWASocket creates a WhatsApp-Web socket that only
  // supports QR / pairing-code linking and has no registration methods.
  _socket = makeWASocket({
    version,
    auth: state,
    logger,
    printQRInTerminal: false,
    mobile: true,
    generateHighQualityLinkPreview: false,
    syncFullHistory: false,
  });

  _socket.ev.on('creds.update', saveCreds);

  _socket.ev.on('connection.update', async (update) => {
    const { connection, lastDisconnect } = update;

    if (connection === 'open') {
      const phone = _socket.user?.id?.split(':')[0] || null;
      _connectionState = { connected: true, status: 'connected', phone };
      console.log('WhatsApp connected, phone:', phone);

    } else if (connection === 'close') {
      const code = lastDisconnect?.error?.output?.statusCode;
      const loggedOut = code === DisconnectReason.loggedOut;
      _socket = null;

      if (loggedOut) {
        // Stale or rejected credentials. Clear them and restart in fresh
        // (unregistered) mode so OTP / pairing registration can proceed.
        console.log('Session ended – clearing credentials and reconnecting fresh');
        _connectionState = { connected: false, status: 'unregistered', phone: null };
        await _clearCredentials();
        setTimeout(_connect, 2000);
      } else {
        console.log('Connection closed, reconnecting in 5s...');
        _connectionState = { connected: false, status: 'reconnecting', phone: null };
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

// ── Registration / pairing ────────────────────────────────────────────────────
// All operate on the single shared socket. The socket is always running:
// if credentials exist → authenticates automatically;
// if no credentials → stays in unregistered state ready for OTP/pairing.

export async function requestOTPCode(phone) {
  if (!_socket) {
    // Socket might be briefly null during reconnect cycle – wait up to 6s
    await new Promise(resolve => setTimeout(resolve, 3000));
    if (!_socket) await new Promise(resolve => setTimeout(resolve, 3000));
  }
  if (!_socket) throw new Error('Bridge socket not available. Please wait a moment and try again.');
  const clean = phone.replace(/[\s\-\+]/g, '');
  return _socket.requestRegistrationCode({ phoneNumber: clean, method: 'sms' });
}

export async function confirmOTPCode(code) {
  if (!_socket) throw new Error('Bridge socket not available');
  const clean = code.replace(/\D/g, '');
  await _socket.register(clean);
}

export async function requestPairingCode(phone) {
  if (!_socket) {
    await new Promise(resolve => setTimeout(resolve, 3000));
    if (!_socket) await new Promise(resolve => setTimeout(resolve, 3000));
  }
  if (!_socket) throw new Error('Bridge socket not available. Please wait a moment and try again.');
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
