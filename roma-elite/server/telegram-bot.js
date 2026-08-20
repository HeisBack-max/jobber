// Roma Elite — Telegram acquisition bot (zero dependencies).
//
// Flow:
//   /start  ->  welcome message + hero image + [ ✅ Confirm & Play Free ] button
//   Confirm ->  calls the site's /api/bot/provision, then replies with the
//               player's username, password and a one-tap magic-login link that
//               drops them straight into the game, already signed in.
//
// DELIBERATELY NO PAYMENT STEP. Accounts are free here, exactly as they are on
// the website. This bot does not request, display or process any payment, and
// must not be advertised as requiring one. See LEGAL.md.
//
// Run:  BOT_TOKEN=... BOT_API_SECRET=... SITE_URL=https://your.site \
//         node server/telegram-bot.js

const BOT_TOKEN = process.env.BOT_TOKEN;
const API_SECRET = process.env.BOT_API_SECRET;
const SITE_URL = (process.env.SITE_URL || 'http://localhost:3000').replace(/\/+$/, '');
const API_URL = (process.env.API_URL || SITE_URL).replace(/\/+$/, '');
// Optional: a hero image shown with the welcome message.
const HERO_IMAGE = process.env.HERO_IMAGE_URL || '';

if (!BOT_TOKEN) {
  console.error('BOT_TOKEN is not set. Create a bot with @BotFather and export its token.');
  process.exit(1);
}
if (!API_SECRET) {
  console.error('BOT_API_SECRET is not set. It must match the value the web server runs with.');
  process.exit(1);
}

const TG = `https://api.telegram.org/bot${BOT_TOKEN}`;

async function tg(method, payload) {
  const res = await fetch(`${TG}/${method}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  const data = await res.json().catch(() => ({}));
  if (!data.ok) console.error(`[tg] ${method} failed:`, data.description || res.status);
  return data.result;
}

const WELCOME = [
  '🏛️ *ROMA ELITE*',
  '_Glory of the Empire_',
  '',
  'Welcome, legionnaire\\! You are one tap away from the arena\\.',
  '',
  '🎁 *100 welcome free spins* — genuinely free',
  '💰 *10,000 virtual coins* to start',
  '🎰 *Two games*: Roma Elite & Phnom Penh Nights',
  '',
  '⚖️ This is a *for\\-fun social game*\\. You play with virtual coins that have',
  '*no cash value*\\. There are no deposits, no withdrawals, and *nothing of',
  'value can be won*\\. No payment is ever required\\. 18\\+\\.',
  '',
  'Tap below to create your free account\\.',
].join('\n');

const CONFIRM_KEYBOARD = {
  inline_keyboard: [[{ text: '✅ Confirm & Play Free', callback_data: 'confirm' }]],
};

async function sendWelcome(chatId) {
  if (HERO_IMAGE) {
    await tg('sendPhoto', {
      chat_id: chatId, photo: HERO_IMAGE,
      caption: WELCOME, parse_mode: 'MarkdownV2', reply_markup: CONFIRM_KEYBOARD,
    });
  } else {
    await tg('sendMessage', {
      chat_id: chatId, text: WELCOME,
      parse_mode: 'MarkdownV2', reply_markup: CONFIRM_KEYBOARD,
      link_preview_options: { is_disabled: true },
    });
  }
}

// Escape user-visible values for Telegram MarkdownV2.
const esc = (s) => String(s).replace(/[_*[\]()~`>#+\-=|{}.!\\]/g, (m) => '\\' + m);

async function provision(chatId) {
  const res = await fetch(`${API_URL}/api/bot/provision`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-Bot-Secret': API_SECRET },
    body: JSON.stringify({ telegramId: chatId }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || `provision failed (${res.status})`);
  return data;
}

async function handleConfirm(chatId, callbackId) {
  await tg('answerCallbackQuery', { callback_query_id: callbackId, text: 'Creating your account…' });
  let acc;
  try {
    acc = await provision(chatId);
  } catch (err) {
    console.error('[bot] provision error:', err.message);
    await tg('sendMessage', {
      chat_id: chatId,
      text: '⚠️ Something went wrong creating your account. Please try /start again shortly.',
    });
    return;
  }

  const url = `${SITE_URL}${acc.path}`;
  const lines = acc.returning
    ? [
        '✅ *Welcome back\\!*',
        '',
        `Username: \`${esc(acc.username)}\``,
        '',
        'Your account is ready — tap below to sign in\\.',
        '_\\(Your password is unchanged from when you first joined\\.\\)_',
      ]
    : [
        '✅ *Your account is ready*',
        '',
        `Username: \`${esc(acc.username)}\``,
        `Password: \`${esc(acc.password)}\``,
        '',
        '💾 _Save these — they are shown only once\\._',
        '',
        '🎁 *100 free spins* and *10,000 coins* are already in your balance\\.',
      ];
  lines.push('', '⚖️ _For fun only\\. Virtual coins have no cash value\\. 18\\+_');

  await tg('sendMessage', {
    chat_id: chatId,
    text: lines.join('\n'),
    parse_mode: 'MarkdownV2',
    reply_markup: { inline_keyboard: [[{ text: '🎰 Launch Roma Elite', url }]] },
  });
}

async function handleUpdate(u) {
  try {
    if (u.callback_query) {
      const cq = u.callback_query;
      if (cq.data === 'confirm') await handleConfirm(cq.message.chat.id, cq.id);
      return;
    }
    const msg = u.message;
    if (!msg || !msg.text) return;
    const chatId = msg.chat.id;
    const text = msg.text.trim().toLowerCase();

    if (text.startsWith('/start')) return void sendWelcome(chatId);
    if (text.startsWith('/help')) {
      return void tg('sendMessage', {
        chat_id: chatId,
        text: 'Send /start to create your free account and get your login link.\n\n'
            + 'This is a for-fun social game: virtual coins only, no cash value, '
            + 'nothing of value can be won, and no payment is ever required. 18+.',
      });
    }
    // Anything else: nudge back to the entry point.
    return void sendWelcome(chatId);
  } catch (err) {
    console.error('[bot] update error:', err.message);
  }
}

async function main() {
  await tg('setMyCommands', {
    commands: [
      { command: 'start', description: 'Create your free account and get your login link' },
      { command: 'help', description: 'What is this?' },
    ],
  });
  const me = await tg('getMe', {});
  console.log(`\n  🤖 Roma Elite bot running as @${me ? me.username : 'unknown'}`);
  console.log(`  ↪  site: ${SITE_URL}`);
  console.log(`  ⚖️  Free accounts only — this bot never requests payment.\n`);

  let offset = 0;
  for (;;) {
    try {
      const res = await fetch(`${TG}/getUpdates?timeout=50&offset=${offset}`);
      const data = await res.json().catch(() => ({}));
      if (data.ok && Array.isArray(data.result)) {
        for (const u of data.result) {
          offset = u.update_id + 1;
          handleUpdate(u);
        }
      }
    } catch (err) {
      console.error('[bot] poll error:', err.message);
      await new Promise((r) => setTimeout(r, 3000));
    }
  }
}

main().catch((e) => { console.error(e); process.exit(1); });
