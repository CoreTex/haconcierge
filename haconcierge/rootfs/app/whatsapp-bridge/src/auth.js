// Auth operations delegate to the single shared socket in session.js.
// Creating separate sockets for registration conflicts with the main session
// and causes the main socket to get logged out.
import { requestOTPCode, confirmOTPCode, requestPairingCode as _requestPairingCode } from './session.js';

export async function requestRegistrationCode(phone) {
  try {
    const result = await requestOTPCode(phone);
    return { success: true, method: 'sms', details: result };
  } catch (err) {
    return { success: false, error: err.message };
  }
}

export async function confirmRegistrationCode(phone, code) {
  try {
    await confirmOTPCode(code);
    return { success: true };
  } catch (err) {
    return { success: false, error: err.message };
  }
}

export async function requestPairingCode(phone) {
  try {
    const code = await _requestPairingCode(phone);
    return { success: true, code };
  } catch (err) {
    return { success: false, error: err.message };
  }
}
