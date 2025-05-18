from flask import Flask, request, render_template_string, redirect, url_for, send_file
from geopy.geocoders import Nominatim
import os
import csv
import io

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
geolocator = Nominatim(user_agent="web_geocoder")
GOOGLE_MAPS_API_KEY = "AIzaSyCAVJVw8jNSjTjUS7ZMhOaf_2dbbiu7nh0"
last_result = {}

TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>AXIOMA | Location Finder</title>
    <script src="https://maps.googleapis.com/maps/api/js?key={{ api_key }}"></script>
    <style>
        body.dark {
            --bg-color: #1c1c1c;
            --text-color: #f5f5f5;
            --header-bg: #222;
            --footer-bg: #222;
            --card-bg: #2a2a2a;
            --button-bg: #4444aa;
            --button-hover: #333399;
        }
        body {
            font-family: Arial, sans-serif;
            background-color: var(--bg-color, #f5f5f5);
            color: var(--text-color, #000);
            margin: 0;
            padding: 0;
        }
        header {
            background-color: var(--header-bg, #003366);
            padding: 1rem;
            text-align: center;
            position: relative;
        }
        header img.logo {
            max-width: 135px;
        }
        .theme-toggle {
            position: absolute;
            top: 10px;
            right: 15px;
            background: none;
            border: none;
            cursor: pointer;
        }
        .theme-toggle img {
            height: 100px;
        }
        main {
            max-width: 800px;
            margin: 2rem auto;
            padding: 2rem;
            background: var(--card-bg, #ffffff);
            border-radius: 12px;
        }
        input, button {
            padding: 0.6rem;
            margin: 0.3rem 0;
            border-radius: 6px;
        }
        #map {
            width: 100%;
            height: 450px;
            margin-top: 1rem;
            border-radius: 10px;
        }
        .share-buttons button, .share-buttons a {
            margin-right: 10px;
        }
        footer {
            background-color: var(--footer-bg, #003366);
            color: white;
            text-align: center;
            padding: 1rem;
        }
    </style>
</head>
<body class="dark">
    <header>
        <a href="/"><img src="/static/axioma_logo.png" class="logo" alt="AXIOMA Logo"></a>
        <button class="theme-toggle" onclick="toggleTheme()">
            <img src="/static/darkmode-button.png" alt="Toggle Theme">
        </button>
    </header>
    <main>
        <h2>🔎 Find Coordinates from a Place</h2>
        <form method="POST">
            <input type="text" name="place" placeholder="Enter place name" required>
            <button type="submit" name="action" value="forward">Find</button>
        </form>

        <h2>📍 Find Address from Coordinates</h2>
        <form method="POST">
            <input type="text" name="latitude" placeholder="Latitude" required>
            <input type="text" name="longitude" placeholder="Longitude" required>
            <button type="submit" name="action" value="reverse">Find</button>
        </form>

        <h2>📂 Batch Upload (CSV)</h2>
        <form method="POST" action="/upload" enctype="multipart/form-data">
            <input type="file" name="file" required>
            <button type="submit">Upload & Process</button>
        </form>

        {% if result %}
            <p class="success">{{ result }}</p>
            <form action="/download" method="get">
                <button type="submit">Download Result as CSV</button>
            </form>
        {% endif %}

        {% if lat and lon %}
            <div id="map"></div>
            <div class="share-buttons">
                <h3>🔗 Share this location</h3>
                <button onclick="copyLink()">Copy Link</button>
                <a href="mailto:?subject=Shared Location&body=Check out this location: https://maps.google.com/?q={{ lat }},{{ lon }}" target="_blank">Email</a>
                <a href="https://wa.me/?text=Check out this location: https://maps.google.com/?q={{ lat }},{{ lon }}" target="_blank">WhatsApp</a>
                <div id="copySuccess" style="color: green; display: none;">📍 Link copied!</div>
            </div>
            <script>
                function initMap() {
                    const target = { lat: {{ lat }}, lng: {{ lon }} };
                    const map = new google.maps.Map(document.getElementById("map"), {
                        center: { lat: 0, lng: 0 },
                        zoom: 2,
                        mapTypeId: "roadmap"
                    });
                    const marker = new google.maps.Marker({
                        position: target,
                        map: map,
                        animation: google.maps.Animation.DROP
                    });
                    const infoWindow = new google.maps.InfoWindow({
                        content: `<div style="color:#000">{{ result | e }}</div>`
                    });
                    marker.addListener("click", () => {
                        infoWindow.open(map, marker);
                    });

                    // Smooth zoom-in and pan after delay
                    setTimeout(() => {
                        map.panTo(target);
                        let zoomLevel = 2;
                        const interval = setInterval(() => {
                            if (zoomLevel < 16) {
                                zoomLevel++;
                                map.setZoom(zoomLevel);
                            } else {
                                clearInterval(interval);
                            }
                        }, 150);
                    }, 1000);
                }

                function copyLink() {
                    const temp = document.createElement("input");
                    temp.value = `https://maps.google.com/?q={{ lat }},{{ lon }}`;
                    document.body.appendChild(temp);
                    temp.select();
                    document.execCommand("copy");
                    document.body.removeChild(temp);
                    document.getElementById("copySuccess").style.display = "block";
                    setTimeout(() => {
                        document.getElementById("copySuccess").style.display = "none";
                    }, 2000);
                }

                window.onload = function() {
                    toggleThemeInit();
                    initMap();
                };
            </script>
        {% else %}
            <script>window.onload = toggleThemeInit;</script>
        {% endif %}
    </main>
    <footer>
        <p>📧 info@axioma-corp.com | 📞 +297 7440399 | 🌐 www.axioma-corp.com</p>
        <p>#WeAreNotTheNextOfThemButTheFirstOfUs</p>
    </footer>
    <script>
        function toggleTheme() {
            document.body.classList.toggle("dark");
            localStorage.setItem("theme", document.body.classList.contains("dark") ? "dark" : "light");
        }
        function toggleThemeInit() {
            const theme = localStorage.getItem("theme");
            if (theme === "light") document.body.classList.remove("dark");
        }
    </script>
</body>
</html>
'''

@app.route('/', methods=['GET', 'POST'])
def index():
    global last_result
    if request.method == 'POST':
        action = request.form['action']
        lat, lon, result = None, None, None
        try:
            if action == 'forward':
                place = request.form['place']
                location = geolocator.geocode(place)
                if location:
                    lat, lon = location.latitude, location.longitude
                    address = location.address
                    result = f"Latitude: {lat}, Longitude: {lon}, Address: {address}"
                    last_result = {"place": place, "latitude": lat, "longitude": lon, "address": address}
                else:
                    result = "Place not found."
                    last_result = {}
            elif action == 'reverse':
                lat = float(request.form['latitude'])
                lon = float(request.form['longitude'])
                location = geolocator.reverse((lat, lon))
                if location:
                    address = location.address
                    result = f"Address: {address}"
                    last_result = {"latitude": lat, "longitude": lon, "address": address}
                else:
                    result = "No address found for these coordinates."
                    last_result = {}
            return render_template_string(TEMPLATE, result=result, lat=lat, lon=lon, api_key=GOOGLE_MAPS_API_KEY)
        except Exception as e:
            return render_template_string(TEMPLATE, error=f"Error: {e}", api_key=GOOGLE_MAPS_API_KEY)
    return render_template_string(TEMPLATE, api_key=GOOGLE_MAPS_API_KEY)

@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return redirect(url_for('index'))
    file = request.files['file']
    if file.filename == '':
        return redirect(url_for('index'))
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(filepath)
    output = io.StringIO()
    writer = csv.writer(output)

    with open(filepath, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        results = []
        for row in reader:
            result_row = row.copy()
            if 'place' in row and row['place']:
                location = geolocator.geocode(row['place'])
                if location:
                    result_row['latitude'] = location.latitude
                    result_row['longitude'] = location.longitude
                    result_row['address'] = location.address
                else:
                    result_row['latitude'] = ''
                    result_row['longitude'] = ''
                    result_row['address'] = 'Not found'
            elif 'latitude' in row and 'longitude' in row:
                try:
                    location = geolocator.reverse((float(row['latitude']), float(row['longitude'])))
                    result_row['address'] = location.address if location else 'Not found'
                except:
                    result_row['address'] = 'Error'
            results.append(result_row)

        fieldnames = list(results[0].keys()) if results else []
        writer.writerow(fieldnames)
        for r in results:
            writer.writerow([r.get(h, '') for h in fieldnames])
    output.seek(0)
    return send_file(io.BytesIO(output.read().encode()), mimetype='text/csv', as_attachment=True, download_name='batch_results.csv')

@app.route('/download')
def download():
    global last_result
    if not last_result:
        return redirect(url_for('index'))
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(last_result.keys())
    writer.writerow(last_result.values())
    output.seek(0)
    return send_file(io.BytesIO(output.read().encode()), mimetype='text/csv', as_attachment=True, download_name='axioma_location_result.csv')

if __name__ == '__main__':
    os.makedirs('uploads', exist_ok=True)
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
