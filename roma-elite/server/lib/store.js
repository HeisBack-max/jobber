// Tiny JSON-backed persistence with atomic writes. Zero dependencies.
// Suitable for a single-process demo; swap for a real DB before any scale use.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DATA_DIR = path.join(__dirname, '..', '..', 'data');
const DB_FILE = path.join(DATA_DIR, 'roma-elite.json');

function emptyDb() {
  return { users: {}, byUsername: {}, tokens: {}, sessions: {} };
}

let db = emptyDb();

export function load() {
  try {
    fs.mkdirSync(DATA_DIR, { recursive: true });
    if (fs.existsSync(DB_FILE)) {
      db = { ...emptyDb(), ...JSON.parse(fs.readFileSync(DB_FILE, 'utf8')) };
    } else {
      persist();
    }
  } catch (err) {
    console.error('[store] failed to load, starting fresh:', err.message);
    db = emptyDb();
  }
  return db;
}

let writeTimer = null;
function persist() {
  // Atomic write: temp file + rename so a crash never leaves a half-written db.
  const tmp = DB_FILE + '.tmp';
  fs.writeFileSync(tmp, JSON.stringify(db, null, 2));
  fs.renameSync(tmp, DB_FILE);
}

// Debounced save to avoid a disk write on every single spin under load.
function scheduleSave() {
  if (writeTimer) return;
  writeTimer = setTimeout(() => {
    writeTimer = null;
    try { persist(); } catch (e) { console.error('[store] save failed:', e.message); }
  }, 200);
}

export function getDb() { return db; }
export function save() { scheduleSave(); }
export function saveNow() { if (writeTimer) { clearTimeout(writeTimer); writeTimer = null; } persist(); }

// --- User records -----------------------------------------------------------
export function createUser(user) {
  db.users[user.id] = user;
  db.byUsername[user.username.toLowerCase()] = user.id;
  scheduleSave();
  return user;
}

export function getUser(id) { return db.users[id] || null; }

export function getUserByUsername(username) {
  const id = db.byUsername[String(username).toLowerCase()];
  return id ? db.users[id] : null;
}

export function updateUser(user) {
  db.users[user.id] = user;
  scheduleSave();
  return user;
}

// --- Magic-link tokens ------------------------------------------------------
export function putToken(token, record) { db.tokens[token] = record; scheduleSave(); }
export function getToken(token) { return db.tokens[token] || null; }
export function consumeToken(token) {
  const rec = db.tokens[token];
  if (rec) { delete db.tokens[token]; scheduleSave(); }
  return rec || null;
}

// --- Sessions ---------------------------------------------------------------
export function putSession(sid, userId) {
  db.sessions[sid] = { userId, createdAt: Date.now() };
  scheduleSave();
}
export function getSession(sid) { return db.sessions[sid] || null; }
export function deleteSession(sid) { delete db.sessions[sid]; scheduleSave(); }
