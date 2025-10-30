import os, logging, asyncio, threading, re, unicodedata
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from typing import Optional, Tuple

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

from db_sqlite import (
    init_db, ensure_schema, cfg_get, cfg_set,
    get_all, exec_sql, insert_and_get_id
)

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("huibot")

BOT_TOKEN = (os.getenv("TELEGRAM_TOKEN") or os.getenv("BOT_TOKEN") or "").strip()
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "").strip()
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))

ISO_FMT = "%Y-%m-%d"

def strip_accents(s: str) -> str:
    return ''.join(c for c in unicodedata.normalize('NFKD', s) if not unicodedata.combining(c))

def parse_iso(s: str) -> datetime:
    if hasattr(s, "year"):
        return datetime(s.year, s.month, s.day)
    return datetime.strptime(str(s), ISO_FMT)

def _smart_parse_dmy(s: str) -> Tuple[int,int,int]:
    s = s.strip().replace("/", "-")
    parts = s.split("-")
    if len(parts) != 3:
        raise ValueError(f"Không hiểu ngày: {s}")
    d, m, y = parts
    d, m, y = int(d), int(m), int(y)
    if y < 100:  y += 2000
    datetime(y, m, d)
    return d, m, y

def parse_user_date(s: str) -> datetime:
    d, m, y = _smart_parse_dmy(s)
    return datetime(y, m, d)

def to_iso_str(d: datetime) -> str:
    return d.strftime(ISO_FMT)

def to_user_str(d: datetime) -> str:
    return d.strftime("%d-%m-%Y")

def parse_money(text: str) -> int:
    s = str(text).strip().lower().replace(",", "").replace("_", "").replace(" ", "").replace(".", "")
    if s.isdigit():
        return int(s)
    try:
        if s.endswith("tr"): return int(float(s[:-2]) * 1_000_000)
        if s.endswith(("k","n")): return int(float(s[:-1]) * 1_000)
        if s.endswith(("m","t")): return int(float(s[:-1]) * 1_000_000)
        return int(float(s))
    except Exception:
        raise ValueError(f"Không hiểu giá trị tiền: {text}")

def k_date(line, k: int) -> datetime:
    return parse_iso(line["start_date"]) + timedelta(days=(k-1)*int(line["period_days"]))

def roi_to_str(r: float) -> str:
    return f"{r*100:.2f}%"

def get_bids(line_id: int):
    rows = get_all("SELECT k, bid FROM rounds WHERE line_id=? ORDER BY k", (line_id,))
    return {int(r["k"]): int(r["bid"]) for r in rows}

def payout_at_k(line, bids: dict, k: int) -> int:
    M, N = int(line["contrib"]), int(line["legs"])
    T_k = int(bids.get(k, 0))
    D   = int(round(M * float(line.get("thau_rate", 0)) / 100.0))
    return (k-1)*M + (N - k)*(M - T_k) - D

def paid_so_far_if_win_at_k(bids: dict, M: int, k: int) -> int:
    return sum((M - int(bids.get(j, 0))) for j in range(1, k))

def compute_profit_var(line, k: int, bids: dict):
    M = int(line["contrib"])
    po = payout_at_k(line, bids, k)
    paid = paid_so_far_if_win_at_k(bids, M, k)
    base = paid if paid > 0 else M
    profit = po - paid
    roi = profit / base if base else 0.0
    return profit, roi, po, paid

def best_k_var(line, bids: dict, metric="roi"):
    bestk, bestkey, bestinfo = 1, -1e18, None
    for kk in range(1, int(line["legs"]) + 1):
        p, r, po, paid = compute_profit_var(line, kk, bids)
        key = r if metric == "roi" else p
        if key > bestkey:
            bestk, bestkey, bestinfo = kk, key, (p, r, po, paid)
    return bestk, bestinfo

def is_finished(line) -> bool:
    if line.get("status") == "CLOSED": return True
    last = k_date(line, int(line["legs"])).date()
    return datetime.now().date() >= last

init_db(); ensure_schema()

app_state = {"loop": None, "application": None, "started": False}

async def notify_admin(text: str):
    if ADMIN_CHAT_ID and app_state.get("application"):
        try:
            await app_state["application"].bot.send_message(chat_id=ADMIN_CHAT_ID, text=text[:4000])
        except Exception:
            logger.exception("notify_admin failed")

async def cmd_start(upd: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await upd.message.reply_text("👋 Hụi Bot Cloud Run đã sẵn sàng. Gõ /lenh để xem lệnh.")

def _int_like(s: str) -> int:
    m = re.search(r"-?\d+", s or "")
    if not m: raise ValueError(f"Không phải số: {s}")
    return int(m.group(0))

async def cmd_lenh(upd: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await upd.message.reply_text(
        "🌟 LỆNH CHÍNH (DD-MM-YYYY):\n"
        "/tao <tên> <tuần|tháng> <DD-MM-YYYY> <số_chân> <mệnh_giá> <sàn_%> <trần_%> <đầu_thảo_%>\n"
        "/tham <mã_dây> <kỳ> <số_tiền_thăm> [DD-MM-YYYY]\n"
        "/hen <mã_dây> <HH:MM>\n"
        "/danhsach\n/tomtat <mã_dây>\n/hottot <mã_dây> [Roi%|Lãi]\n/dong <mã_dây>\n/baocao [chat_id]"
    )

async def cmd_setreport(upd: Update, ctx: ContextTypes.DEFAULT_TYPE):
    cfg = cfg_get("bot_cfg", {}) or {}
    if ctx.args:
        try: cid = int(ctx.args[0])
        except Exception: return await upd.message.reply_text("❌ `chat_id` không hợp lệ.")
    else:
        cid = upd.effective_chat.id
    cfg["report_chat_id"] = cid
    cfg_set("bot_cfg", cfg)
    await upd.message.reply_text(f"✅ Đã lưu nơi nhận báo cáo/nhắc: {cid}")

async def _create_line_and_reply(upd: Update, name, kind, start_user, legs, contrib, base_rate, cap_rate, thau_rate):
    kind_l = str(kind).lower()
    period_days = 7 if kind_l in ["tuan","tuần","t","week","weekly"] else 30
    start_dt  = parse_user_date(start_user)
    start_iso = to_iso_str(start_dt)
    legs      = int(legs)
    contrib_i = parse_money(contrib)
    base_rate = float(base_rate); cap_rate = float(cap_rate); thau_rate = float(thau_rate)
    if not (0 <= base_rate <= cap_rate <= 100): raise ValueError("sàn% <= trần% và trong [0..100]")
    if not (0 <= thau_rate <= 100): raise ValueError("đầu thảo% trong [0..100]")

    line_id = insert_and_get_id(
        "INSERT INTO lines(name,period_days,start_date,legs,contrib,bid_type,bid_value,status,base_rate,cap_rate,thau_rate,remind_hour,remind_min,last_remind_iso) "
        "VALUES(?,?,?,?,?,'dynamic',0,'OPEN',?,?,?,8,0,NULL)",
        (name, period_days, start_iso, legs, contrib_i, base_rate, cap_rate, thau_rate)
    )

    await upd.message.reply_text(
        f"✅ Tạo dây #{line_id} ({name}) — {'Hụi Tuần' if period_days==7 else 'Hụi Tháng'}\n"
        f"• Mở: {to_user_str(start_dt)} · Chân: {legs} · Mệnh giá: {contrib_i:,} VND\n"
        f"• Sàn {base_rate:.2f}% · Trần {cap_rate:.2f}% · Đầu thảo {thau_rate:.2f}% (trên M)\n"
        f"⏰ Nhắc mặc định: 08:00 (đổi bằng /hen {line_id} HH:MM)\n"
        f"➡️ Nhập thăm: /tham {line_id} <kỳ> <số_tiền_thăm> [DD-MM-YYYY]"
    )

async def cmd_tao(upd: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if len(ctx.args) < 8:
        return await upd.message.reply_text("❗Cú pháp: /tao <tên> <tuần|tháng> <DD-MM-YYYY> <số_chân> <mệnh_giá> <sàn_%> <trần_%> <đầu_thảo_%>")
    try:
        await _create_line_and_reply(upd, *ctx.args[:8])
    except Exception as e:
        logger.exception("cmd_tao error: %s", e)
        await upd.message.reply_text(f"⚠️ Lỗi: {e}")

async def _save_tham_msg(upd: Update, line_id: int, k: int, bid: int, rdate_iso: Optional[str]):
    rows = get_all("SELECT * FROM lines WHERE id=?", (line_id,))
    if not rows:  return await upd.message.reply_text("❌ Không tìm thấy dây.")
    line = rows[0]
    if not (1 <= k <= int(line["legs"])): return await upd.message.reply_text(f"❌ Kỳ hợp lệ 1..{line['legs']}.")
    M = int(line["contrib"])
    min_bid = int(round(M * float(line.get("base_rate", 0)) / 100.0))
    max_bid = int(round(M * float(line.get("cap_rate", 100)) / 100.0))
    if bid < min_bid or bid > max_bid:
        return await upd.message.reply_text(
            f"❌ Thăm phải trong [{min_bid:,} .. {max_bid:,}] VND "
            f"(Sàn {line['base_rate']}% · Trần {line['cap_rate']}% · M={M:,})"
        )

    exec_sql(
        "INSERT INTO rounds(line_id,k,bid,round_date) VALUES(?,?,?,?) "
        "ON CONFLICT(line_id,k) DO UPDATE SET bid=excluded.bid, round_date=excluded.round_date",
        (line_id, k, bid, rdate_iso)
    )
    await upd.message.reply_text(
        f"✅ Lưu thăm kỳ {k} cho dây #{line_id}: {bid:,} VND" + (f" · ngày {to_user_str(parse_iso(rdate_iso))}" if rdate_iso else "")
    )

async def cmd_tham(upd: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if len(ctx.args) < 3:
        return await upd.message.reply_text("❗Cú pháp: /tham <mã_dây> <kỳ> <số_tiền_thăm> [DD-MM-YYYY]")
    try:
        line_id = int(ctx.args[0])
        k = int(ctx.args[1])
        bid = parse_money(ctx.args[2])
        rdate_iso = to_iso_str(parse_user_date(ctx.args[3])) if len(ctx.args) >= 4 else None
        await _save_tham_msg(upd, line_id, k, bid, rdate_iso)
    except Exception as e:
        logger.exception("cmd_tham error: %s", e)
        await upd.message.reply_text(f"⚠️ Lỗi: {e}")

async def cmd_hen(upd: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if len(ctx.args) != 2:
        return await upd.message.reply_text("❗Cú pháp: /hen <mã_dây> <HH:MM>  (VD: /hen 1 07:45)")
    try:
        line_id = int(ctx.args[0])
        hh, mm = ctx.args[1].split(":"); hh = int(hh); mm = int(mm)
        if not (0 <= hh <= 23 and 0 <= mm <= 59): raise ValueError("giờ/phút không hợp lệ")
    except Exception as e:
        return await upd.message.reply_text(f"❌ Tham số không hợp lệ: {e}")
    rows = get_all("SELECT id FROM lines WHERE id=?", (line_id,))
    if not rows: return await upd.message.reply_text("❌ Không tìm thấy dây.")
    exec_sql("UPDATE lines SET remind_hour=?, remind_min=? WHERE id=?", (hh, mm, line_id))
    await upd.message.reply_text(f"✅ Đã đặt giờ nhắc cho dây #{line_id}: {hh:02d}:{mm:02d}")

def list_text() -> str:
    rows = get_all("SELECT id,name,period_days,start_date,legs,contrib,base_rate,cap_rate,thau_rate,status,remind_hour,remind_min FROM lines ORDER BY id DESC")
    if not rows: return "📂 Chưa có dây nào."
    out = ["📋 **Danh sách dây**:"]
    for r in rows:
        kind = "Tuần" if int(r["period_days"])==7 else "Tháng"
        out.append(
            f"• #{r['id']} · {r['name']} · {kind} · mở {to_user_str(parse_iso(r['start_date']))} · chân {r['legs']} · M {int(r['contrib']):,} VND · "
            f"sàn {float(r['base_rate']):.2f}% · trần {float(r['cap_rate']):.2f}% · thầu {float(r['thau_rate']):.2f}% · nhắc {int(r['remind_hour']):02d}:{int(r['remind_min']):02d} · {r['status']}"
        )
    return "\n".join(out)

async def cmd_danhsach(upd: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await upd.message.reply_text(list_text())

def load_line(line_id: int):
    rows = get_all("SELECT * FROM lines WHERE id=?", (line_id,))
    return rows[0] if rows else None

async def cmd_tomtat(upd: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args: return await upd.message.reply_text("❗Cú pháp: /tomtat <mã_dây>")
    try: line_id = int(ctx.args[0])
    except Exception: return await upd.message.reply_text("❌ mã_dây phải là số.")
    line = load_line(line_id)
    if not line: return await upd.message.reply_text("❌ Không tìm thấy dây.")
    bids = get_bids(line_id)
    M, N = int(line["contrib"]), int(line["legs"])
    cfg_line = f"Sàn {float(line.get('base_rate',0)):.2f}% · Trần {float(line.get('cap_rate',100)):.2f}% · Đầu thảo {float(line.get('thau_rate',0)):.2f}% (trên M)"
    k_now = max(1, min(len(bids)+1, N))
    p, r, po, paid = compute_profit_var(line, k_now, bids)
    bestk, (bp, br, bpo, bpaid) = best_k_var(line, bids, metric="roi")
    msg = [
        f"📌 Dây #{line['id']} · {line['name']} · {'Tuần' if int(line['period_days'])==7 else 'Tháng'}",
        f"• Mở: {to_user_str(parse_iso(line['start_date']))} · Chân: {N} · Mệnh giá/kỳ: {M:,} VND",
        f"• {cfg_line} · Nhắc {int(line.get('remind_hour',8)):02d}:{int(line.get('remind_min',0)):02d}",
        f"• Thăm: " + (", ".join([f"k{kk}:{int(b):,}" for kk,b in sorted(bids.items())]) if bids else "(chưa có)"),
        f"• Kỳ hiện tại ước tính: {k_now} · Payout: {po:,} · Đã đóng: {paid:,} → Lãi: {int(round(p)):,} (ROI {roi_to_str(r)})",
    ]
    best_line = f"⭐ Đề xuất (ROI): kỳ {bestk} · ngày {to_user_str(k_date(line,bestk))} · Payout {bpo:,} · Đã đóng {bpaid:,} · Lãi {int(round(bp)):,} · ROI {roi_to_str(br)}"
    msg.append(best_line)
    if is_finished(line): msg.append("✅ Dây đã đến hạn — /dong để lưu trữ.")
    await upd.message.reply_text("\n".join(msg))

async def cmd_hottot(upd: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if len(ctx.args) < 1: return await upd.message.reply_text("❗Cú pháp: /hottot <mã_dây> [Roi%|Lãi]")
    try: line_id = int(ctx.args[0])
    except Exception: return await upd.message.reply_text("❌ mã_dây phải là số.")
    metric = "roi"
    if len(ctx.args) >= 2:
        raw = strip_accents(ctx.args[1].strip().lower().replace("%", ""))
        if raw in ("roi", "lai"): metric = raw
    line = load_line(line_id)
    if not line: return await upd.message.reply_text("❌ Không tìm thấy dây.")
    bids = get_bids(line_id)
    bestk, (bp, br, bpo, bpaid) = best_k_var(line, bids, metric=("roi" if metric=="roi" else "lai"))
    await upd.message.reply_text(
        f"🔎 Gợi ý theo {'ROI%' if metric=='roi' else 'Lãi'}:\n"
        f"• Nên hốt kỳ: {bestk}\n"
        f"• Ngày dự kiến: {to_user_str(k_date(line,bestk))}\n"
        f"• Payout kỳ đó: {bpo:,}\n"
        f"• Đã đóng trước đó: {bpaid:,}\n"
        f"• Lãi ước tính: {int(round(bp)):,} — ROI: {roi_to_str(br)}"
    )

async def cmd_dong(upd: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args: return await upd.message.reply_text("❗Cú pháp: /dong <mã_dây>")
    try: line_id = int(ctx.args[0])
    except Exception: return await upd.message.reply_text("❌ mã_dây phải là số.")
    exec_sql("UPDATE lines SET status='CLOSED' WHERE id=?", (line_id,))
    await upd.message.reply_text(f"🗂️ Đã đóng & lưu trữ dây #{line_id}.")

async def cmd_huy(upd: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await upd.message.reply_text("🛑 Huỷ wizard. Hãy dùng các lệnh một bước như /tao, /tham, /hen ...")

async def handle_text(upd: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await upd.message.reply_text("💡 Vui lòng dùng lệnh: /tao, /tham, /hen, /danhsach, /tomtat, /hottot, /dong, /baocao")

def build_app():
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start",    cmd_start))
    application.add_handler(CommandHandler("lenh",     cmd_lenh))
    application.add_handler(CommandHandler("baocao",   cmd_setreport))
    application.add_handler(CommandHandler("tao",      cmd_tao))
    application.add_handler(CommandHandler("tham",     cmd_tham))
    application.add_handler(CommandHandler("hen",      cmd_hen))
    application.add_handler(CommandHandler("danhsach", cmd_danhsach))
    application.add_handler(CommandHandler("tomtat",   cmd_tomtat))
    application.add_handler(CommandHandler("hottot",   cmd_hottot))
    application.add_handler(CommandHandler("dong",     cmd_dong))
    application.add_handler(CommandHandler("huy",      cmd_huy))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    async def on_error(update, context):
        logger.exception("PTB error: %s", context.error)
        try:
            await notify_admin(f"⚠️ PTB error: {context.error}")
        except Exception:
            pass
    application.add_error_handler(on_error)
    return application

def run_bot_background():
    if getattr(run_bot_background, "_started", False):
        return
    if not BOT_TOKEN:
        logger.warning("BOT_TOKEN is empty; bot will not start.")
        return
    loop = asyncio.new_event_loop()
    app_state["loop"] = loop

    async def _runner():
        app_state["application"] = build_app()
        await app_state["application"].initialize()
        await app_state["application"].start()
        logger.info("Telegram application started")
        while True:
            await asyncio.sleep(3600)

    def _thread():
        asyncio.set_event_loop(loop)
        loop.create_task(_runner())
        loop.run_forever()

    t = threading.Thread(target=_thread, name="tg-bot", daemon=True)
    t.start()
    app_state["started"] = True
    run_bot_background._started = True

run_bot_background()

@app.get("/")
def root():
    return "ok", 200

@app.get("/health")
def health():
    return jsonify(status="ok"), 200

@app.post("/webhook")
def webhook():
    expected = WEBHOOK_SECRET or ""
    got = request.args.get("secret", "")
    if expected and got != expected:
        return "forbidden", 403

    if not app_state.get("application") or not app_state.get("loop"):
        return "bot not started", 503

    data = request.get_json(silent=True) or {}
    try:
        update = Update.de_json(data, app_state["application"].bot)
        fut = asyncio.run_coroutine_threadsafe(
            app_state["application"].process_update(update),
            app_state["loop"]
        )
        fut.result(timeout=10)
    except Exception as e:
        logger.exception("webhook error: %s", e)
    return "ok", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    app.run(host="0.0.0.0", port=port)
