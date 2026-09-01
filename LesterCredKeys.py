import asyncio
import logging
import sqlite3
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
    filters
)

ADMIN_ID = 6345954014
BOT_TOKEN = "8840360690:AAFlnPdW5mE9uWOpwvHOWECMhy_RN3D-Rc0"

WAITING_RESTOCK_KEYS = 1
WAITING_USER_ID = 2
WAITING_CREDIT_AMOUNT = 3
WAITING_BRAND_NAME = 4
WAITING_APK_FILE = 5
WAITING_BROADCAST_MSG = 6
WAITING_MANAGE_USER_ID = 7
WAITING_SEND_USER_MSG = 8
WAITING_EDIT_PRICE_VAL = 9

PRICES = {
    "1 Day": 99,
    "7 Days": 249,
    "30 Days": 449,
    "60 Days": 799
}

def fmt(amount: int) -> str:
    return f"{amount:,}"

def get_db_connection():
    conn = sqlite3.connect("bot_database.db", timeout=10)
    # Fast SQLite execution mode
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            balance INTEGER DEFAULT 0,
            payment_pending INTEGER DEFAULT 0
        )
    """)
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN payment_pending INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    cursor.execute("CREATE TABLE IF NOT EXISTS brands (name TEXT PRIMARY KEY)")
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            brand TEXT,
            duration TEXT,
            key_code TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS apks (
            brand TEXT PRIMARY KEY,
            file_id TEXT,
            caption TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS brand_prices (
            brand TEXT,
            duration TEXT,
            price INTEGER,
            PRIMARY KEY (brand, duration)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            brand TEXT,
            duration TEXT,
            key_code TEXT,
            purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("SELECT COUNT(*) FROM brands")
    if cursor.fetchone()[0] == 0:
        cursor.executemany("INSERT INTO brands VALUES (?)", [("Lester Mod Apk",), ("Realme Loader",)])
        for b in ["Lester Mod Apk", "Realme Loader"]:
            for dur, pr in PRICES.items():
                cursor.execute("INSERT OR IGNORE INTO brand_prices (brand, duration, price) VALUES (?, ?, ?)", (b, dur, pr))
    conn.commit()
    conn.close()

init_db()

def get_brand_price(brand: str, duration: str) -> int:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT price FROM brand_prices WHERE brand = ? AND duration = ?", (brand, duration))
    res = cursor.fetchone()
    conn.close()
    if res:
        return res[0]
    return PRICES.get(duration, 99)

def get_key_count(brand: str, duration: str) -> int:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM keys WHERE brand = ? AND duration = ?", (brand, duration))
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_main_keyboard(user_id):
    buttons = [
        ["💳 My Wallet", "🔑 Generate Key"],
        ["📲 Get Latest Apk", "🔑 My Keys"]
    ]
    if user_id == ADMIN_ID:
        buttons.append(["⚙️ Admin Panel"])
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id, balance) VALUES (?, 0)", (user_id,))
    conn.commit()
    conn.close()
    
    welcome_text = (
        "<b>👋 WELCOME TO KEY GENERATOR STORE</b>\n\n"
        "<i>Select an option from the menu below to get started.</i>"
    )
    await update.message.reply_text(
        welcome_text,
        parse_mode="HTML",
        reply_markup=get_main_keyboard(user_id)
    )

async def handle_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT balance, payment_pending FROM users WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    conn.close()
    
    balance = res[0] if res else 0
    payment_pending = res[1] if res else 0

    wallet_text = (
        "<b>MY WALLET DASHBOARD</b>\n\n"
        f"👤 <b>User ID:</b> <code>{user_id}</code>\n"
        f"💰 <b>Balance:</b> <code>{fmt(balance)} Credits</code>\n"
    )

    if payment_pending:
        wallet_text += "\n⚠️ <b>Payment Pending:</b> <i>Please clear your pending payment to the admin! Contact @Lester_Owner</i>\n"

    wallet_text += "\n<i>To top-up credits, contact Admin: @Lester_Owner</i>"
    
    keyboard = [
        [InlineKeyboardButton("📋 Price List", callback_data="price_list")],
        [InlineKeyboardButton("💳 Buy Credits", callback_data="price_list")]
    ]

    await update.message.reply_text(
        wallet_text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_price_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("👤 I am a User", callback_data="pricelist_user")],
        [InlineKeyboardButton("💼 I am a Re-Seller", callback_data="pricelist_reseller")]
    ]
    await query.edit_message_text("<b>📋 SELECT PRICE LIST TYPE</b>\n\n", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_pricelist_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("💳 Buy Credits Via Admin", url="https://t.me/Lester_Owner")],
        [InlineKeyboardButton("⬅️ Back to Price List", callback_data="price_list")]
    ]
    await query.edit_message_text("<b>👤 USER PRICE LIST</b>\n\n<i>Coming soon</i>", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_pricelist_reseller(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    text = (
        "<b>💼 RE-SELLER PRICE LIST</b>\n\n"
        "🔹 <b>1,000 Credits</b> - ₹849\n"
        "🔹 <b>2,500 Credits</b> - ₹1499\n"
        "🔹 <b>5,000 Credits</b> - ₹2,899\n"
        "🔹 <b>Unlimited 60 Days</b> - ₹3,999\n\n"
        "<i>Select Your Plan and inform the Admin to Top-up the Credits</i>"
    )
    keyboard = [
        [InlineKeyboardButton("💳 Buy Credits Via Admin", url="https://t.me/Lester_Owner")],
        [InlineKeyboardButton("⬅️ Back to Price List", callback_data="price_list")]
    ]
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_my_keys(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT brand, duration, key_code, purchased_at FROM user_keys WHERE user_id = ? ORDER BY id DESC LIMIT 10", (user_id,))
    keys = cursor.fetchall()
    conn.close()

    if not keys:
        await update.message.reply_text("<b>🔑 MY PURCHASED KEYS</b>\n\n<i>You haven't purchased any keys yet.</i>", parse_mode="HTML")
        return

    text = "<b>🔑 YOUR RECENT PURCHASED KEYS</b>\n\n"
    for idx, (brand, duration, key_code, purchased_at) in enumerate(keys, 1):
        text += f"<b>{idx}. Brand:</b> <i>{brand}</i>\n" \
                f"   <b>Duration:</b> <i>{duration}</i>\n" \
                f"   <b>Key:</b> <code>{key_code}</code>\n" \
                f"   <b>Date:</b> <code>{purchased_at}</code>\n\n"

    await update.message.reply_text(text, parse_mode="HTML")

async def show_brands(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM brands")
    brands = [row[0] for row in cursor.fetchall()]
    conn.close()

    if not brands:
        await update.message.reply_text("<i>⚠️ No brands available right now.</i>", parse_mode="HTML")
        return

    keyboard = [[InlineKeyboardButton(f"🔥 {b}", callback_data=f"selectbrand_{b}")] for b in brands]
    await update.message.reply_text(
        "<b>🛒 SELECT YOUR BRAND</b>\n\n<i>Choose a brand to proceed:</i>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_brand_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    brand_name = query.data.split("selectbrand_")[1]
    
    p1 = get_brand_price(brand_name, "1 Day")
    p7 = get_brand_price(brand_name, "7 Days")
    p30 = get_brand_price(brand_name, "30 Days")
    p60 = get_brand_price(brand_name, "60 Days")

    c1 = get_key_count(brand_name, "1 Day")
    c7 = get_key_count(brand_name, "7 Days")
    c30 = get_key_count(brand_name, "30 Days")
    c60 = get_key_count(brand_name, "60 Days")

    keyboard = [
        [InlineKeyboardButton(f"🎟️ 1 Day - {fmt(p1)} Credits ({c1} Pcs.)", callback_data=f"buy_{brand_name}_1 Day")],
        [InlineKeyboardButton(f"🎫 7 Days - {fmt(p7)} Credits ({c7} Pcs.)", callback_data=f"buy_{brand_name}_7 Days")],
        [InlineKeyboardButton(f"🏆 30 Days - {fmt(p30)} Credits ({c30} Pcs.)", callback_data=f"buy_{brand_name}_30 Days")],
        [InlineKeyboardButton(f"👑 60 Days - {fmt(p60)} Credits ({c60} Pcs.)", callback_data=f"buy_{brand_name}_60 Days")]
    ]
    text = (
        f"<b>🏷️ Selected Brand:</b> <i>{brand_name}</i>\n\n"
        "<b>⏳ Choose key duration:</b>"
    )
    await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_key_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    parts = query.data.split("_")
    brand = parts[1]
    duration = "_".join(parts[2:])
    cost = get_brand_price(brand, duration)

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    balance = user[0] if user else 0

    if balance < cost:
        conn.close()
        keyboard = [[InlineKeyboardButton("💳 Buy Credits Via Admin", url="https://t.me/Lester_Owner")]]
        await query.edit_message_text(
            f"❌ <b>INSUFFICIENT CREDITS!</b>\n\n"
            f"<b>Required:</b> <code>{fmt(cost)} Credits</code>\n"
            f"<b>Your Balance:</b> <code>{fmt(balance)} Credits</code>\n\n"
            f"<i>Please top up your wallet credits.</i>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    cursor.execute("SELECT id, key_code FROM keys WHERE brand = ? AND duration = ? LIMIT 1", (brand, duration))
    key_data = cursor.fetchone()

    if not key_data:
        conn.close()
        await query.edit_message_text(
            f"⚠️ <b>OUT OF STOCK!</b>\n\n"
            f"Currently no keys available for <b>{brand}</b> (<i>{duration}</i>).\n"
            f"<i>Please try again later.</i>",
            parse_mode="HTML"
        )
        return

    key_id, key_code = key_data
    new_balance = balance - cost

    cursor.execute("DELETE FROM keys WHERE id = ?", (key_id,))
    cursor.execute("UPDATE users SET balance = ? WHERE user_id = ?", (new_balance, user_id))
    cursor.execute("INSERT INTO user_keys (user_id, brand, duration, key_code) VALUES (?, ?, ?, ?)", (user_id, brand, duration, key_code))
    conn.commit()
    conn.close()

    keyboard = [
        [InlineKeyboardButton("Get Latest Updated apk ✅", callback_data=f"get_apk_{brand}")],
        [InlineKeyboardButton("💳 Buy Credits", callback_data="price_list")]
    ]

    success_text = (
        "<b>🎉 PURCHASE SUCCESSFUL!</b>\n\n"
        f"🏷️ <b>Brand:</b> <i>{brand}</i>\n"
        f"⏳ <b>Duration:</b> <i>{duration}</i>\n"
        f"🔑 <b>Your Key:</b> <code>{key_code}</code>\n\n"
        f"💰 <b>Remaining Balance:</b> <code>{fmt(new_balance)} Credits</code>"
    )
    await query.edit_message_text(success_text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))

async def delete_msg_task(bot, chat_id: int, message_id: int, delay: int = 300):
    await asyncio.sleep(delay)
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception:
        pass

async def handle_get_apk_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    balance = res[0] if res else 0
    conn.close()

    if balance < 99:
        keyboard = [[InlineKeyboardButton("💳 Buy Credits Via Admin", url="https://t.me/Lester_Owner")]]
        msg_text = "⚠️ <i>You need at least <b>99 Credits</b> in your wallet to use the Get Latest APK button.</i>"
        if update.callback_query:
            await update.callback_query.answer("⚠️ You need at least 99 Credits to access latest APKs!", show_alert=True)
            await update.callback_query.message.reply_text(msg_text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await update.message.reply_text(msg_text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM brands")
    apk_brands = [row[0] for row in cursor.fetchall()]
    conn.close()

    if not apk_brands:
        msg = "<i>⚠️ No brands available right now.</i>"
        if update.callback_query:
            await update.callback_query.message.reply_text(msg, parse_mode="HTML")
            await update.callback_query.answer()
        else:
            await update.message.reply_text(msg, parse_mode="HTML")
        return

    keyboard = [[InlineKeyboardButton(f"📲 {b}", callback_data=f"get_apk_{b}")] for b in apk_brands]
    keyboard.append([InlineKeyboardButton("💳 Buy Credits", callback_data="price_list")])
    text = "<b>📲 SELECT BRAND TO DOWNLOAD APK</b>\n\n"
    
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_get_apk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    balance = res[0] if res else 0
    conn.close()

    if balance < 99:
        await query.answer("⚠️ You need at least 99 Credits to download APKs!", show_alert=True)
        return

    brand = query.data.replace("get_apk_", "")

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT file_id, caption FROM apks WHERE brand = ?", (brand,))
    res = cursor.fetchone()
    conn.close()

    if not res or not res[0]:
        await query.message.reply_text(
            f"⚠️ <i>No updated APK file configured for {brand} yet.</i>",
            parse_mode="HTML"
        )
        return

    file_id, custom_caption = res[0], res[1] or ""

    caption_text = ""
    if custom_caption:
        caption_text = f"{custom_caption}\n\n"

    caption_text += (
        "⚠️ <b>Notice:</b> <i>This APK file will be automatically deleted from this chat after <b>5 minutes</b> for security reasons. Download it now!</i>"
    )

    sent_msg = await context.bot.send_document(
        chat_id=query.message.chat_id,
        document=file_id,
        caption=caption_text,
        parse_mode="HTML"
    )

    asyncio.create_task(delete_msg_task(context.bot, query.message.chat_id, sent_msg.message_id, 300))

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    keyboard = [
        [InlineKeyboardButton("➕ Add Keys", callback_data="admin_addkeys"), InlineKeyboardButton("💳 Add Credits", callback_data="admin_addcredit")],
        [InlineKeyboardButton("📁 Add Brand", callback_data="admin_addbrand"), InlineKeyboardButton("🗑️ Remove Brand", callback_data="admin_rembrand")],
        [InlineKeyboardButton("🛠️ Manage Brand", callback_data="admin_managebrand"), InlineKeyboardButton("👥 Manage User", callback_data="admin_manageuser")],
        [InlineKeyboardButton("📲 Upload APK", callback_data="admin_addapk"), InlineKeyboardButton("❌ Remove APK", callback_data="admin_remapk")],
        [InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")]
    ]
    admin_text = (
        "<b>⚙️ ADMIN CONTROL PANEL</b>\n\n"
        "<i>Select an operation to manage the system:</i>"
    )
    await update.message.reply_text(admin_text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))

async def admin_callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "admin_addkeys":
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM brands")
        brands = [row[0] for row in cursor.fetchall()]
        conn.close()

        if not brands:
            await query.edit_message_text("<i>⚠️ Please add a brand first.</i>", parse_mode="HTML")
            return

        keyboard = [[InlineKeyboardButton(f"🏷️ {b}", callback_data=f"restockbrand_{b}")] for b in brands]
        await query.edit_message_text("<b>Select Brand to Restock:</b>", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data == "admin_addcredit":
        await query.edit_message_text("<b>💳 Add User Credits</b>\n\n<i>Send Telegram User ID:</i>", parse_mode="HTML")
        return WAITING_USER_ID

    elif data == "admin_addbrand":
        await query.edit_message_text("<b>📁 Add Brand</b>\n\n<i>Send the new Brand name:</i>", parse_mode="HTML")
        return WAITING_BRAND_NAME

    elif data == "admin_rembrand":
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM brands")
        brands = [row[0] for row in cursor.fetchall()]
        conn.close()
        keyboard = [[InlineKeyboardButton(f"❌ {b}", callback_data=f"delbrand_{b}")] for b in brands]
        await query.edit_message_text("<b>Select Brand to Remove:</b>", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "admin_managebrand":
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM brands")
        brands = [row[0] for row in cursor.fetchall()]
        conn.close()

        if not brands:
            await query.edit_message_text("<i>⚠️ No brands available.</i>", parse_mode="HTML")
            return

        keyboard = [[InlineKeyboardButton(f"🛠️ {b}", callback_data=f"managebrand_{b}")] for b in brands]
        await query.edit_message_text("<b>Select Brand to Manage:</b>", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "admin_manageuser":
        await query.edit_message_text("<b>👥 Manage User</b>\n\n<i>Send Telegram User ID of the user:</i>", parse_mode="HTML")
        return WAITING_MANAGE_USER_ID

    elif data == "admin_broadcast":
        await query.edit_message_text("<b>📢 Broadcast Message</b>\n\n<i>Send the message you want to broadcast to all users:</i>", parse_mode="HTML")
        return WAITING_BROADCAST_MSG

    elif data == "admin_addapk":
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM brands")
        brands = [row[0] for row in cursor.fetchall()]
        conn.close()

        if not brands:
            await query.edit_message_text("<i>⚠️ Please add a brand first.</i>", parse_mode="HTML")
            return

        keyboard = [[InlineKeyboardButton(f"📲 {b}", callback_data=f"apkbrand_{b}")] for b in brands]
        await query.edit_message_text("<b>Select Brand to Add/Update APK:</b>", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "admin_remapk":
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT brand FROM apks")
        apk_brands = [row[0] for row in cursor.fetchall()]
        conn.close()

        if not apk_brands:
            await query.edit_message_text("<i>⚠️ No APK files stored currently.</i>", parse_mode="HTML")
            return

        keyboard = [[InlineKeyboardButton(f"❌ {b}", callback_data=f"delapk_{b}")] for b in apk_brands]
        await query.edit_message_text("<b>Select Brand to Remove APK:</b>", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))

async def manage_brand_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    brand = query.data.split("managebrand_")[1]
    context.user_data['manage_brand'] = brand

    keyboard = [
        [InlineKeyboardButton("🗑️ Remove All Keys", callback_data=f"mbrand_remkeys_{brand}")],
        [InlineKeyboardButton("💲 Edit Prices", callback_data=f"mbrand_editprice_{brand}")]
    ]
    await query.edit_message_text(
        f"<b>🛠️ Managing Brand:</b> <i>{brand}</i>\n\n<i>Choose an action:</i>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def manage_brand_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("mbrand_remkeys_"):
        brand = data.replace("mbrand_remkeys_", "")
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM keys WHERE brand = ?", (brand,))
        conn.commit()
        conn.close()
        await query.edit_message_text(f"<b>✅ All keys for '{brand}' have been removed successfully.</b>", parse_mode="HTML")

    elif data.startswith("mbrand_editprice_"):
        brand = data.replace("mbrand_editprice_", "")
        context.user_data['edit_price_brand'] = brand
        keyboard = [
            [InlineKeyboardButton("1 Day", callback_data=f"edur_{brand}_1 Day"), InlineKeyboardButton("7 Days", callback_data=f"edur_{brand}_7 Days")],
            [InlineKeyboardButton("30 Days", callback_data=f"edur_{brand}_30 Days"), InlineKeyboardButton("60 Days", callback_data=f"edur_{brand}_60 Days")]
        ]
        await query.edit_message_text(f"<b>Select duration to edit price for {brand}:</b>", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))

async def edit_price_duration_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    parts = query.data.split("_")
    brand = parts[1]
    duration = "_".join(parts[2:])
    context.user_data['edit_price_duration'] = duration

    await query.edit_message_text(
        f"<b>💲 Edit Price</b>\nBrand: <i>{brand}</i> | Duration: <i>{duration}</i>\n\n<i>Send the new integer price for this key:</i>",
        parse_mode="HTML"
    )
    return WAITING_EDIT_PRICE_VAL

async def receive_new_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        new_price = int(update.message.text.strip())
        brand = context.user_data.get('edit_price_brand')
        duration = context.user_data.get('edit_price_duration')

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO brand_prices (brand, duration, price) VALUES (?, ?, ?)", (brand, duration, new_price))
        conn.commit()
        conn.close()

        await update.message.reply_text(f"<b>✅ Price updated successfully for {brand} ({duration}) to {fmt(new_price)} Credits.</b>", parse_mode="HTML")
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("❌ <i>Invalid price. Enter a valid number:</i>", parse_mode="HTML")
        return WAITING_EDIT_PRICE_VAL

async def process_brand_for_apk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    brand = query.data.split("apkbrand_")[1]
    context.user_data['apk_brand'] = brand

    await query.edit_message_text(
        f"<b>📲 Upload APK for Brand:</b> <i>{brand}</i>\n\n"
        f"<i>Please send/upload the APK file directly in chat. You can include any description/caption with the file so users can see it!</i>",
        parse_mode="HTML"
    )
    return WAITING_APK_FILE

async def process_brand_to_restock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    brand = query.data.split("restockbrand_")[1]
    context.user_data['restock_brand'] = brand

    keyboard = [
        [InlineKeyboardButton("1 Day", callback_data="restockdur_1 Day"), InlineKeyboardButton("7 Days", callback_data="restockdur_7 Days")],
        [InlineKeyboardButton("30 Days", callback_data="restockdur_30 Days"), InlineKeyboardButton("60 Days", callback_data="restockdur_60 Days")]
    ]
    await query.edit_message_text(f"<b>Selected Brand:</b> <i>{brand}</i>\n\n<i>Select duration to restock:</i>", parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))

async def process_duration_to_restock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    duration = query.data.split("restockdur_")[1]
    context.user_data['restock_duration'] = duration
    await query.edit_message_text(
        f"<b>🔑 Restock Keys:</b> <i>{context.user_data['restock_brand']} ({duration})</i>\n\n"
        f"<i>Send keys line by line (one key per line):</i>",
        parse_mode="HTML"
    )
    return WAITING_RESTOCK_KEYS

async def receive_keys(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw_keys = update.message.text.strip().split("\n")
    keys_list = [k.strip() for k in raw_keys if k.strip()]
    brand = context.user_data.get('restock_brand')
    duration = context.user_data.get('restock_duration')

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.executemany("INSERT INTO keys (brand, duration, key_code) VALUES (?, ?, ?)", [(brand, duration, k) for k in keys_list])
    conn.commit()
    conn.close()
    await update.message.reply_text(f"<b>✅ Added {len(keys_list)} keys for {brand} ({duration}).</b>", parse_mode="HTML")
    return ConversationHandler.END

async def receive_user_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        target_id = int(update.message.text.strip())
        context.user_data['target_user_id'] = target_id
        await update.message.reply_text(f"<b>User ID set to:</b> <code>{target_id}</code>\n\n<i>Enter Credit amount to add:</i>", parse_mode="HTML")
        return WAITING_CREDIT_AMOUNT
    except ValueError:
        await update.message.reply_text("❌ <i>Invalid User ID. Enter a valid numerical ID:</i>", parse_mode="HTML")
        return WAITING_USER_ID

async def receive_credit_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = int(update.message.text.strip())
        target_id = context.user_data.get('target_user_id')

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO users (user_id, balance) VALUES (?, 0)", (target_id,))
        cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, target_id))
        conn.commit()
        conn.close()

        await update.message.reply_text(f"<b>✅ Successfully added {fmt(amount)} Credits to User {target_id}.</b>", parse_mode="HTML")
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("❌ <i>Invalid amount. Enter a valid number:</i>", parse_mode="HTML")
        return WAITING_CREDIT_AMOUNT

async def receive_manage_user_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        target_id = int(update.message.text.strip())
        context.user_data['manage_target_id'] = target_id

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT balance, payment_pending FROM users WHERE user_id = ?", (target_id,))
        res = cursor.fetchone()
        conn.close()

        balance = res[0] if res else 0
        payment_pending = res[1] if res else 0
        pending_status = "Enabled ⚠️" if payment_pending else "Disabled 🟢"

        keyboard = [
            [InlineKeyboardButton("🗑️ Remove All Credits", callback_data=f"muser_remcredits_{target_id}")],
            [InlineKeyboardButton(f"💳 Payment Pending: {pending_status}", callback_data=f"muser_togglepay_{target_id}")],
            [InlineKeyboardButton("✉️ Send Message to User", callback_data=f"muser_sendmsg_{target_id}")]
        ]

        text = (
            f"<b>👥 MANAGE USER:</b> <code>{target_id}</code>\n\n"
            f"💰 <b>Balance:</b> <code>{fmt(balance)} Credits</code>\n"
            f"⚠️ <b>Payment Pending Flag:</b> <i>{pending_status}</i>"
        )
        await update.message.reply_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text("❌ <i>Invalid User ID. Enter a valid numerical ID:</i>", parse_mode="HTML")
        return WAITING_MANAGE_USER_ID

async def manage_user_actions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("muser_remcredits_"):
        target_id = int(data.replace("muser_remcredits_", ""))
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET balance = 0 WHERE user_id = ?", (target_id,))
        conn.commit()
        conn.close()
        await query.edit_message_text(f"<b>✅ All credits removed for user <code>{target_id}</code>. Balance is now 0.</b>", parse_mode="HTML")

    elif data.startswith("muser_togglepay_"):
        target_id = int(data.replace("muser_togglepay_", ""))
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT payment_pending FROM users WHERE user_id = ?", (target_id,))
        res = cursor.fetchone()
        current_status = res[0] if res else 0
        new_status = 0 if current_status else 1
        cursor.execute("UPDATE users SET payment_pending = ? WHERE user_id = ?", (new_status, target_id))
        conn.commit()
        conn.close()

        status_str = "Enabled ⚠️" if new_status else "Disabled 🟢"
        keyboard = [
            [InlineKeyboardButton("🗑️ Remove All Credits", callback_data=f"muser_remcredits_{target_id}")],
            [InlineKeyboardButton(f"💳 Payment Pending: {status_str}", callback_data=f"muser_togglepay_{target_id}")],
            [InlineKeyboardButton("✉️ Send Message to User", callback_data=f"muser_sendmsg_{target_id}")]
        ]
        text = (
            f"<b>👥 MANAGE USER:</b> <code>{target_id}</code>\n\n"
            f"⚠️ <b>Payment Pending Flag:</b> <i>{status_str} (Updated)</i>"
        )
        await query.edit_message_text(text, parse_mode="HTML", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("muser_sendmsg_"):
        target_id = int(data.replace("muser_sendmsg_", ""))
        context.user_data['msg_target_id'] = target_id
        await query.message.reply_text(f"<b>✉️ Send Message to User <code>{target_id}</code></b>\n\n<i>Send the message text now:</i>", parse_mode="HTML")
        return WAITING_SEND_USER_MSG

async def receive_send_user_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    target_id = context.user_data.get('msg_target_id')
    message_text = update.message.text

    try:
        await context.bot.send_message(
            chat_id=target_id,
            text=f"<b>💬 Message from Admin:</b>\n\n{message_text}",
            parse_mode="HTML"
        )
        await update.message.reply_text(f"<b>✅ Message successfully sent to user <code>{target_id}</code>.</b>", parse_mode="HTML")
    except Exception as e:
        await update.message.reply_text(f"❌ <i>Failed to send message: {e}</i>", parse_mode="HTML")
    return ConversationHandler.END

async def receive_new_brand(update: Update, context: ContextTypes.DEFAULT_TYPE):
    brand_name = update.message.text.strip()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO brands VALUES (?)", (brand_name,))
    for dur, pr in PRICES.items():
        cursor.execute("INSERT OR IGNORE INTO brand_prices (brand, duration, price) VALUES (?, ?, ?)", (brand_name, dur, pr))
    conn.commit()
    conn.close()
    await update.message.reply_text(f"<b>✅ Brand '{brand_name}' added successfully.</b>", parse_mode="HTML")
    return ConversationHandler.END

async def receive_apk_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.document:
        await update.message.reply_text("❌ <i>Please send a valid file/document. Try again:</i>", parse_mode="HTML")
        return WAITING_APK_FILE

    file_id = update.message.document.file_id
    caption = update.message.caption or ""
    brand = context.user_data.get('apk_brand')

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT OR REPLACE INTO apks (brand, file_id, caption) VALUES (?, ?, ?)", (brand, file_id, caption))
    cursor.execute("SELECT user_id FROM users")
    all_users = [row[0] for row in cursor.fetchall()]
    conn.close()

    await update.message.reply_text(f"<b>✅ Latest APK & Description for '{brand}' uploaded and saved successfully! Broadcasters notifying users...</b>", parse_mode="HTML")

    notif_text = (
        f"🚨 <b>APK UPDATED!</b>\n\n"
        f"<b>{brand}</b> has been updated! Please checkout the <b>Get Latest Apk</b> button to download it."
    )
    for uid in all_users:
        try:
            await context.bot.send_message(chat_id=uid, text=notif_text, parse_mode="HTML")
        except Exception:
            pass

    return ConversationHandler.END

async def receive_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message.text
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    all_users = [row[0] for row in cursor.fetchall()]
    conn.close()

    success_count = 0
    for uid in all_users:
        try:
            await context.bot.send_message(chat_id=uid, text=msg, parse_mode="HTML")
            success_count += 1
        except Exception:
            pass

    await update.message.reply_text(f"<b>✅ Broadcast sent successfully to {success_count} users.</b>", parse_mode="HTML")
    return ConversationHandler.END

async def process_remove_brand(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    brand = query.data.split("delbrand_")[1]
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM brands WHERE name = ?", (brand,))
    cursor.execute("DELETE FROM apks WHERE brand = ?", (brand,))
    cursor.execute("DELETE FROM brand_prices WHERE brand = ?", (brand,))
    conn.commit()
    conn.close()
    await query.edit_message_text(f"<b>🗑️ Brand '{brand}' removed.</b>", parse_mode="HTML")

async def process_remove_apk(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    brand = query.data.split("delapk_")[1]
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM apks WHERE brand = ?", (brand,))
    conn.commit()
    conn.close()
    await query.edit_message_text(f"<b>🗑️ APK for '{brand}' removed.</b>", parse_mode="HTML")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Regex("^🔑 Generate Key$"), show_brands))
    app.add_handler(MessageHandler(filters.Regex("^💳 My Wallet$"), handle_wallet))
    app.add_handler(MessageHandler(filters.Regex("^📲 Get Latest Apk$"), handle_get_apk_menu))
    app.add_handler(MessageHandler(filters.Regex("^🔑 My Keys$"), handle_my_keys))
    app.add_handler(MessageHandler(filters.Regex("^⚙️ Admin Panel$"), admin_panel))
    
    app.add_handler(CallbackQueryHandler(handle_price_list, pattern="^price_list$"))
    app.add_handler(CallbackQueryHandler(handle_pricelist_user, pattern="^pricelist_user$"))
    app.add_handler(CallbackQueryHandler(handle_pricelist_reseller, pattern="^pricelist_reseller$"))
    
    app.add_handler(CallbackQueryHandler(handle_get_apk, pattern="^get_apk_"))
    app.add_handler(CallbackQueryHandler(handle_brand_selection, pattern="^selectbrand_"))
    app.add_handler(CallbackQueryHandler(handle_key_purchase, pattern="^buy_"))
    app.add_handler(CallbackQueryHandler(process_brand_to_restock, pattern="^restockbrand_"))
    app.add_handler(CallbackQueryHandler(process_remove_brand, pattern="^delbrand_"))
    app.add_handler(CallbackQueryHandler(process_remove_apk, pattern="^delapk_"))
    app.add_handler(CallbackQueryHandler(manage_brand_menu, pattern="^managebrand_"))
    app.add_handler(CallbackQueryHandler(manage_brand_actions, pattern="^mbrand_"))
    app.add_handler(CallbackQueryHandler(manage_user_actions, pattern="^muser_"))

    conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(admin_callback_router, pattern="^admin_"),
            CallbackQueryHandler(process_brand_for_apk, pattern="^apkbrand_"),
            CallbackQueryHandler(process_duration_to_restock, pattern="^restockdur_"),
            CallbackQueryHandler(edit_price_duration_callback, pattern="^edur_")
        ],
        states={
            WAITING_RESTOCK_KEYS: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_keys)],
            WAITING_USER_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_user_id)],
            WAITING_CREDIT_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_credit_amount)],
            WAITING_BRAND_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_new_brand)],
            WAITING_APK_FILE: [MessageHandler(filters.Document.ALL, receive_apk_file)],
            WAITING_BROADCAST_MSG: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_broadcast)],
            WAITING_MANAGE_USER_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_manage_user_id)],
            WAITING_SEND_USER_MSG: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_send_user_msg)],
            WAITING_EDIT_PRICE_VAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_new_price)],
        },
        fallbacks=[CommandHandler("start", start)],
    )
    app.add_handler(conv_handler)

    logging.basicConfig(level=logging.INFO)
    app.run_polling()

if __name__ == "__main__":
    main()
