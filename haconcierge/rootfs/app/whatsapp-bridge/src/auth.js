import { requestPairingCode as _requestPairingCode } from './session.js';

export async function requestPairingCode(phone) {
  try {
    const code = await _requestPairingCode(phone);
    return { success: true, code };
  } catch (err) {
    return { success: false, error: err.message };
  }
}
