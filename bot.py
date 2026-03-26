import os
import yt_dlp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

TOKEN = os.environ.get("TOKEN")

# ─── Qualidades disponíveis ───────────────────────────────────────────────────
QUALIDADES = {
    "alta":  {"label": "🔥 Alta (320kbps)",  "quality": "320"},
    "media": {"label": "⚡ Média (192kbps)", "quality": "192"},
    "baixa": {"label": "💾 Baixa (128kbps)",  "quality": "128"},
}

# ─── /start ───────────────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Olá! Eu converto vídeos do *YouTube* e *TikTok* em MP3.\n\n"
        "📎 Envie um link para começar!\n"
        "📋 Playlists do YouTube também são suportadas.",
        parse_mode="Markdown"
    )

# ─── Recebe o link ────────────────────────────────────────────────────────────
async def receber_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()

    if not any(d in url for d in ["youtube.com", "youtu.be", "tiktok.com"]):
        await update.message.reply_text("❌ Envie um link válido do YouTube ou TikTok.")
        return

    # Salva o link no contexto do usuário
    context.user_data["url"] = url

    # Detecta se é playlist
    is_playlist = "list=" in url
    context.user_data["is_playlist"] = is_playlist

    # Monta o menu de qualidade
    keyboard = [
        [InlineKeyboardButton(QUALIDADES["alta"]["label"],  callback_data="q_alta")],
        [InlineKeyboardButton(QUALIDADES["media"]["label"], callback_data="q_media")],
        [InlineKeyboardButton(QUALIDADES["baixa"]["label"], callback_data="q_baixa")],
    ]

    msg = "🎵 Link recebido!\n"
    if is_playlist:
        msg += "📋 *Playlist detectada* — todos os vídeos serão baixados.\n"
    msg += "\nEscolha a qualidade do MP3:"

    await update.message.reply_text(
        msg,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ─── Callback dos botões de qualidade ────────────────────────────────────────
async def escolher_qualidade(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    qualidade_key = query.data.replace("q_", "")
    qualidade = QUALIDADES[qualidade_key]
    url = context.user_data.get("url")
    is_playlist = context.user_data.get("is_playlist", False)

    await query.edit_message_text(
        f"⏳ Baixando em *{qualidade['label']}*...\n"
        + ("📋 Isso pode demorar um pouco para playlists." if is_playlist else ""),
        parse_mode="Markdown"
    )

    await processar_download(query, context, url, qualidade["quality"], is_playlist)

# ─── Faz o download e envia ───────────────────────────────────────────────────
async def processar_download(query, context, url, quality, is_playlist):
    base_path = f"audio_{query.message.chat_id}_{query.message.message_id}"

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": base_path + "_%(autonumber)s" if is_playlist else base_path,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": quality,
        }],
        "quiet": True,
        "noplaylist": not is_playlist,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)

        # Coleta os arquivos gerados
        if is_playlist:
            entries = info.get("entries", [])
            arquivos = sorted([
                f for f in os.listdir(".")
                if f.startswith(os.path.basename(base_path)) and f.endswith(".mp3")
            ])
            titulos = [e.get("title", f"Faixa {i+1}") for i, e in enumerate(entries)]
        else:
            arquivos = [base_path + ".mp3"]
            titulos = [info.get("title", "audio")]

        total = len(arquivos)

        for i, (arquivo, titulo) in enumerate(zip(arquivos, titulos), 1):
            if not os.path.exists(arquivo):
                continue

            # Aviso de progresso para playlists
            if is_playlist:
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=f"📤 Enviando {i}/{total}: *{titulo}*",
                    parse_mode="Markdown"
                )

            await context.bot.send_audio(
                chat_id=query.message.chat_id,
                audio=open(arquivo, "rb"),
                title=titulo,
                filename=f"{titulo}.mp3"
            )
            os.remove(arquivo)

        if is_playlist:
            await context.bot.send_message(
                chat_id=query.message.chat_id,
                text=f"✅ Playlist concluída! {total} faixas enviadas."
            )

    except Exception as e:
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=f"❌ Erro ao baixar: {str(e)}"
        )
        # Limpa arquivos em caso de erro
        for f in os.listdir("."):
            if f.startswith(os.path.basename(base_path)) and f.endswith(".mp3"):
                os.remove(f)

# ─── Inicialização ────────────────────────────────────────────────────────────
app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receber_link))
app.add_handler(CallbackQueryHandler(escolher_qualidade, pattern="^q_"))
app.run_polling()
```

---

## `requirements.txt`
```
python-telegram-bot==20.7
yt-dlp
```

---

## `Procfile` (para o Railway)
```
worker: python bot.py
```

---

## Como subir no Railway

**1. Crie o repositório no GitHub** com os 3 arquivos acima.

**2. No Railway:**
- Acesse [railway.app](https://railway.app) e faça login com GitHub
- Clique em **New Project → Deploy from GitHub repo**
- Selecione seu repositório

**3. Adicione a variável de ambiente:**
- Vá em **Variables** e adicione:
```
  TOKEN = seu_token_aqui
```

**4. Adicione o FFmpeg:**
- Vá em **Settings → Nixpacks** e adicione o pacote:
```
  ffmpeg