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
        :root {
            --bg-color: #f5f7fa;
            --text-color: #000000;
            --header-bg: #003366;
            --footer-bg: #003366;
            --card-bg: #ffffff;
            --button-bg: #0077b6;
            --button-hover: #005b9e;
        }

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
            font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-color);
            margin: 0;
            padding: 0;
            transition: background-color 0.3s ease, color 0.3s ease;
        }

        header {
            background-color: var(--header-bg);
            padding: 1rem;
            text-align: center;
            position: relative;
        }

        header img.logo {
            max-width: 135px;
            height: auto;
            transition: opacity 0.3s ease;
        }

        header a:hover img.logo {
            opacity: 0.85;
        }

        .theme-toggle {
            position: absolute;
            top: 10px;
            right: 15px;
            cursor: pointer;
            border: none;
            background: none;
            padding: 0;
        }

        .theme-toggle img {
            height: 100px;
            width: auto;
        }

        main {
            max-width: 800px;
            margin: 2rem auto;
            padding: 2.5rem;
            background: var(--card-bg);
            border-radius: 12px;
            box-shadow: 0 6px 20px rgba(0,0,0,0.08);
        }

        h2 {
            color: var(--text-color);
            margin-top: 1.5rem;
        }

        form {
            margin-bottom: 2rem;
        }

        input[type="text"],
        input[type="file"] {
            width: 60%;
            padding: 0.6rem;
            border: 1px solid #ccc;
            border-radius: 6px;
            font-size: 1rem;
        }

        button {
            background-color: var(--button-bg);
            color: white;
            padding: 0.6rem 1.2rem;
            border: none;
            border-radius: 6px;
            font-size: 1rem;
            cursor: pointer;
            margin-right: 0.5rem;
        }

        button:hover {
            background-color: var(--button-hover);
        }

        .share-buttons {
            margin-top: 1rem;
        }

        .share-buttons a,
        .share-buttons button {
            margin-right: 10px;
            margin-bottom: 10px;
            text-decoration: none;
        }

        .copy-success {
            font-size: 0.9rem;
            color: green;
            margin-top: 0.5rem;
        }

        .error {
            color: red;
            font-weight: 500;
        }

        .success {
            color: #2e7d32;
            font-weight: 500;
        }

        #map {
            width: 100%;
            height: 450px;
            margin-top: 1.5rem;
            border-radius: 8px;
        }

        footer {
            background-color: var(--footer-bg);
            color: white;
            text-align: center;
            padding: 1rem;
            font-size: 0.9rem;
            margin-top: 2rem;
        }

        @media screen and (max-width: 600px) {
            input[type="text"],
            input[type="file"] {
                width: 100%;
                margin-bottom: 1rem;
            }

            button {
                width: 100%;
                margin-bottom: 0.5rem;
            }

            .theme-toggle img {
                height: 80px;
            }
        }
    </style>
</head>
<body class="dark">
    <header>
        <a href="/">
            <img src="/static/axioma_logo.png" alt="AXIOMA Logo" class="logo">
        </a>
        <button class="theme-toggle" onclick="toggleTheme()">
            <img src="/static/darkmode-button.png" alt="Toggle theme">
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
        {% elif error %}
            <p class="error">{{ error }}</p>
        {% endif %}

        {% if lat and lon %}
            <div id="map"></div>

            <div class="share-buttons">
                <h3>🔗 Share this location</h3>
                <button onclick="copyLink()">Copy Link</button>
                <a href="mailto:?subject=Shared Location&body=Check out this location: https://maps.google.com/?q={{ lat }},{{ lon }}" target="_blank">
                    Share via Email
                </a>
                <a href="https://wa.me/?text=Check out this location: https://maps.google.com/?q={{ lat }},{{ lon }}" target="_blank">
                    Share via WhatsApp
                </a>
                <div id="copySuccess" class="copy-success" style="display:none;">📍 Link copied!</div>
            </div>

            <script>
                function initMap() {
                    const location = { lat: {{ lat }}, lng: {{ lon }} };
                    const map = new google.maps.Map(document.getElementById('map'), {
                        center: location,
                        zoom: 10,
                        mapTypeId: 'roadmap'
                    });
                    const marker = new google.maps.Marker({
                        position: location,
                        map: map,
                        animation: google.maps.Animation.DROP
                    });
                    const contentString = `
                        <div style="color: #000000; font-size: 14px; max-width: 240px;">
                            {{ result | e }}
                        </div>
                    `;
                    const infowindow = new google.maps.InfoWindow({
                        content: contentString
                    });
                    marker.addListener("click", () => {
                        infowindow.open(map, marker);
                    });
                    setTimeout(() => map.setZoom(16), 600);
                }

                function copyLink() {
                    const tempInput = document.createElement('input');
                    tempInput.value = `https://maps.google.com/?q={{ lat }},{{ lon }}`;
                    document.body.appendChild(tempInput);
                    tempInput.select();
                    document.execCommand('copy');
                    document.body.removeChild(tempInput);
                    document.getElementById('copySuccess').style.display = 'block';
                    setTimeout(() => {
                        document.getElementById('copySuccess').style.display = 'none';
                    }, 2000);
                }

                window.onload = function() {
                    toggleThemeInit();
                    initMap();
                };
            </script>
        {% else %}
            <script>
                window.onload = function() {
                    toggleThemeInit();
                };
            </script>
        {% endif %}
    </main>
    <footer>
        <p>📧 info@axioma-corp.com | 📞 +297 7440399 | 🌐 www.axioma-corp.com</p>
        <p>#WeAreNotTheNextOfThemButTheFirstOfUs</p>
    </footer>
    <script>
        function toggleTheme() {
            document.body.classList.toggle('dark');
            localStorage.setItem('theme', document.body.classList.contains('dark') ? 'dark' : 'light');
        }

        function toggleThemeInit() {
            const savedTheme = localStorage.getItem('theme');
            if (savedTheme === 'light') {
                document.body.classList.remove('dark');
            } else {
                document.body.classList.add('dark');
            }
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
    app.run(debug=True)
