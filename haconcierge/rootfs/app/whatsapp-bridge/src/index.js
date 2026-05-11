import express from 'express';
import { createWASession, getSocket, getConnectionState } from './session.js';
import { sendMessage, getGroups, leaveGroup } from './messaging.js';
import { requestRegistrationCode, confirmRegistrationCode, requestPairingCode } from './auth.js';
import pino from 'pino';

const logger = pino({ level: process.env.LOG_LEVEL || 'info' });
const PORT = 3001;
const BACKEND_URL = process.env.BACKEND_URL || 'http://127.0.0.1:8099';
const SESSION_DIR = process.env.SESSION_DIR || '/config/haconcierge/sessions';

// Prevent Baileys internal promise timeouts from crashing the process
process.on('unhandledRejection', (reason) => {
  logger.warn('Unhandled rejection (non-fatal): %s', reason?.message || String(reason));
});

const app = express();
app.use(express.json());

async function forwardMessage(payload) {
  try {
    const resp = await fetch(`${BACKEND_URL}/api/whatsapp/webhook`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!resp.ok) logger.warn('Backend webhook returned %d', resp.status);
  } catch (err) {
    logger.error('Failed to forward message: %s', err.message);
  }
}

// Status
app.get('/status', (req, res) => {
  res.json(getConnectionState());
});

// Send message
app.post('/send', async (req, res) => {
  const { jid, text, quotedId } = req.body;
  if (!jid || !text) return res.status(400).json({ error: 'jid and text required' });
  try {
    await sendMessage(jid, text, quotedId);
    res.json({ success: true });
  } catch (err) {
    res.status(500).json({ success: false, error: err.message });
  }
});

// Groups (returns [] if not connected – never throws)
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

// OTP registration – request SMS code
app.post('/register/request-code', async (req, res) => {
  const { phone } = req.body;
  if (!phone) return res.status(400).json({ success: false, error: 'phone required' });
  const result = await requestRegistrationCode(phone);
  res.json(result);
});

// OTP registration – confirm code
app.post('/register/confirm-code', async (req, res) => {
  const { phone, code } = req.body;
  if (!code) return res.status(400).json({ success: false, error: 'code required' });
  const result = await confirmRegistrationCode(phone, code);
  res.json(result);
});

// Pairing code (link existing WhatsApp account)
app.post('/pair/request-code', async (req, res) => {
  const { phone } = req.body;
  if (!phone) return res.status(400).json({ success: false, error: 'phone required' });
  const result = await requestPairingCode(phone);
  res.json(result);
});

// Disconnect / logout
app.post('/disconnect', async (req, res) => {
  try {
    const sock = getSocket();
    if (sock) await sock.logout();
    res.json({ success: true });
  } catch (err) {
    res.status(500).json({ success: false, error: err.message });
  }
});

// Start
app.listen(PORT, '127.0.0.1', async () => {
  logger.info('WhatsApp bridge listening on port %d', PORT);
  try {
    await createWASession(SESSION_DIR, forwardMessage);
  } catch (err) {
    logger.warn('Session start error: %s', err.message);
  }
});
