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
// True once the noise handshake is complete and WA is waiting for auth.
// requestPairingCode must only be called while this is true.
let _qrReady = false;
// Timer handle for scheduled reconnects – kept so it can be cancelled.
let _reconnectTimer = null;

export function getSocket() { return _socket; }
export function getConnectionState() { return { ..._connectionState }; }
export function isQRReady() { return _qrReady; }

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
    console.log('Cleared WA credentials');
  } catch { /* ignore */ }
}

async function _connect() {
  // Cancel any timer that would schedule another connect while this one runs.
  if (_reconnectTimer) { clearTimeout(_reconnectTimer); _reconnectTimer = null; }

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
    browser: ['HAConcierge', 'Chrome', '124.0.0'],
    generateHighQualityLinkPreview: false,
    syncFullHistory: false,
  });

  _socket.ev.on('creds.update', saveCreds);

  _socket.ev.on('connection.update', async (update) => {
    const { connection, lastDisconnect } = update;

    // QR event = noise handshake complete; socket is ready for requestPairingCode
    if (update.qr) {
      _qrReady = true;
      console.log('QR ready – pairing code can now be requested');
    }

    if (connection === 'open') {
      _qrReady = false;
      const phone = _socket.user?.id?.split(':')[0] || null;
      _connectionState = { connected: true, status: 'connected', phone };
      console.log('WhatsApp connected, phone:', phone);

    } else if (connection === 'close') {
      _qrReady = false;
      const code = lastDisconnect?.error?.output?.statusCode;
      const loggedOut = code === DisconnectReason.loggedOut;

      if (loggedOut) {
        _socket = null;
        _connectionState = { connected: false, status: 'unregistered', phone: null };
        console.log('Session ended – clearing credentials and reconnecting fresh');
        await _clearCredentials();
        _reconnectTimer = setTimeout(_connect, 2000);
      } else {
        _connectionState = { connected: false, status: 'reconnecting', phone: null };
        console.log('Connection closed, reconnecting in 5s...');
        _reconnectTimer = setTimeout(_connect, 5000);
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

export async function requestPairingCode(phone) {
  if (_connectionState.connected) {
    throw new Error('Bereits verbunden. Bitte zuerst trennen.');
  }

  // Cancel any pending reconnect, clear all credentials, and start a clean
  // socket. Stale auth files from previous attempts (e.g. the mobile API
  // sessions) corrupt the session keys and cause WA to reject the pairing
  // handshake even when the code itself is delivered successfully.
  if (_reconnectTimer) { clearTimeout(_reconnectTimer); _reconnectTimer = null; }
  _socket = null;
  _qrReady = false;
  await _clearCredentials();
  await _connect();

  // _connect() returns as soon as the socket object is created; the QR event
  // fires asynchronously once the noise handshake completes (~1–3 s).
  for (let i = 0; i < 30; i++) {
    if (_socket && _qrReady) break;
    await new Promise(r => setTimeout(r, 1000));
  }
  if (!_socket) throw new Error('Bridge socket not available. Please wait a moment and try again.');
  if (!_qrReady) throw new Error('Socket noch nicht bereit. Bitte kurz warten und erneut versuchen.');

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
