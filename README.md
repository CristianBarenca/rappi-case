# Repositorio con la solución a un caso técnico para el puesto de AI Engineer en Rappi 💼

**Contexto del Problema**

Rappi opera flotas de repartidores en tiempo real en cientos de zonas a través de 9 países. El equipo de Operations depende de la disponibilidad de repartidores conectados para atender la demanda de órdenes de forma sostenible. Cuando la oferta de repartidores y la demanda de órdenes no están balanceadas, se generan dos tipos de problemas:

* Saturación: demasiadas órdenes relativas a repartidores disponibles — clientes esperan más tiempo, órdenes se pierden, NPS cae.

* Sobre-oferta: demasiados repartidores activos con pocas órdenes — ineficiencia operacional, costo sin retorno.

La métrica central de balance operacional es:

```
Ratio = Órdenes / Repartidores Conectados   
< 0.5: Sobre-oferta (ineficiencia de costo)   
 0.9 – 1.2: Rango saludable    
> 1.8: SATURACIÓN (pérdida de órdenes)
```

El caso está dividido en tres módulos progresivos. El Módulo 1 es el fundamento analítico: sin él, los Módulos 2 y 3 no tienen base. Prioriza en ese orden.

---

### Recrea el ambiente para la reproducibilidad del proyecto

1. Ve a anaconda navegator.
2. Selecciona la opción de ```Environments```
3. Has clic en el boton import.
4. Selecciona la opción Local drive.
5. Busca el archivo [environment.yaml](environment.yaml)
6. Finalmente has clic en el boton import y listo. 

---
### Estrcutura del repositorio

```
El equipo de Operations actualmente gestiona el balance de forma reactiva.

Nuestra misión es construir un sistema que lo haga de forma proactiva: detectar condiciones que degradarán la operación antes de que ocurran, y enviar alertas accionables con recomendaciones concretas al equipo a través de Telegram.

La estructura que queremos que tenga este repositorio es la siguiente:

rappi-case
│
├─ environment.yaml <-
├─ LICENSE
├─ main_pipeline.py
│
├─ modulo1_diagnostico
│  ├─ diagnostico.ipynb
│  ├─ README.md
│  ├─ Resumen de hallazgos
│  │  └─ Resumen de hallazgos.pdf
│  └─ Visualizaciones para cada hallazgo
│     ├─ EDA
│     │  ├─ 1.Variables_categóricas_conteo_DATE.png
│     │  ├─ 1.Variables_categóricas_conteo_RATIO_CATEGORY.png
│     │  ├─ 1.Variables_categóricas_conteo_ZONE.png
│     │  ├─ 2.Variables_numéricas_conteo_RATIO.png
│     │  ├─ 3.Correlacion_Pearson.png
│     │  └─ 4.Correlacion_en_visual.png
│     ├─ P1
│     │  └─ P1_heatmap_saturacion_critica_mayor_1_8.png
│     ├─ P2
│     │  └─ Heatmap_de_saturación_por_hora_y_zona.png
│     ├─ P3
│     │  └─ P3.Promedio_de_saturacion_por_zona_(horizontal).png
│     ├─ P4
│     │  └─ P4.Deteccion_de_Gasto_Ineficiente_Dias_con_Sobrecostos_y_Baja_Demanda.png
│     └─ P5
│        └─ P5.Earnings promedio por nivel de saturacion.png
│
├─ modulo2_motor_alertas
│  ├─ Justificación_de_los_umbrales_y_reglas_del_motor.pdf
│  ├─ motor_alertas.py
│  ├─ Original-Monolito-Motor-Alertas.py
│  └─ README.md
│
├─ modulo3_agente_telegram
│  ├─ alerts_notify.py
│  └─ README.md
│
├─ README.md 
└─ requirements.txt

```


# Anexos 

### ¿Cómo crear el ambiente de conda?
Con base en (CONDA, 2026), nombre mi ambiente de desarrollo como: rappi_ai_project_py310 el cual contiene el nombre de la empresa, el puesto, proyecto y la version de Python que estoy utilizando en este caso 3.10, ya que este proyecto sera escalable al integrar la libreria LangChain, la cual esta disponible en la version 3.10 y posteriores (LangChain, 2026).

“Se selecciona Python 3.11 como versión base del proyecto debido a su compatibilidad completa con el stack propuesto (LangChain, requests, Telegram API, pandas, seaborn, matplotlib), su mejora significativa de rendimiento respecto a 3.10, y su soporte oficial hasta octubre de 2027, lo que garantiza estabilidad, escalabilidad y facilidad de mantenimiento a largo plazo.”


Bibliografia

1. ¿Cómo crear un ambiente en Anaconda navegator?
https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html

2. How To install LangChain
https://docs.langchain.com/oss/python/langchain/install