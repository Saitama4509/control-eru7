import datetime
import json
import os
import re
import streamlit as st

st.set_page_config(
    page_title="Control de Rutas - Nextday ERU7", layout="centered"
)

st.title("📦 Control de rutas Nextday - ERU7 - Villa Mercedes")

DB_FILE = "rutas_db.json"


def cargar_base_datos():
  if os.path.exists(DB_FILE):
    try:
      with open(DB_FILE, "r", encoding="utf-8") as f:
        datos = json.load(f)
        for fecha, rutas in datos.items():
          for r_name, r_data in rutas.items():
            if "parada_idx" not in r_data:
              r_data["parada_idx"] = 0
            if "faltantes" not in r_data:
              r_data["faltantes"] = []
            if "veces_controlada" not in r_data:
              r_data["veces_controlada"] = 0
        return datos
    except:
      return {}
  return {}


def guardar_base_datos(datos):
  with open(DB_FILE, "w", encoding="utf-8") as f:
    json.dump(datos, f, ensure_ascii=False, indent=4)


if "rutas_por_fecha" not in st.session_state:
  st.session_state.rutas_por_fecha = cargar_base_datos()

if "ruta_seleccionada" not in st.session_state:
  st.session_state.ruta_seleccionada = None
if "fecha_activa_control" not in st.session_state:
  st.session_state.fecha_activa_control = None
if "admin_logueado" not in st.session_state:
  st.session_state.admin_logueado = False

# Control para limpiar el cuadro de texto de carga automáticamente
if "texto_ruta_input" not in st.session_state:
  st.session_state.texto_ruta_input = ""


# --- ORDENAMIENTO NUMÉRICO INTELIGENTE (F1, F2... F10, F11) ---
def clave_orden_natural(nombre_ruta):
  # Extrae todas las partes de texto y números para ordenar matemáticamente
  partes = re.findall(r"(\d+|\D+)", nombre_ruta)
  return [int(p) if p.isdigit() else p.lower() for p in partes]


# --- FUNCIÓN INTELIGENTE: EXTRAE NOMBRE Y PARADAS ---
def procesar_texto_completo(texto_crudo):
  match_nombre = re.search(
      r"(?:Ruta\s+)?([FKM]\d+_[A-Za-z0-9]+)", texto_crudo, re.IGNORECASE
  )
  nombre_ruta = match_nombre.group(1).upper() if match_nombre else "RUTA_NUEVA"

  paradas = []
  lineas = [l.strip() for l in texto_crudo.split("\n") if l.strip()]

  i = 0
  while i < len(lineas):
    if lineas[i].isdigit() and int(lineas[i]) < 300:
      nro_parada = int(lineas[i])
      direccion = "Dirección no especificada"
      paquetes = 1

      if i + 1 < len(lineas):
        direccion = lineas[i + 1]

      for j in range(i + 2, min(i + 6, len(lineas))):
        match_paq = re.search(r"(\d+)\s+paquete", lineas[j], re.IGNORECASE)
        if match_paq:
          paquetes = int(match_paq.group(1))
          break

      paradas.append({"nro": nro_parada, "dir": direccion, "paquetes": paquetes})
    i += 1

  return nombre_ruta, paradas


# --- MENÚ LATERAL SEGURO ---
st.sidebar.subheader("🔒 Acceso al Sistema")
modo_app = st.sidebar.radio(
    "Seleccionar Vista:", ["👷‍♂️ Panel de Operadores", "⚙️ Carga (Admin)"]
)

st.sidebar.write("---")
st.sidebar.subheader("📅 Fecha de Operación")
fecha_hoy = datetime.date.today()
fecha_seleccionada = st.sidebar.date_input(
    "Seleccionar Día", value=fecha_hoy, key="selector_fecha_global"
)
fecha_str = str(fecha_seleccionada)

if fecha_str not in st.session_state.rutas_por_fecha:
  st.session_state.rutas_por_fecha[fecha_str] = {}

rutas_dia_actual = st.session_state.rutas_por_fecha[fecha_str]

# --- VISTA 1: ZONA DE CARGA PROTEGIDA POR PIN ---
if modo_app == "⚙️ Carga (Admin)":
  st.subheader("🔐 Área de Administración de Rutas")

  PIN_SECRETO = "2026"

  if not st.session_state.admin_logueado:
    pin_ingresado = st.text_input(
        "Ingresá el PIN de Administrador para desbloquear la carga:",
        type="password",
    )
    if st.button("Ingresar", type="primary"):
      if pin_ingresado == PIN_SECRETO:
        st.session_state.admin_logueado = True
        st.rerun()
      else:
        st.error("PIN incorrecto.")
  else:
    st.success("🔓 Modo Administrador Activo")
    if st.button("Cerrar sesión de Admin"):
      st.session_state.admin_logueado = False
      st.rerun()

    st.write("---")
    st.subheader(f"📥 Cargar Ruta para el día: {fecha_str}")

    st.markdown("##### 📊 Control Visual de Rutas Cargadas:")
    if rutas_dia_actual:
      cols_resumen = st.columns(4)
      idx_col = 0
      # ORDENAMIENTO NATURAL EN EL PANEL VISUAL
      rutas_ordenadas_keys = sorted(
          rutas_dia_actual.keys(), key=clave_orden_natural
      )
      for r_name in rutas_ordenadas_keys:
        r_info = rutas_dia_actual[r_name]
        est = r_info["estado"]
        veces = r_info.get("veces_controlada", 0)
        if est == "Disponible":
          icon = "🟢"
        elif est == "En Control":
          icon = "🟡"
        else:
          icon = f"✅ ({veces})"

        with cols_resumen[idx_col % 4]:
          st.markdown(f"`{r_name}` {icon}")
        idx_col += 1
    else:
      st.info("Todavía no hay rutas cargadas para esta fecha.")
    st.write("---")

    # Cuadro de texto vinculado al session_state para poder limpiarlo automáticamente
    texto_pegado = st.text_area(
        "Pegá el texto completo de la plataforma aquí:",
        key="texto_ruta_input",
        height=220,
    )

    if st.button("Procesar y Publicar Ruta", type="primary"):
      if texto_pegado:
        nombre_detectado, paradas_extraidas = procesar_texto_completo(
            texto_pegado
        )

        if paradas_extraidas:
          if nombre_detectado in rutas_dia_actual:
            st.error(
                f"⚠️ ¡Atención! La ruta **{nombre_detectado}** ya se encuentra"
                f" cargada para la fecha {fecha_str}."
            )
          else:
            rutas_dia_actual[nombre_detectado] = {
                "estado": "Disponible",
                "paradas": paradas_extraidas,
                "parada_idx": 0,
                "faltantes": [],
                "veces_controlada": 0,
            }
            guardar_base_datos(st.session_state.rutas_por_fecha)

            # LIMPIAR EL TEXTO AUTOMÁTICAMENTE
            st.session_state.texto_ruta_input = ""

            st.success(
                f"¡Éxito! Ruta **{nombre_detectado}** guardada permanentemente"
                f" para el **{fecha_str}** ({len(paradas_extraidas)} paradas)."
            )
            st.rerun()
        else:
          st.error(
              "No se pudieron extraer las paradas. Verificá el formato del texto."
          )
      else:
        st.warning("Por favor pegá el texto de la ruta.")

# --- VISTA 2: PANEL DE OPERADORES ---
else:
  if st.session_state.ruta_seleccionada is None:
    st.subheader(f"🔍 Rutas Disponibles para Controlar ({fecha_str}):")

    if not rutas_dia_actual:
      st.warning(
          f"⚠️ No hay rutas cargadas para la fecha {fecha_str} todavía."
      )
    else:
      # ORDENAMIENTO NATURAL EN EL PANEL DE OPERADORES
      rutas_ordenadas_keys = sorted(
          rutas_dia_actual.keys(), key=clave_orden_natural
      )
      for nombre_ruta in rutas_ordenadas_keys:
        data = rutas_dia_actual[nombre_ruta]
        col1, col2, col3 = st.columns([2, 1, 1])

        estado = data.get("estado", "Disponible")
        veces = data.get("veces_controlada", 0)
        progreso_actual = data.get("parada_idx", 0)
        total_paradas = len(data.get("paradas", []))

        with col1:
          st.write(
              f"**{nombre_ruta}** — *{total_paradas} paradas*"
              f" {f'(Progreso: {progreso_actual}/{total_paradas})' if progreso_actual > 0 else ''}"
          )
        with col2:
          if estado == "Disponible":
            st.success("Disponible")
          elif estado == "En Control":
            st.warning("En Proceso 🟡")
          else:
            st.info(f"Revisada ({veces} 🔄)")

        with col3:
          if estado in ["Disponible", "En Control", "Volver a Controlar"]:
            if estado == "Disponible":
              texto_boton = "Tomar Ruta"
            elif estado == "En Control":
              texto_boton = "Continuar 🟡"
            else:
              texto_boton = "Recontrolar 🔄"

            if st.button(
                texto_boton, key=f"btn_{fecha_str}_{nombre_ruta}"
            ):
              rutas_dia_actual[nombre_ruta]["estado"] = "En Control"
              guardar_base_datos(st.session_state.rutas_por_fecha)
              st.session_state.ruta_seleccionada = nombre_ruta
              st.session_state.fecha_activa_control = fecha_str
              st.rerun()

  # --- CONTROL PASO A PASO DEL OPERADOR ---
  else:
    fecha_activa = st.session_state.fecha_activa_control
    ruta_activa = st.session_state.ruta_seleccionada
    datos_ruta = st.session_state.rutas_por_fecha[fecha_activa][ruta_activa]
    paradas = datos_ruta.get("paradas", [])
    idx = datos_ruta.get("parada_idx", 0)

    st.markdown(f"### 🚚 Controlando: `{ruta_activa}` ({fecha_activa})")

    if idx < len(paradas):
      parada = paradas[idx]

      st.progress((idx) / len(paradas))
      st.write(f"Progreso de descarga: Parada {idx + 1} de {len(paradas)}")

      st.markdown(f"#### Parada N° {parada['nro']}")
      st.info(f"**Dirección:** {parada['dir']}")
      st.warning(f"**Paquetes a bajar:** {parada['paquetes']}")

      col1, col2, col3 = st.columns(3)

      with col1:
        if st.button(
            "⬅️ Anterior",
            disabled=(idx == 0),
            use_container_width=True,
        ):
          if idx > 0:
            datos_ruta["parada_idx"] -= 1
            guardar_base_datos(st.session_state.rutas_por_fecha)
            st.rerun()

      with col2:
        if st.button(
            "✔ Todo OK / Siguiente", type="primary", use_container_width=True
        ):
          datos_ruta["parada_idx"] += 1
          guardar_base_datos(st.session_state.rutas_por_fecha)
          st.rerun()

      with col3:
        if st.button(
            "⚠️ Falta Paquete", type="secondary", use_container_width=True
        ):
          if parada["nro"] not in datos_ruta.get("faltantes", []):
            datos_ruta.setdefault("faltantes", []).append(parada["nro"])
          datos_ruta["parada_idx"] += 1
          guardar_base_datos(st.session_state.rutas_por_fecha)
          st.rerun()

      st.write("---")
      if st.button("❌ Guardar y Salir (Continuar luego)"):
        guardar_base_datos(st.session_state.rutas_por_fecha)
        st.session_state.ruta_seleccionada = None
        st.rerun()

    else:
      st.success("¡Ruta controlada y finalizada con éxito!")
      faltantes_fin = datos_ruta.get("faltantes", [])
      if faltantes_fin:
        st.error(f"Faltantes registrados en paradas: {faltantes_fin}")
      else:
        st.balloons()

      datos_ruta["estado"] = "Volver a Controlar"
      datos_ruta["veces_controlada"] = (
          datos_ruta.get("veces_controlada", 0) + 1
      )
      datos_ruta["parada_idx"] = 0
      guardar_base_datos(st.session_state.rutas_por_fecha)

      if st.button("Volver al listado general de rutas", type="primary"):
        st.session_state.ruta_seleccionada = None
        st.rerun()
