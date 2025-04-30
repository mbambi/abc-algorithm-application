document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM loaded, initializing map...');
    
    // Initialize the map and set the view to a central coordinate in Morocco
    var map = L.map('map').setView([34.25, -6.57], 7);
    
    // Add OpenStreetMap tile layer
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '© OpenStreetMap'
    }).addTo(map);
    
    // Add markers for main locations from the global variable "locations"
    for (var key in locations) {
        if (locations.hasOwnProperty(key)) {
            var coords = locations[key];
            L.marker(coords).addTo(map).bindPopup(key);
        }
    }
    
    // Variables for route polyline, spinner, result container, and logs container
    var routePolyline = null;
    var spinner = document.getElementById('spinner');
    var resultElement = document.getElementById('result');
    var logsElement = document.getElementById('abcLogs');
    var optimizeBtn = document.getElementById('optimizeBtn');
    
    // Function to compute a curved line between two points for a nicer visual route
    function getCurvedLine(p1, p2) {
        var lat1 = p1[0], lon1 = p1[1];
        var lat2 = p2[0], lon2 = p2[1];
        var midLat = (lat1 + lat2) / 2;
        var midLon = (lon1 + lon2) / 2;
        var dx = lat2 - lat1;
        var dy = lon2 - lon1;
        var offsetMagnitude = 0.0015;
        var offsetLat = -dy * offsetMagnitude;
        var offsetLon = dx * offsetMagnitude;
        var offsetMid = [midLat + offsetLat, midLon + offsetLon];
        return [p1, offsetMid, p2];
    }
    
    // Event listener for the "Optimiser" button click
    optimizeBtn.addEventListener('click', function() {
        console.log('Optimiser button clicked');
        var start = document.getElementById('start').value;
        var end = document.getElementById('end').value;
    
        if (start === end) {
            alert('Les points de départ et d\'arrivée doivent être différents.');
            return;
        }
    
        // Disable the button and show the spinner during the API call
        optimizeBtn.disabled = true;
        spinner.classList.remove('hidden');
        resultElement.innerHTML = '';
        logsElement.innerHTML = '';
    
        // Call the Flask endpoint for optimization
        fetch('/optimize', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ start: start, end: end })
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(data => { throw data.error; });
            }
            return response.json();
        })
        .then(data => {
            console.log('Data received:', data);
            spinner.classList.add('hidden');
            optimizeBtn.disabled = false;
    
            var route = data.route;
            var distance = data.distance;
            var abcLogs = data.abc_logs;
            var allLocations = data.all_locations;
    
            // Build result HTML
            var resultHTML = '<h3>Itinéraire Optimisé</h3>';
            resultHTML += '<p><strong>Route:</strong> ' + route.join(' -> ') + '</p>';
            resultHTML += '<p><strong>Distance Totale:</strong> ' + distance.toFixed(2) + ' km</p>';
            resultElement.innerHTML = resultHTML;
    
            // Build logs HTML
            var logsHTML = '<h4>Logs de l\'Algorithme ABC</h4><div class="logs-box">';
            abcLogs.forEach(function(logLine) {
                logsHTML += '<p>' + logLine + '</p>';
            });
            logsHTML += '</div>';
            logsElement.innerHTML = logsHTML;
    
            // Construct a curved polyline for the route using coordinates from either "locations" or "allLocations"
            var curvedLatlngs = [];
            for (var i = 0; i < route.length - 1; i++) {
                var nodeA = route[i];
                var nodeB = route[i + 1];
                var p1 = locations[nodeA] || allLocations[nodeA];
                var p2 = locations[nodeB] || allLocations[nodeB];
                if (!p1 || !p2) continue;
                var segment = getCurvedLine(p1, p2);
                if (i > 0) segment.shift(); // Avoid duplicate points
                curvedLatlngs = curvedLatlngs.concat(segment);
            }
    
            // Remove any existing polyline and add the new one
            if (routePolyline) {
                map.removeLayer(routePolyline);
            }
            if (curvedLatlngs.length > 0) {
                routePolyline = L.polyline(curvedLatlngs, { color: 'red', weight: 4, dashArray: '5, 10' }).addTo(map);
                map.fitBounds(routePolyline.getBounds());
            }
        })
        .catch(err => {
            console.error('Error:', err);
            spinner.classList.add('hidden');
            optimizeBtn.disabled = false;
            resultElement.style.color = "red";
            resultElement.innerHTML = 'Erreur: ' + err;
        });
    });
});
