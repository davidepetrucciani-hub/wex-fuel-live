import streamlit as st
import pandas as pd
import requests
import folium
from streamlit_folium import st_folium
from datetime import datetime
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configurazione Pagina
st.set_page_config(page_title="WEX Fuel Finder", layout="wide")

# --- LOGICA DATI ---
@st.cache_data(ttl=3600) # Aggiorna i prezzi ogni ora
def get_live_prices():
    prezzi = {}
    url = "https://carburanti.mise.gov.it/ospzApi/search/servicearea"
    try:
        r = requests.post(url, json={"searchParams": {"serviceArea": {"latitude": 42.0, "longitude": 12.5}, "maxResults": 100000}}, timeout=30, verify=False)
        if r.status_code == 200:
            for item in r.json().get('results', []):
                pid = str(item.get('id')).strip()
                prezzi[pid] = {f"{f['name']} ({'Self' if f.get('isSelf') else 'Servito'})": float(f.get('price', 0)) for f in item.get('fuels', [])}
    except: pass
    return prezzi

# --- INTERFACCIA ---
st.title("⛽ WEX Live Station Finder")
st.sidebar.header("Filtri Ricerca")

try:
    db = pd.read_excel("Incrocio_DKV_MISE_Coordinate_Precise.xlsx")
    db['ID_Impianto_MISE'] = db['ID_Impianto_MISE'].apply(lambda x: str(int(float(x))) if pd.notna(x) else "").str.strip()
    
    prezzi_live = get_live_prices()
    
    fuel_type = st.sidebar.selectbox("Seleziona Carburante", ["Gasolio (Self)", "Benzina (Self)", "Gasolio (Servito)"])
    brand_filter = st.sidebar.text_input("Cerca Brand (es. ENI)").upper()
    
    # Filtraggio
    map_data = []
    for _, row in db.iterrows():
        id_m = row['ID_Impianto_MISE']
        if id_m in prezzi_live and fuel_type in prezzi_live[id_m]:
            price = prezzi_live[id_m][fuel_type]
            brand = str(row['Bandiera']).upper()
            
            if brand_filter in brand:
                map_data.append({
                    "lat": row['Latitudine_MISE'],
                    "lng": row['Longitudine_MISE'],
                    "brand": brand,
                    "price": price,
                    "addr": row['Indirizzo_MISE'],
                    "reg": row.get('Regione', 'N.D.')
                })

    # --- MAPPA ---
    m = folium.Map(location=[42, 12.5], zoom_start=6, control_scale=True)
    
    for p in map_data:
        # Link per Google Maps
        gmaps_url = f"https://www.google.com/maps/dir/?api=1&destination={p['lat']},{p['lng']}"
        
        popup_html = f"""
            <div style='font-family:sans-serif; width:200px'>
                <h4>{p['brand']}</h4>
                <b style='font-size:18px; color:green'>{p['price']:.3f} €</b><br>
                <small>{p['addr']}</small><br><br>
                <a href='{gmaps_url}' target='_blank' style='display:block; background:#4285F4; color:white; text-align:center; padding:8px; border-radius:5px; text-decoration:none'>NAVIGA (Google Maps)</a>
            </div>
        """
        
        folium.CircleMarker(
            location=[p['lat'], p['lng']],
            radius=8,
            popup=folium.Popup(popup_html, max_width=250),
            color='green' if p['price'] < 1.8 else 'orange',
            fill=True
        ).add_to(m)

    st_folium(m, width="100%", height=700)

except Exception as e:
    st.error(f"Errore: Caricare il file Excel nella cartella. ({e})")