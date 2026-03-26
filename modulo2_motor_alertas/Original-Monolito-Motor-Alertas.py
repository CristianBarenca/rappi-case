import asyncio
import logging
import pandas as pd
import requests
from shapely.wkt import loads
from datetime import datetime, timedelta
import numpy as np
from telegram import Bot
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage

# -------------------------
# CONFIGURACIÓN
# -------------------------
TELEGRAM_TOKEN = ""
TELEGRAM_CHAT_ID = ""
GOOGLE_API_KEY = ""
CHECK_INTERVAL_MINUTES = 30

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TELEGRAM_TOKEN)
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0.3,
    google_api_key=GOOGLE_API_KEY
)

# -------------------------
#  MODO PRODUCCIÓN
# -------------------------
# En producción, descomenta
# FORCE_RAIN = False
# FORCED_PRECIP_MM = 0

# -------------------------
# VARIABLES DE PRUEBA
# -------------------------
# Para pruebas locales, simula lluvia
# Descomenta para probar el flujo sin depender del clima real
FORCE_RAIN = True
FORCED_PRECIP_MM = 6

# -------------------------
# CARGA DE DATOS
# -------------------------
df = pd.read_excel("../rappi_delivery_case_data.xlsx", sheet_name="RAW_DATA")
zones = pd.read_excel("../rappi_delivery_case_data.xlsx", sheet_name="ZONE_INFO")
polygons_df = pd.read_excel("../rappi_delivery_case_data.xlsx", sheet_name="ZONE_POLYGONS")

def safe_load_wkt(wkt):
    try:
        if pd.isna(wkt):
            return None
        wkt = str(wkt).strip()
        if not wkt.startswith("POLYGON"):
            return None
        return loads(wkt)
    except Exception as e:
        logging.warning(f"WKT error: {e}")
        return None

polygons_df["geometry"] = polygons_df["GEOMETRY_WKT"].apply(safe_load_wkt)
polygons_df = polygons_df.dropna(subset=["geometry"])

# -------------------------
# FEATURE ENGINEERING
# -------------------------
df = df[df["CONNECTED_RT"] > 0].copy()
df["SUPPLY_DEMAND_RATIO"] = df["ORDERS"] / df["CONNECTED_RT"]

baseline_ratio = df["SUPPLY_DEMAND_RATIO"].quantile(0.75)

precip_bins = [0,1,2,3,4,5,6,7,10,20]
grouped = df.groupby(pd.cut(df["PRECIPITATION_MM"], bins=precip_bins))["SUPPLY_DEMAND_RATIO"].mean()

PRECIP_THRESHOLD = 2
for bin_range, ratio in grouped.items():
    if ratio > baseline_ratio:
        PRECIP_THRESHOLD = bin_range.left
        break

stress = df[df["SUPPLY_DEMAND_RATIO"] > 1.5]
MULTIPLIER = (
    stress["EARNINGS"].mean() / df["EARNINGS"].mean()
    if len(stress) > 0 else 1.4
)

alert_history = {}

# -------------------------
# FUNCIONES AUXILIARES
# -------------------------
def get_forecast(lat, lon):
    try:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat,
            "longitude": lon,
            "hourly": "precipitation",
            "forecast_days": 1
        }
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logging.error(f"Weather API error: {e}")
        return None

def evaluate_zone(zone_name, forecast_mm):
    zone_data = df[df["ZONE"] == zone_name]
    if zone_data.empty:
        return None

    base_earnings = zone_data["EARNINGS"].mean()
    corr = zone_data["PRECIPITATION_MM"].corr(zone_data["SUPPLY_DEMAND_RATIO"])

    local_threshold = PRECIP_THRESHOLD
    if corr is not None:
        if corr > 0.4:
            local_threshold = max(1, PRECIP_THRESHOLD - 1)
        elif corr < 0.2:
            local_threshold = PRECIP_THRESHOLD + 1

    if forecast_mm < local_threshold:
        return None

    projected_ratio = 1.0 + (forecast_mm / local_threshold) * 0.8
    risk = "ALTO" if projected_ratio > 1.7 else "MEDIO"
    new_earnings = int(base_earnings * MULTIPLIER)

    now = datetime.now()
    if zone_name in alert_history:
        last_time, last_precip = alert_history[zone_name]
        if (now - last_time < timedelta(hours=2)) and (forecast_mm <= last_precip * 1.2):
            return None
    alert_history[zone_name] = (now, forecast_mm)

    return {
        "zone": zone_name,
        "precip": round(forecast_mm, 1),
        "risk": risk,
        "ratio": round(projected_ratio, 2),
        "earnings_from": int(base_earnings),
        "earnings_to": new_earnings
    }

def generate_alert(alert):
    messages = [
    SystemMessage(content=(
        "Eres un Operations Assistant. Crea un mensaje similar a este:\n"
        "Zona: Santiago\n"
        "Precipitación esperada: 7.2 mm/hr en las próximas 2 horas\n"
        "Riesgo: ALTO (ratio proyectado ~1.9 basado en histórico)\n"
        "Acción recomendada: subir earnings de 55 a 78 MXN en los próximos 30 min\n"
        "Zonas secundarias a monitorear: Carretera Nacional, Santa Catarina"
    )),
        HumanMessage(content=f"""
    Zona: {alert['zone']}
    Precipitación: {alert['precip']} mm/hr
    Riesgo: {alert['risk']}
    Ratio: {alert['ratio']}
    Earnings: Subir de {alert['earnings_from']} a {alert['earnings_to']} MXN
    Genera un mensaje corto tipo alerta.
    """)
    ]

    try:
        response = llm.invoke(messages)
        return response.content.strip()
    except Exception as e:
        logging.error(f"LLM error: {e}")
        return f"⚠️ {alert['zone']} | lluvia {alert['precip']} mm | riesgo {alert['risk']}"

# -------------------------
# TELEGRAM ASÍNCRONO
# -------------------------
async def send_telegram_async(msg):
    try:
        await bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=msg)
        logging.info(f"Mensaje enviado ✅: {msg}")
    except Exception as e:
        logging.error(f"Telegram async error: {e}")

def send_telegram(msg):
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        asyncio.create_task(send_telegram_async(msg))
    else:
        asyncio.run(send_telegram_async(msg))

# -------------------------
# EJECUCIÓN SEGURA DE COROUTINES
# -------------------------
def run_async_safe(coro):
    """Ejecuta una coroutine de forma segura, incluso si ya hay un loop activo"""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        return asyncio.create_task(coro)
    else:
        return asyncio.run(coro)

# -------------------------
# LOOP PRINCIPAL ASÍNCRONO
# -------------------------
async def run():
    logging.info("Starting monitoring...")

    while True:
        try:
            for _, row in zones.iterrows():
                forecast = get_forecast(row["LATITUDE_CENTER"], row["LONGITUDE_CENTER"])
                if not forecast or "hourly" not in forecast:
                    continue

                precipitation = forecast["hourly"]["precipitation"]
                next_hours = precipitation[:2]
                if not next_hours:
                    continue

                avg_precip = FORCED_PRECIP_MM if FORCE_RAIN else np.mean(next_hours)
                result = evaluate_zone(row["ZONE"], avg_precip)

                if result:
                    msg = generate_alert(result)
                    send_telegram(msg)
                    logging.info(f"Alert sent: {result['zone']}")

        except Exception as e:
            logging.error(f"Loop error: {e}")

        await asyncio.sleep(CHECK_INTERVAL_MINUTES * 60)

# -------------------------
# EJECUCIÓN
# -------------------------
if __name__ == "__main__":
    try:
        run_async_safe(run())
    except KeyboardInterrupt:
        logging.info("Monitoring stopped manually.")