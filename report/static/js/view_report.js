google.charts.load('current', {
    'packages': ['map'],
    // Note: you will need to get a mapsApiKey for your project.
    // See: https://developers.google.com/chart/interactive/docs/basic_load_libs#load-settings
    'mapsApiKey': mapsApiKey,
});
google.charts.setOnLoadCallback(drawMap);

var map;
var options;
var sliderStartDate;
var sliderEndDate;

function updateMapMarkers(startDate, endDate) {

    var options = {
        showTooltip: true,
        showInfoWindow: true,
        useMapTypeControl: true,
        icons: {
            red: {
                normal: 'https://icons.iconarchive.com/icons/paomedia/small-n-flat/48/map-marker-icon.png',
                selected: 'https://icons.iconarchive.com/icons/paomedia/small-n-flat/48/map-marker-icon.png'
            },
            blue: {
                normal: 'https://icons.iconarchive.com/icons/icons-land/vista-map-markers/32/Map-Marker-Marker-Outside-Azure-icon.png',
                selected: 'https://icons.iconarchive.com/icons/icons-land/vista-map-markers/32/Map-Marker-Marker-Outside-Azure-icon.png'
            }
        }
    };

    var map_location_data = []
    for (let array_with_date of location_data) {
        if (array_with_date[0] == 'Lat' || array_with_date[1][0] == 'U') {
            map_location_data.push([array_with_date[0], array_with_date[1], array_with_date[2], array_with_date[3]])
        }
        else{
            var dateMoment = moment(array_with_date[4], "YYYY-MM-DD");
            if (dateMoment >= startDate && dateMoment <= endDate) {
                map_location_data.push([array_with_date[0], array_with_date[1], array_with_date[2], array_with_date[3]])
            }
        }
    }
    var map = new google.visualization.Map(document.getElementById('map_markers_div'));
    if(map_location_data.length == 1){
        var dataTable = google.visualization.arrayToDataTable([['0','0',"Empty"]]);
        map.draw(dataTable,options)
    }else if(map_location_data.length == 2){
        var dataTable = google.visualization.arrayToDataTable(map_location_data,false);
        options.zoomLevel = 15
        map.draw(dataTable, options);
    }else{
        var dataTable = google.visualization.arrayToDataTable(map_location_data,false);
        map.draw(dataTable, options);
    }
}

function drawMap() {

    $("#date-range-slider").dateRangeSlider({
        formatter: function(val) {
            return val.toLocaleString('en-uk', {
                month: 'long',
                year: 'numeric',
                day: 'numeric'
            })
        }
    });

    $("#date-range-slider").dateRangeSlider("bounds", sliderStartDate.toDate(), sliderEndDate.toDate());
    $("#date-range-slider").dateRangeSlider("values", sliderStartDate.toDate(), sliderEndDate.toDate());
    $("#date-range-slider").bind("valuesChanged", function(e, data) {
        updateMapMarkers(data.values.min, data.values.max)
    });
    updateMapMarkers(sliderStartDate.toDate(), sliderEndDate.toDate())

}