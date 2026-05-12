import streamlit as st
import pandas as pd
import json
import plotly.express as px

# Configuración de página
st.set_page_config(page_title="Análisis de Oferta Académica", page_icon="🎓", layout="wide")

st.title("🎓 Explorador de Oferta Académica por Área")
st.markdown("Busca un área específica y descubre cuántas y cuáles escuelas la ofrecen, además de conocer el nombre exacto con el que aparece en su oferta académica.")

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

# Menú lateral para filtros
st.sidebar.header("🔍 Filtros de Búsqueda")
nivel = st.sidebar.radio("Nivel Educativo:", ["Licenciaturas", "Posgrados"])

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

area_seleccionada = st.sidebar.selectbox("Selecciona un Área:", options=areas_disponibles)

if area_seleccionada:
    nombre_columna = f"{prefijo}{area_seleccionada}"
    
    # Filtrar solo las escuelas que ofrecen esta área
    df_filtrado = df[df[nombre_columna] == 1].copy()
    
    # --- MÉTRICAS ---
    st.header(f"Estadísticas para: {area_seleccionada}")
    st.metric(label="Total de Universidades que lo ofrecen", value=len(df_filtrado))
    
    if len(df_filtrado) == 0:
        st.info("Ninguna universidad en la base de datos actual ofrece esta área.")
        st.stop()
        
    st.divider()
    
    # --- GRÁFICO Y TABLA DE ALCALDÍAS ---
    st.subheader("📍 Distribución por Alcaldía")
    col1, col2 = st.columns([2, 1])
    
    # Contar por alcaldía
    # Rellenar vacíos por si acaso
    df_filtrado['alcaldia_busqueda'] = df_filtrado['alcaldia_busqueda'].fillna('No especificada')
    alcaldias_count = df_filtrado.groupby('alcaldia_busqueda').size().reset_index(name='Total de Universidades')
    alcaldias_count = alcaldias_count.sort_values('Total de Universidades', ascending=False)
    
    with col1:
        # Gráfico
        fig = px.bar(
            alcaldias_count, 
            x='alcaldia_busqueda', 
            y='Total de Universidades',
            text='Total de Universidades',
            color='alcaldia_busqueda',
            title=f"Universidades en {area_seleccionada} por Alcaldía",
            labels={'alcaldia_busqueda': 'Alcaldía'},
            template='plotly_white'
        )
        fig.update_traces(textposition='outside')
        fig.update_layout(showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
        
    with col2:
        # Tabla de resumen
        st.dataframe(
            alcaldias_count.set_index('alcaldia_busqueda'), 
            use_container_width=True
        )

    st.divider()
    
    # --- TABLA DETALLADA ---
    st.subheader("🎓 Detalles por Universidad")
    
    # Función para encontrar el nombre original
    def encontrar_nombre_original(fila):
        crudo = str(fila.get(col_cruda, ''))
        nombres_encontrados = []
        for elemento in crudo.split(','):
            limpio = elemento.strip()
            # Si el elemento limpio mapea al área seleccionada, lo guardamos
            if mapeo_actual.get(limpio) == area_seleccionada:
                nombres_encontrados.append(limpio)
        # Por si no encuentra match exacto (raro), ponemos una nota
        return ", ".join(nombres_encontrados) if nombres_encontrados else "Nombre no identificado"
    
    df_filtrado['Nombre Original del Programa'] = df_filtrado.apply(encontrar_nombre_original, axis=1)
    
    # Seleccionamos y renombramos columnas para mostrar
    columnas_mostrar = ['nombre', 'alcaldia_busqueda', 'Nombre Original del Programa', 'website', 'telefono']
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
            "Sitio Web": st.column_config.LinkColumn(
                "Sitio Web",
                help="Abre el enlace de la universidad en una pestaña nueva",
                display_text="Ver sitio web" # Para que se vea más limpio
            )
        }
    )
