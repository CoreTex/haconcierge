import express from 'express';
import { createWASession, getSocket, getConnectionState } from './session.js';
import { sendMessage, getGroups, leaveGroup } from './messaging.js';
import { requestRegistrationCode, confirmRegistrationCode, requestPairingCode } from './auth.js';
import pino from 'pino';

const logger = pino({ level: process.env.LOG_LEVEL || 'info' });
const PORT = 3001;
const BACKEND_URL = process.env.BACKEND_URL || 'http://127.0.0.1:8099';
const SESSION_DIR = process.env.SESSION_DIR || '/config/haconcierge/sessions';

const app = express();
app.use(express.json());

// Forward incoming messages to Python backend
export async function forwardMessage(payload) {
  try {
    const resp = await fetch(`${BACKEND_URL}/api/whatsapp/webhook`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!resp.ok) logger.warn('Backend webhook returned %d', resp.status);
  } catch (err) {
    logger.error('Failed to forward message to backend: %s', err.message);
  }
}

// Status endpoint
app.get('/status', (req, res) => {
  const state = getConnectionState();
  res.json(state);
});

// Send message
app.post('/send', async (req, res) => {
  const { jid, text, quotedId } = req.body;
  if (!jid || !text) return res.status(400).json({ error: 'jid and text required' });
  try {
    await sendMessage(jid, text, quotedId);
    res.json({ success: true });
  } catch (err) {
    logger.error('Send failed: %s', err.message);
    res.status(500).json({ success: false, error: err.message });
  }
});

// Get all groups
app.get('/groups', async (req, res) => {
  try {
    const groups = await getGroups();
    res.json({ groups });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Leave group
app.post('/groups/leave', async (req, res) => {
  const { jid } = req.body;
  try {
    await leaveGroup(jid);
    res.json({ success: true });
  } catch (err) {
    res.status(500).json({ success: false, error: err.message });
  }
});

// Registration – request SMS OTP
app.post('/register/request-code', async (req, res) => {
  const { phone } = req.body;
  try {
    const result = await requestRegistrationCode(phone, SESSION_DIR);
    res.json(result);
  } catch (err) {
    res.status(500).json({ success: false, error: err.message });
  }
});

// Registration – confirm OTP
app.post('/register/confirm-code', async (req, res) => {
  const { phone, code } = req.body;
  try {
    const result = await confirmRegistrationCode(phone, code, SESSION_DIR, forwardMessage);
    res.json(result);
  } catch (err) {
    res.status(500).json({ success: false, error: err.message });
  }
});

// Pairing code (for existing accounts)
app.post('/pair/request-code', async (req, res) => {
  const { phone } = req.body;
  try {
    const result = await requestPairingCode(phone, SESSION_DIR, forwardMessage);
    res.json(result);
  } catch (err) {
    res.status(500).json({ success: false, error: err.message });
  }
});

// Disconnect
app.post('/disconnect', async (req, res) => {
  try {
    const sock = getSocket();
    if (sock) await sock.logout();
    res.json({ success: true });
  } catch (err) {
    res.status(500).json({ success: false, error: err.message });
  }
});

// Start server
app.listen(PORT, '127.0.0.1', async () => {
  logger.info('WhatsApp bridge listening on port %d', PORT);
  // Try to restore existing session
  try {
    await createWASession(SESSION_DIR, forwardMessage);
  } catch (err) {
    logger.warn('No existing session to restore: %s', err.message);
  }
});
