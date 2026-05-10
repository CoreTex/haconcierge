import {
  makeWASocket,
  useMultiFileAuthState,
  fetchLatestBaileysVersion,
} from '@whiskeysockets/baileys';
import pino from 'pino';
import path from 'path';
import { createWASession } from './session.js';

const logger = pino({ level: 'warn' });

export async function requestRegistrationCode(phone, sessionDir) {
  // Clean phone: remove +, spaces, dashes
  const cleanPhone = phone.replace(/[\s\-\+]/g, '');
  const authDir = path.join(sessionDir, 'baileys_auth');
  const { state, saveCreds } = await useMultiFileAuthState(authDir);
  const { version } = await fetchLatestBaileysVersion();

  return new Promise((resolve) => {
    const sock = makeWASocket({
      version,
      auth: state,
      logger,
      printQRInTerminal: false,
      browser: ['HAConcierge', 'Chrome', '1.0.0'],
    });

    sock.ev.on('creds.update', saveCreds);

    sock.ev.on('connection.update', async (update) => {
      const { connection } = update;
      if (connection === 'open') {
        try {
          // Request registration via SMS
          const result = await sock.requestRegistrationCode({ phoneNumber: cleanPhone, method: 'sms' });
          resolve({ success: true, method: 'sms', details: result });
        } catch (err) {
          resolve({ success: false, error: err.message });
        } finally {
          await sock.end();
        }
      }
    });

    // Timeout after 30s
    setTimeout(() => resolve({ success: false, error: 'Timeout' }), 30000);
  });
}

export async function confirmRegistrationCode(phone, code, sessionDir, forwardMessage) {
  const cleanPhone = phone.replace(/[\s\-\+]/g, '');
  const cleanCode = code.replace(/\D/g, '');
  const authDir = path.join(sessionDir, 'baileys_auth');
  const { state, saveCreds } = await useMultiFileAuthState(authDir);
  const { version } = await fetchLatestBaileysVersion();

  return new Promise((resolve) => {
    const sock = makeWASocket({
      version,
      auth: state,
      logger,
      printQRInTerminal: false,
      browser: ['HAConcierge', 'Chrome', '1.0.0'],
    });

    sock.ev.on('creds.update', saveCreds);

    sock.ev.on('connection.update', async (update) => {
      const { connection } = update;
      if (connection === 'open') {
        try {
          await sock.register(cleanCode);
          resolve({ success: true });
          // Start full session
          setTimeout(() => createWASession(sessionDir, forwardMessage), 1000);
        } catch (err) {
          resolve({ success: false, error: err.message });
        } finally {
          await sock.end();
        }
      }
    });

    setTimeout(() => resolve({ success: false, error: 'Timeout' }), 30000);
  });
}

export async function requestPairingCode(phone, sessionDir, forwardMessage) {
  const cleanPhone = phone.replace(/[\s\-\+]/g, '');
  const authDir = path.join(sessionDir, 'baileys_auth');
  const { state, saveCreds } = await useMultiFileAuthState(authDir);
  const { version } = await fetchLatestBaileysVersion();

  return new Promise((resolve) => {
    const sock = makeWASocket({
      version,
      auth: state,
      logger,
      printQRInTerminal: false,
      browser: ['HAConcierge', 'Chrome', '1.0.0'],
    });

    sock.ev.on('creds.update', saveCreds);

    sock.ev.on('connection.update', async (update) => {
      const { connection } = update;
      if (connection === 'open') {
        // Already connected (session restored), no pairing needed
        resolve({ success: true, alreadyConnected: true });
      }
    });

    // Wait briefly then request pairing code
    setTimeout(async () => {
      try {
        const code = await sock.requestPairingCode(cleanPhone);
        resolve({ success: true, code: code.match(/.{1,4}/g)?.join('-') || code });
        // After pairing, transition to full session
        sock.ev.on('connection.update', async (u) => {
          if (u.connection === 'open') {
            await sock.end();
            setTimeout(() => createWASession(sessionDir, forwardMessage), 500);
          }
        });
      } catch (err) {
        resolve({ success: false, error: err.message });
        await sock.end();
      }
    }, 3000);

    setTimeout(() => resolve({ success: false, error: 'Timeout' }), 60000);
  });
}
