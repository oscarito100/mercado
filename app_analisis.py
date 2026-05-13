import streamlit as st
import pandas as pd
import json
import plotly.express as px

# Configuración de página
st.set_page_config(page_title="Análisis de Oferta Académica", page_icon="🎓", layout="wide")

st.title("🎓 Dashboard de Inteligencia Académica")

@st.cache_data
def load_data():
    try:
        df = pd.read_excel("oferta_academica_agrupada.xlsx")
        
        with open("mapeo_carreras.json", "r", encoding="utf-8") as f:
            mapeo_carreras = json.load(f)
            
        with open("mapeo_posgrados.json", "r", encoding="utf-8") as f:
            mapeo_posgrados = json.load(f)
            
        return df, mapeo_carreras, mapeo_posgrados
    except Exception as e:
        st.error(f"Error cargando los archivos: {e}")
        return pd.DataFrame(), {}, {}

df, mapeo_carreras, mapeo_posgrados = load_data()

if df.empty:
    st.warning("No se encontraron los datos. Por favor ejecuta el script de agrupación primero.")
    st.stop()

# Crear pestañas principales
tab1, tab2 = st.tabs(["🔍 Explorar Mercado por Área", "🏢 Análisis Individual de Competidor"])

with tab1:
    st.markdown("### Busca un área específica y descubre cuántas y cuáles escuelas la ofrecen.")
    
    col_filtros1, col_filtros2 = st.columns(2)
    
    with col_filtros1:
        nivel = st.radio("Nivel Educativo:", ["Licenciaturas", "Posgrados"], horizontal=True)

    if nivel == "Licenciaturas":
        prefijo = "Lic: "
        col_cruda = "carreras"
        mapeo_actual = mapeo_carreras
    else:
        prefijo = "Posg: "
        col_cruda = "posgrados"
        mapeo_actual = mapeo_posgrados

    # Obtener todas las áreas disponibles de las columnas generadas
    areas_disponibles = [col.replace(prefijo, "") for col in df.columns if col.startswith(prefijo)]
    areas_disponibles.sort()

    with col_filtros2:
        area_seleccionada = st.selectbox("Selecciona un Área de Estudio:", options=["(Seleccionar)"] + areas_disponibles)

    if area_seleccionada and area_seleccionada != "(Seleccionar)":
        nombre_columna = f"{prefijo}{area_seleccionada}"
        
        # Filtrar solo las escuelas que ofrecen esta área
        df_filtrado = df[df[nombre_columna] == 1].copy()
        
        # --- MÉTRICAS ---
        st.header(f"Estadísticas del Mercado: {area_seleccionada}")
        st.metric(label="Total de Universidades competidoras en esta área", value=len(df_filtrado))
        
        if len(df_filtrado) == 0:
            st.info("Ninguna universidad en la base de datos actual ofrece esta área.")
        else:
            st.divider()
            
            # --- GRÁFICO Y TABLA DE ALCALDÍAS ---
            st.subheader("📍 Distribución de la Oferta por Alcaldía")
            col_graf, col_tabla = st.columns([2, 1])
            
            df_filtrado['alcaldia_busqueda'] = df_filtrado['alcaldia_busqueda'].fillna('No especificada')
            alcaldias_count = df_filtrado.groupby('alcaldia_busqueda').size().reset_index(name='Total de Universidades')
            alcaldias_count = alcaldias_count.sort_values('Total de Universidades', ascending=False)
            
            with col_graf:
                fig = px.bar(
                    alcaldias_count, 
                    x='alcaldia_busqueda', 
                    y='Total de Universidades',
                    text='Total de Universidades',
                    color='alcaldia_busqueda',
                    title=f"Universidades que ofrecen {area_seleccionada} por Alcaldía",
                    labels={'alcaldia_busqueda': 'Alcaldía'},
                    template='plotly_white'
                )
                fig.update_traces(textposition='outside')
                fig.update_layout(showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
                
            with col_tabla:
                st.dataframe(alcaldias_count.set_index('alcaldia_busqueda'), use_container_width=True)

            st.divider()
            
            # --- TABLA DETALLADA ---
            st.subheader("🎓 Detalle del Directorio Escolar")
            
            def encontrar_nombre_original(fila):
                crudo = str(fila.get(col_cruda, ''))
                nombres_encontrados = []
                for elemento in crudo.split(','):
                    limpio = elemento.strip()
                    if mapeo_actual.get(limpio) == area_seleccionada:
                        nombres_encontrados.append(limpio)
                return ", ".join(nombres_encontrados) if nombres_encontrados else "Nombre genérico / Equivalencia"
            
            df_filtrado['Nombre Oficial del Programa'] = df_filtrado.apply(encontrar_nombre_original, axis=1)
            
            columnas_mostrar = ['nombre', 'alcaldia_busqueda', 'Nombre Oficial del Programa', 'website', 'telefono']
            df_mostrar = df_filtrado[columnas_mostrar].rename(columns={
                'nombre': 'Universidad',
                'alcaldia_busqueda': 'Alcaldía',
                'website': 'Sitio Web',
                'telefono': 'Teléfono'
            })
            st.dataframe(
                df_mostrar, 
                use_container_width=True, 
                hide_index=True,
                column_config={
                    "Sitio Web": st.column_config.LinkColumn("Sitio Web", help="Abre el enlace en una pestaña nueva")
                }
            )

with tab2:
    st.markdown("### Selecciona cualquier universidad para conocer su catálogo y qué programas chocan directamente con la UDL.")
    
    # 1. Obtener perfil de la Universidad de Londres
    udl_rows = df[df['nombre'].str.contains('Londres', case=False, na=False)]
    if udl_rows.empty:
        st.warning("No se encontró a la 'Universidad de Londres' en el archivo agrupado.")
    else:
        udl_row = udl_rows.iloc[0]
        # Extraemos las ÁREAS que ofrece la UDL (columnas con 1)
        udl_areas_lic = [col.replace("Lic: ", "") for col in df.columns if col.startswith("Lic: ") and udl_row[col] == 1]
        udl_areas_posg = [col.replace("Posg: ", "") for col in df.columns if col.startswith("Posg: ") and udl_row[col] == 1]
        
        # 2. Selector de competidor
        escuelas_list = df['nombre'].dropna().unique().tolist()
        escuelas_list.sort()
        competidor_nombre = st.selectbox("🏢 Selecciona una Escuela Competidora:", options=["(Seleccionar)"] + escuelas_list)
        
        if competidor_nombre and competidor_nombre != "(Seleccionar)":
            comp_row = df[df['nombre'] == competidor_nombre].iloc[0]
            
            st.header(f"Catálogo de: {competidor_nombre}")
            st.caption("Los programas marcados con 🔥 representan una competencia directa con la Universidad de Londres al pertenecer a la misma área de estudio.")
            
            col_lic, col_posg = st.columns(2)
            
            # --- Tabla de Licenciaturas ---
            with col_lic:
                st.subheader("🎓 Licenciaturas / Carreras")
                carreras_crudas = str(comp_row.get('carreras', ''))
                if carreras_crudas and carreras_crudas.lower() not in ["no disponible", "nan", "error"]:
                    carreras_lista = [c.strip() for c in carreras_crudas.split(',') if c.strip()]
                    
                    datos_lic = []
                    for c in carreras_lista:
                        area = mapeo_carreras.get(c, "")
                        compite = "🔥 Sí" if area in udl_areas_lic else "⬜ No"
                        datos_lic.append({
                            "Programa Oficial": c,
                            "Área Detectada": area if area else "Sin área",
                            "¿Compite con UDL?": compite
                        })
                    
                    df_comp_lic = pd.DataFrame(datos_lic)
                    st.dataframe(df_comp_lic, use_container_width=True, hide_index=True)
                else:
                    st.info("Esta escuela no tiene licenciaturas registradas.")
                    
            # --- Tabla de Posgrados ---
            with col_posg:
                st.subheader("🎓 Posgrados / Especialidades")
                posgrados_crudos = str(comp_row.get('posgrados', ''))
                if posgrados_crudos and posgrados_crudos.lower() not in ["no disponible", "nan", "error"]:
                    posgrados_lista = [p.strip() for p in posgrados_crudos.split(',') if p.strip()]
                    
                    datos_posg = []
                    for p in posgrados_lista:
                        area = mapeo_posgrados.get(p, "")
                        compite = "🔥 Sí" if area in udl_areas_posg else "⬜ No"
                        datos_posg.append({
                            "Programa Oficial": p,
                            "Área Detectada": area if area else "Sin área",
                            "¿Compite con UDL?": compite
                        })
                    
                    df_comp_posg = pd.DataFrame(datos_posg)
                    st.dataframe(df_comp_posg, use_container_width=True, hide_index=True)
                else:
                    st.info("Esta escuela no tiene posgrados registrados.")
