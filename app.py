import streamlit as st
import folium
from streamlit_folium import st_folium
from geopy.geocoders import Nominatim
import requests

# 🔹 minii app haha
st.set_page_config(page_title="Mini Map Beta", layout="wide")
st.title("🗺️ Mini Map Beta")

geolocator = Nominatim(user_agent="mini_map_beta")

# 1.tsag agaar
def get_weather(lat, lon):
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
        res = requests.get(url).json()
        if "current_weather" in res:
            temp = res["current_weather"]["temperature"]
            wind = res["current_weather"]["windspeed"]
            return f"{temp}°C (Салхи: {wind} км/ц)"
    except Exception:
        pass
    return "Мэдээлэл олдсонгүй"

# 2. hool us undaa bolon benzeen
def get_nearby_pois(lat, lon, poi_type="fuel", radius=3000):
    overpass_url = "http://overpass-api.de/api/interpreter"
    query = f"""
    [out:json];
    node(around:{radius},{lat},{lon})["amenity"="{poi_type}"];
    out body 10;
    """
    try:
        res = requests.get(overpass_url, params={'data': query}).json()
        pois = []
        for element in res.get('elements', []):
            pois.append({
                'name': element.get('tags', {}).get('name', 'Нэргүй газар'),
                'lat': element['lat'],
                'lon': element['lon']
            })
        return pois
    except Exception:
        return []

# 3. alhmuut
INSTRUCTION_TRANSLATIONS = {
    "turn right": "Баруун тийш эргэ",
    "turn left": "Зүүн тийш эргэ",
    "slight right": "Ялимгүй баруун шахаж яв",
    "slight left": "Ялимгүй зүүн шахаж яв",
    "sharp right": "Баруун тийш огцом эргэ",
    "sharp left": "Зүүн тийш огцом эргэ",
    "straight": "Чигээрээ яв",
    "uturn": "Буцаж эргэ (U-turn)",
    "depart": "Хөдөлгөөнөө эхлүүл",
    "arrive": "Зорьсон газартаа хүрлээ"
}

def translate_instruction(step):
    maneuver = step.get("maneuver", {})
    m_type = maneuver.get("type", "")
    m_modifier = maneuver.get("modifier", "")
    name = step.get("name", "")
    
    action_key = f"{m_type} {m_modifier}".strip() if m_modifier else m_type
    action_text = INSTRUCTION_TRANSLATIONS.get(action_key, INSTRUCTION_TRANSLATIONS.get(m_type, "Чигээрээ яв"))
    return f"{action_text} ({name} замаар)" if name else action_text

@st.cache_data
def get_coordinates(location_name):
    try:
        loc = geolocator.geocode(location_name)
        if loc:
            return (loc.latitude, loc.longitude)
    except Exception:
        pass
    return None

def get_route_details(start_coords, end_coords, mode="driving"):
    url = f"http://router.project-osrm.org/route/v1/{mode}/{start_coords[1]},{start_coords[0]};{end_coords[1]},{end_coords[0]}?overview=full&geometries=geojson&steps=true"
    response = requests.get(url).json()
    
    if "routes" in response and len(response["routes"]) > 0:
        route = response["routes"][0]
        geometry = route["geometry"]["coordinates"]
        distance_km = route["distance"] / 1000
        duration_min = route["duration"] / 60
        
        steps = route["legs"][0]["steps"]
        instructions = [{"text": translate_instruction(s), "distance": s["distance"]} for s in steps]
        route_points = [[point[1], point[0]] for point in geometry]
        return route_points, distance_km, duration_min, instructions
    return None, 0, 0, []

# hajuugiin tses maygiin yum  (Sidebar)
st.sidebar.header("📍 Зам төлөвлөлт")
start_location_name = st.sidebar.text_input("Эхлэх цэг", "Ulaanbaatar")
end_location_name = st.sidebar.text_input("Очих цэг", "Darkhan")

travel_mode = st.sidebar.selectbox(
    "Тээврийн хэрэгсэл:",
    options=["driving", "walking", "cycling"],
    format_func=lambda x: "🚗 Машинаар" if x == "driving" else ("🚶 Явган" if x == "walking" else "🚴 Дугуйгаар")
)

st.sidebar.header("🔍 Хайх газрууд (POI)")
show_poi = st.sidebar.checkbox("Очих газрын ойролцоох байршлуудыг харуулах", value=True)
poi_type = st.sidebar.selectbox(
    "Газрын төрөл:", 
    options=["fuel", "restaurant", "hotel"], 
    format_func=lambda x: "⛽ ШТС / Бензин" if x == "fuel" else ("🍽️ Ресторан" if x == "restaurant" else "🏨 Зочид буудал")
)

map_tile = st.sidebar.selectbox("Зургийн хэв маяг:", options=["OpenStreetMap", "CartoDB positron", "CartoDB dark_matter"])

start_coords = get_coordinates(start_location_name)
end_coords = get_coordinates(end_location_name)

if start_coords and end_coords:
    route_points, distance_km, duration_min, instructions = get_route_details(start_coords, end_coords, travel_mode)
    
    start_weather = get_weather(start_coords[0], start_coords[1])
    end_weather = get_weather(end_coords[0], end_coords[1])
    
    w_col1, w_col2 = st.columns(2)
    w_col1.info(f"🌤️ **{start_location_name} Цаг агаар:** {start_weather}")
    w_col2.info(f"🌤️ **{end_location_name} Цаг агаар:** {end_weather}")

    col_map, col_info = st.columns([2.5, 1])
    
    with col_map:
        st.subheader("🗺️ Газрын зураг")
        center_lat = (start_coords[0] + end_coords[0]) / 2
        center_lon = (start_coords[1] + end_coords[1]) / 2
        
        m = folium.Map(location=[center_lat, center_lon], zoom_start=7, tiles=map_tile)
        
        folium.Marker(start_coords, popup=f"Эхлэх: {start_location_name}", icon=folium.Icon(color="green", icon="play")).add_to(m)
        folium.Marker(end_coords, popup=f"Очих: {end_location_name}", icon=folium.Icon(color="red", icon="stop")).add_to(m)
        
        if show_poi:
            pois = get_nearby_pois(end_coords[0], end_coords[1], poi_type=poi_type)
            icon_name = "fuel" if poi_type == "fuel" else ("utensils" if poi_type == "restaurant" else "bed")
            for p in pois:
                folium.Marker(
                    [p['lat'], p['lon']],
                    popup=p['name'],
                    icon=folium.Icon(color="orange", icon=icon_name, prefix="fa")
                ).add_to(m)

        if route_points:
            line_color = "red" if travel_mode == "walking" else ("green" if travel_mode == "cycling" else "blue")
            folium.PolyLine(route_points, color=line_color, weight=5, opacity=0.8).add_to(m)
            
        st_folium(m, width=800, height=600)

    with col_info:
        st.subheader("📊 Замын мэдээлэл")
        st.metric("Нийт замын урт", f"{distance_km:.1f} км")
        if duration_min > 60:
            st.metric("Хугацаа", f"{int(duration_min // 60)}ц {int(duration_min % 60)}м")
        else:
            st.metric("Хугацаа", f"{int(duration_min)} мин")
        
        st.subheader("🛣️ Алхамчилсан заавар")
        st.write("---")
        for i, step in enumerate(instructions, 1):
            d_str = f"{int(step['distance'])} м" if step['distance'] < 1000 else f"{step['distance']/1000:.1f} км"
            st.markdown(f"**{i}.** {step['text']} (`{d_str}`)")

else:
    st.error("Байршил олдсонгүй. Хаягийн нэрээ шалгана уу.")