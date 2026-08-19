"""
Dashboard Principal - Economía Venezuela
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

# Page config
st.set_page_config(
    page_title="Economía Venezuela",
    page_icon="🇻🇪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Title
st.title("🇻🇪 Economía Venezuela")
st.markdown("---")

# Sidebar
with st.sidebar:
    st.header("🔍 Filtros")
    
    # Date range
    start_date = st.date_input(
        "Fecha inicio",
        value=datetime.now() - timedelta(days=30)
    )
    end_date = st.date_input(
        "Fecha fin",
        value=datetime.now()
    )
    
    # Metrics selection
    metrics = st.multiselect(
        "Métricas a mostrar",
        ["Dólar Oficial", "Dólar Paralelo", "Inflación", "PIB", "Reservas"],
        default=["Dólar Oficial", "Dólar Paralelo"]
    )

# Main dashboard
col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        label="💵 Dólar Oficial",
        value="Bs 36.50",
        delta="+0.5%"
    )

with col2:
    st.metric(
        label="💵 Dólar Paralelo",
        value="Bs 78.00",
        delta="-2.3%"
    )

with col3:
    st.metric(
        label="📈 Inflación Mensual",
        value="5.2%",
        delta="+0.8%"
    )

# Charts placeholder
st.subheader("📊 Gráficos")
st.info("Los gráficos se mostrarán aquí cuando se conecten los datos")

# Recent data
st.subheader("📋 Datos Recientes")
st.info("Los datos recientes se mostrarán aquí")

# System status
st.subheader("⚙️ Estado del Sistema")
status_col1, status_col2 = st.columns(2)

with status_col1:
    st.success("✅ Base de datos: Conectada")
    st.success("✅ Redis: Conectado")

with status_col2:
    st.warning("⚠️ API BCV: Pendiente")
    st.warning("⚠️ API Binance: Pendiente")

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #888;'>
        <p>Economía Venezuela v0.1.0 | Actualizado: {}</p>
    </div>
    """.format(datetime.now().strftime("%Y-%m-%d %H:%M")),
    unsafe_allow_html=True
)
