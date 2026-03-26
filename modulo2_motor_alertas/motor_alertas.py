import asyncio
import logging
import pandas as pd
import requests
from shapely.wkt import loads
from datetime import datetime, timedelta
import numpy as np

# -------------------------
# CONFIGURACIÓN
# -------------------------
CHECK_INTERVAL_MINUTES = 30

# -------------------------
# VARIABLES DE PRUEBA
# -------------------------
# Para pruebas locales, simula lluvia
# Descomenta para probar el flujo sin depender del clima real
FORCE_RAIN = True
FORCED_PRECIP_MM = 6


logging.basicConfig(level=logging.INFO)

# -------------------------
# CARGA DE DATOS
# -------------------------
df = pd.read_excel("rappi_delivery_case_data.xlsx", sheet_name="RAW_DATA")
zones = pd.read_excel("rappi_delivery_case_data.xlsx", sheet_name="ZONE_INFO")
polygons_df = pd.read_excel("rappi_delivery_case_data.xlsx", sheet_name="ZONE_POLYGONS")

def safe_load_wkt(wkt):
    try:
        if pd.isna(wkt): return None
        wkt = str(wkt).strip()
        if not wkt.startswith("POLYGON"): return None
        return loads(wkt)
    except:
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
MULTIPLIER = (stress["EARNINGS"].mean() / df["EARNINGS"].mean()) if len(stress) > 0 else 1.4
alert_history = {}

# -------------------------
# FUNCIONES
# -------------------------
def get_forecast(lat, lon):
    try:
        url = "https://api.open-meteo.com/v1/forecast"
        params = {"latitude": lat, "longitude": lon, "hourly": "precipitation", "forecast_days": 1}
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        logging.error(f"Weather API error: {e}")
        return None

def evaluate_zone(zone_name, forecast_mm):
    zone_data = df[df["ZONE"]==zone_name]
    if zone_data.empty: return None

    base_earnings = zone_data["EARNINGS"].mean()
    corr = zone_data["PRECIPITATION_MM"].corr(zone_data["SUPPLY_DEMAND_RATIO"])

    local_threshold = PRECIP_THRESHOLD
    if corr is not None:
        if corr>0.4: local_threshold = max(1, PRECIP_THRESHOLD-1)
        elif corr<0.2: local_threshold = PRECIP_THRESHOLD+1

    if forecast_mm < local_threshold: return None

    projected_ratio = 1.0 + (forecast_mm / local_threshold) * 0.8
    risk = "ALTO" if projected_ratio > 1.7 else "MEDIO"
    new_earnings = int(base_earnings * MULTIPLIER)

    now = datetime.now()
    if zone_name in alert_history:
        last_time, last_precip = alert_history[zone_name]
        if (now - last_time < timedelta(hours=2)) and (forecast_mm <= last_precip * 1.2):
            return None
    alert_history[zone_name] = (now, forecast_mm)

    print('Zona:' + zone_name + ',' +
      'Precipitación esperada ' + str(round(forecast_mm,1)) + ' en las proximas 2 horas,' +
      "Riesgo: " + risk + ',' +
      "(ratio proyectado ~" + str(round(projected_ratio,2)) + ' basado en histórico),' +
      "Acción recomendada: subir earnings de " + str(int(base_earnings)) + ' a ' + str(new_earnings) +
      ' Zonas secundarias a monitorear: Carretera Nacional y Santiago.')

    return {"zone": zone_name, "precip": round(forecast_mm,1), "risk": risk,
            "ratio": round(projected_ratio,2), "earnings_from": int(base_earnings),
            "earnings_to": new_earnings}

# -------------------------
# PRODUCER
# -------------------------
async def alerts_producer(queue: asyncio.Queue):
    logging.info("Alert producer started...")
    while True:
        try:
            for _, row in zones.iterrows():
                forecast = get_forecast(row["LATITUDE_CENTER"], row["LONGITUDE_CENTER"])
                if not forecast or "hourly" not in forecast: continue

                precipitation = forecast["hourly"]["precipitation"][:2]
                if not precipitation: continue

                avg_precip = FORCED_PRECIP_MM if FORCE_RAIN else np.mean(precipitation)
                result = evaluate_zone(row["ZONE"], avg_precip)
                if result:
                    await queue.put(result)
        except Exception as e:
            logging.error(f"Producer loop error: {e}")

        await asyncio.sleep(CHECK_INTERVAL_MINUTES*60)

# -------------------------
# EJECUCIÓN
# -------------------------
if __name__=="__main__":
    queue = asyncio.Queue()
    asyncio.run(alerts_producer(queue))