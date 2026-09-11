"""
App básica de Streamlit — Nivel de ríos/quebradas (CORNARE / MARCO)
--------------------------------------------------------------------
Cada estudiante debe cambiar, como mínimo, el código de la estación
en el sidebar. Los valores de fecha y calidad también son ajustables.

Para correrla:
    streamlit run app_nivel_cornare.py
"""

import requests
import pandas as pd
import numpy as np
import streamlit as st
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ------------------------------------------------------------------
# Coordenadas por defecto
# ------------------------------------------------------------------
LAT_DEFECTO = 6.3929
LON_DEFECTO = -75.2595

API_BASE_URL = "https://marco.cornare.gov.co/api/v1/estaciones"

LLAVE_FECHA = "level_date"
LLAVE_VALOR = "level"
CANDIDATOS_LAT = ["lat", "latitude", "latitud"]
CANDIDATOS_LON = ["lng", "lon", "longitude", "longitud"]

st.set_page_config(
    page_title="Concepción, Río Concepción, Barrio Obrero",
    page_icon="🌊",
    layout="wide"
)


# ------------------------------------------------------------------
# Funciones de consulta
# ------------------------------------------------------------------

def obtener_serie_nivel(codigo_estacion, desde, hasta, calidad=1, timeout=30):

    url = f"{API_BASE_URL}/{codigo_estacion}/nivel"

    params = {
        "desde": desde,
        "hasta": hasta,
        "calidad": calidad
    }

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
        "Accept": "application/json, text/plain, */*",
    }

    try:

        resp = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=timeout,
            verify=False
        )

        if resp.status_code == 200:
            return resp.json(), None

        return None, f"HTTP {resp.status_code}"

    except requests.exceptions.RequestException as e:

        return None, f"Error de red: {e}"


def obtener_todas_las_paginas(datos_json, timeout=30):

    registros = list(datos_json.get("values", []))

    siguiente_url = datos_json.get("next")

    while siguiente_url:

        try:

            resp = requests.get(
                siguiente_url,
                timeout=timeout,
                verify=False
            )

        except requests.exceptions.RequestException:
            break

        if resp.status_code != 200:
            break

        pagina = resp.json()

        registros.extend(
            pagina.get("values", [])
        )

        siguiente_url = pagina.get("next")

    return registros


def detectar_coordenadas(datos_json):

    if not isinstance(datos_json, dict):
        return LAT_DEFECTO, LON_DEFECTO, False

    lat = next(
        (datos_json[k] for k in CANDIDATOS_LAT if k in datos_json),
        None
    )

    lon = next(
        (datos_json[k] for k in CANDIDATOS_LON if k in datos_json),
        None
    )

    if lat is not None and lon is not None:

        try:
            return float(lat), float(lon), True

        except (TypeError, ValueError):
            pass

    return LAT_DEFECTO, LON_DEFECTO, False


def calcular_indice_calidad(df):

    if df.empty or len(df) < 2:
        return 0.0, 0, 0

    df_idx = df.set_index("fecha")

    frecuencia_tipica = (
        df["fecha"].diff().dropna().mode()
    )

    if len(frecuencia_tipica) == 0:
        return 0.0, 0, 0

    frecuencia_tipica = frecuencia_tipica[0]

    rango_completo = pd.date_range(
        start=df_idx.index.min(),
        end=df_idx.index.max(),
        freq=frecuencia_tipica
    )

    esperados = len(rango_completo)

    huecos = esperados - len(df_idx)

    completitud = max(
        0.0,
        1 - (huecos / esperados)
    ) if esperados > 0 else 0.0

    Q1 = df["nivel"].quantile(0.25)
    Q3 = df["nivel"].quantile(0.75)

    IQR = Q3 - Q1

    lim_inf = Q1 - 1.5 * IQR
    lim_sup = Q3 + 1.5 * IQR

    es_outlier = (
        (df["nivel"] < lim_inf) |
        (df["nivel"] > lim_sup) |
        (df["nivel"] < 0)
    )

    proporcion_outliers = es_outlier.mean()

    indice = (
        completitud * 0.7 +
        (1 - proporcion_outliers) * 0.3
    ) * 100

    return (
        round(indice, 1),
        int(huecos),
        int(es_outlier.sum())
    )


# ------------------------------------------------------------------
# Sidebar — parámetros de la consulta
# ------------------------------------------------------------------

st.sidebar.header("Parámetros de tu consulta")

nombre_estudiante = st.sidebar.text_input(
    "Nombre del estudiante",
    "Tu Nombre Aquí"
)

codigo_estacion = st.sidebar.text_input(
    "Código de estación",
    "42"
)

fecha_desde = st.sidebar.date_input(
    "Desde",
    pd.to_datetime("2026-08-23")
).strftime("%Y-%m-%d")

fecha_hasta = st.sidebar.date_input(
    "Hasta",
    pd.to_datetime("2026-08-30")
).strftime("%Y-%m-%d")

calidad = st.sidebar.selectbox(
    "Calidad",
    [1, 0],
    index=0,
    help="1 = solo datos validados"
)


# ==============================================================
# 🟢 NUEVO 2: CONFIGURACIÓN DE ALERTAS
# ==============================================================

st.sidebar.subheader("🚨 Parámetros de alerta")

nivel_alto = st.sidebar.number_input(
    "Nivel alto",
    min_value=0.0,
    value=1.50,
    step=0.10
)

nivel_bajo = st.sidebar.number_input(
    "Nivel bajo",
    min_value=0.0,
    value=0.30,
    step=0.10
)


consultar = st.sidebar.button(
    "🔍 Consultar",
    type="primary"
)


# ------------------------------------------------------------------
# Título
# ------------------------------------------------------------------

st.title("🌊 Concepción, Río Concepción, Barrio Obrero")

st.caption(
    f"Estudiante: **{nombre_estudiante}** · "
    f"Estación: **{codigo_estacion}**"
)


# ==============================================================
# 🟢 NUEVO 3: IMAGEN
# ==============================================================

st.image(
    "imagen_rio.jpg",
    caption="Río Concepción - Barrio Obrero",
    use_container_width=True
)


# ------------------------------------------------------------------
# Consulta y procesamiento
# ------------------------------------------------------------------

if consultar:

    with st.spinner("Consultando la API..."):

        datos_crudos, error = obtener_serie_nivel(
            codigo_estacion,
            fecha_desde,
            fecha_hasta,
            calidad
        )

    if error:

        st.error(f"❌ {error}")

    else:

        registros = obtener_todas_las_paginas(
            datos_crudos
        )

        if not registros:

            st.warning(
                "No hay registros para esta estación y rango de fechas. "
                "Prueba otro código u otro rango."
            )

        else:

            df = pd.DataFrame(registros)

            df = df.rename(
                columns={
                    LLAVE_FECHA: "fecha",
                    LLAVE_VALOR: "nivel"
                }
            )

            df["fecha"] = pd.to_datetime(
                df["fecha"],
                errors="coerce"
            )

            df["nivel"] = pd.to_numeric(
                df["nivel"],
                errors="coerce"
            )

            df = (
                df.dropna(
                    subset=["fecha", "nivel"]
                )
                .sort_values("fecha")
                .reset_index(drop=True)
            )


            # ======================================================
            # 🟢 NUEVO 4: DETECTAR PICOS ALTOS Y BAJOS
            # ======================================================

            picos_altos = df[
                df["nivel"] >= nivel_alto
            ].copy()

            picos_bajos = df[
                df["nivel"] <= nivel_bajo
            ].copy()


            # ------------------------------------------------------------------
            # Coordenadas
            # ------------------------------------------------------------------

            lat, lon, coords_reales = detectar_coordenadas(
                datos_crudos
            )

            indice_calidad, huecos, n_outliers = (
                calcular_indice_calidad(df)
            )


            # ------------------------------------------------------------------
            # Métricas principales
            # ------------------------------------------------------------------

            col1, col2, col3, col4 = st.columns(4)

            col1.metric(
                "Lecturas",
                len(df)
            )

            col2.metric(
                "Nivel promedio",
                f"{df['nivel'].mean():.2f}"
            )

            col3.metric(
                "Índice de calidad",
                f"{indice_calidad} / 100"
            )

            col4.metric(
                "Outliers detectados",
                n_outliers
            )


            # ======================================================
            # 🟢 NUEVO 5: ALERTAS
            # ======================================================

            st.subheader("🚨 Alertas del nivel del río")

            if not picos_altos.empty:

                st.error(
                    f"🔴 ALERTA: Se detectaron "
                    f"**{len(picos_altos)} picos altos** "
                    f"por encima de {nivel_alto:.2f}."
                )

            else:

                st.success(
                    f"🟢 No se detectaron niveles altos "
                    f"por encima de {nivel_alto:.2f}."
                )


            if not picos_bajos.empty:

                st.warning(
                    f"🔵 ATENCIÓN: Se detectaron "
                    f"**{len(picos_bajos)} niveles bajos** "
                    f"por debajo de {nivel_bajo:.2f}."
                )

            else:

                st.success(
                    f"🟢 No se detectaron niveles bajos "
                    f"por debajo de {nivel_bajo:.2f}."
                )


            # ======================================================
            # 🟢 NUEVO 6: GRÁFICO CON LÍMITES DE ALERTA
            # ======================================================

            st.subheader(
                "📈 Serie de nivel y límites de alerta"
            )

            grafico = df.set_index("fecha")[
                ["nivel"]
            ].copy()

            grafico["Alerta alta"] = nivel_alto

            grafico["Alerta baja"] = nivel_bajo

            st.line_chart(grafico)


            # ======================================================
            # 🟢 NUEVO 7: TABLA DE PICOS
            # ======================================================

            st.subheader("📊 Picos detectados")

            col1, col2 = st.columns(2)

            with col1:

                st.write("🔴 **Picos altos**")

                if not picos_altos.empty:

                    st.dataframe(
                        picos_altos[
                            ["fecha", "nivel"]
                        ],
                        use_container_width=True
                    )

                else:

                    st.info(
                        "No se encontraron picos altos."
                    )


            with col2:

                st.write("🔵 **Picos bajos**")

                if not picos_bajos.empty:

                    st.dataframe(
                        picos_bajos[
                            ["fecha", "nivel"]
                        ],
                        use_container_width=True
                    )

                else:

                    st.info(
                        "No se encontraron niveles bajos."
                    )


            # ======================================================
            # 🟢 NUEVO 8: RESUMEN AUTOMÁTICO
            # ======================================================

            st.subheader("📝 Resumen de la medición")

            nivel_maximo = df["nivel"].max()
            nivel_minimo = df["nivel"].min()
            nivel_promedio = df["nivel"].mean()

            fecha_maximo = df.loc[
                df["nivel"].idxmax(),
                "fecha"
            ]

            st.write(
                f"""
                Durante el período analizado se registraron
                **{len(df)} lecturas**. El nivel promedio fue de
                **{nivel_promedio:.2f}**, con un nivel máximo de
                **{nivel_maximo:.2f}** registrado el
                **{fecha_maximo}**.

                El nivel mínimo registrado fue de
                **{nivel_minimo:.2f}**.
                """
            )


            # ------------------------------------------------------------------
            # Mapa de la estación
            # ------------------------------------------------------------------

            st.subheader(
                "📍 Ubicación de la estación"
            )

            if not coords_reales:

                st.caption(
                    "La API no trajo latitud/longitud de la estación. "
                    "Se muestra el punto de partida."
                )

            st.map(
                pd.DataFrame({
                    "lat": [lat],
                    "lon": [lon]
                }),
                zoom=10
            )


            # ------------------------------------------------------------------
            # Detalle de calidad
            # ------------------------------------------------------------------

            with st.expander(
                "Detalle del índice de calidad"
            ):

                st.write(
                    f"- Huecos de reporte detectados: "
                    f"**{huecos}**"
                )

                st.write(
                    f"- Outliers (IQR + nivel negativo): "
                    f"**{n_outliers}** de {len(df)} lecturas"
                )

                st.write(
                    "El índice combina completitud de la serie "
                    "(70%) y proporción de datos sin outliers (30%)."
                )


            # ------------------------------------------------------------------
            # Tabla y descarga
            # ------------------------------------------------------------------

            with st.expander(
                "📋 Ver datos crudos"
            ):

                st.dataframe(
                    df,
                    use_container_width=True
                )


            csv = df.to_csv(
                index=False
            ).encode("utf-8")

            st.download_button(
                "⬇️ Descargar CSV",
                csv,
                file_name=f"nivel_estacion_{codigo_estacion}.csv",
                mime="text/csv"
            )

else:

    st.info(
        "Ajusta los parámetros en el sidebar "
        "y presiona **Consultar**."
    )
