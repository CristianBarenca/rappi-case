import asyncio
import logging
from telegram import Bot
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from credentials import TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, GOOGLE_API_KEY

# -------------------------
# CONFIGURACIÓN
# -------------------------
#TELEGRAM_TOKEN = ""
#TELEGRAM_CHAT_ID = ""
#GOOGLE_API_KEY = ""

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TELEGRAM_TOKEN)
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.3, google_api_key=GOOGLE_API_KEY)

# -------------------------
# FUNCIONES
# -------------------------
def generate_alert_msg(alert, secondary_zones=None):
    secondary_zones = secondary_zones or ["Sin zonas secundarias"]
    messages = [
        SystemMessage(content=(
            "Genera un mensaje de alerta para un Operations Manager debe incluir: zona y nivel de riesgo, "
            "qué se espera que pase, acción concreta con números, ventana de tiempo, "
            "zonas secundarias afectadas."
        )),
        HumanMessage(content=f"""
Zona: {alert['zone']}
Precipitación: {alert['precip']} mm/hr
Riesgo: {alert['risk']}
Ratio proyectado: {alert['ratio']}
Earnings: de {alert['earnings_from']} a {alert['earnings_to']} MXN
Ventana: 30 min
Zonas secundarias: {', '.join(secondary_zones)}
Genera un mensaje listo para Telegram.
""")
    ]
    try:
        response = llm.invoke(messages)
        return response.content.strip()
    except:
        return f"⚠️ {alert['zone']} | lluvia {alert['precip']} mm | riesgo {alert['risk']}"

async def send_telegram_async(msg):
    try:
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=msg)
        logging.info(f"Mensaje enviado ✅: {msg}")
    except Exception as e:
        logging.error(f"Telegram error: {e}")

# -------------------------
# CONSUMER
# -------------------------
async def alerts_consumer(queue: asyncio.Queue):
    logging.info("Alert consumer started...")
    while True:
        alert = await queue.get()
        try:
            msg = generate_alert_msg(alert, secondary_zones=["Carretera Nacional", "Santa Catarina"])
            await send_telegram_async(msg)
        except Exception as e:
            logging.error(f"Consumer error: {e}")
        finally:
            queue.task_done()