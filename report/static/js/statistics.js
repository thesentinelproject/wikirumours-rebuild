  var map = null;
  var timeChart = null;
  var statusesPieChart = null;
  var prioritiesPieChart = null;
  var domainsBarChart = null;
  function addFeatureSource(filteredFeatures,isDarkMode) {
    // Add a geojson point source.
    // Heatmap layers also work with a vector tile source.
    var circleColor = "black"
    if (isDarkMode){
        circleColor = "white"
    }
    map.addSource('rumours', {
      'type': 'geojson',
      'data': filteredFeatures
    });
    map.addLayer(
      {
        'id': 'rumours-heat',
        'type': 'heatmap',
        'source': 'rumours',
        'maxzoom': 9,
        'paint': {
          // Increase the heatmap weight based on frequency and property magnitude
          'heatmap-weight': [
            'interpolate',
            ['linear'],
            ['get', 'mag'],
            0,
            0,
            6,
            1
          ],
          // Increase the heatmap color weight weight by zoom level
          // heatmap-intensity is a multiplier on top of heatmap-weight
          'heatmap-intensity': [
            'interpolate',
            ['linear'],
            ['zoom'],
            0,
            1,
            9,
            3
          ],
          // Color ramp for heatmap.  Domain is 0 (low) to 1 (high).
          // Begin color ramp at 0-stop with a 0-transparancy color
          // to create a blur-like effect.
          'heatmap-color': [
            'interpolate',
            ['linear'],
            ['heatmap-density'],
            0,
            'rgba(33,102,172,0)',
            0.2,
            'rgb(103,169,207)',
            0.4,
            'rgb(209,229,240)',
            0.6,
            'rgb(253,219,199)',
            0.8,
            'rgb(239,138,98)',
            1,
            'rgb(178,24,43)'
          ],
          // Adjust the heatmap radius by zoom level
          'heatmap-radius': [
            'interpolate',
            ['linear'],
            ['zoom'],
            0,
            2,
            9,
            20
          ],
          // Transition from heatmap to circle layer by zoom level
          'heatmap-opacity': [
            'interpolate',
            ['linear'],
            ['zoom'],
            7,
            1,
            9,
            0
          ]
        }
      },
      'waterway-label'
    );
    map.addLayer(
      {
        'id': 'rumours-point',
        'type': 'circle',
        'source': 'rumours',
        'minzoom': 2,
        'paint': {
          // Size circle radius by earthquake magnitude and zoom level
          'circle-radius': [
            'interpolate',
            ['linear'],
            ['zoom'],
            7,
            ['interpolate', ['linear'], ['get', 'mag'], 1, 1, 6, 4],
            16,
            ['interpolate', ['linear'], ['get', 'mag'], 1, 5, 6, 50]
          ],
          // Color circle by earthquake magnitude
          'circle-color': [
            'interpolate',
            ['linear'],
            ['get', 'mag'],
            1,
            'rgba(33,102,172,0)',
            2,
            'rgb(103,169,207)',
            3,
            'rgb(209,229,240)',
            4,
            'rgb(253,219,199)',
            5,
            'rgb(239,138,98)',
            6,
            'rgb(178,24,43)'
          ],
          'circle-stroke-color': circleColor,
          'circle-stroke-width': 1,
          // Transition from heatmap to circle layer by zoom level
          'circle-opacity': [
            'interpolate',
            ['linear'],
            ['zoom'],
            7,
            0,
            8,
            1
          ]
        }
      },
      'waterway-label'
    );

  }
  function removeFeatureSource() {
    if (map.getLayer("rumours-point")) {
      map.removeLayer("rumours-point");
    }
    if (map.getLayer("rumours-heat")) {
      map.removeLayer("rumours-heat");
    }
    if (map.getSource("rumours")) {
      map.removeSource("rumours");
    }
  }
  function fetchStatisticsData(startDate, endDate) {
    const formattedStartDate = startDate.toISOString().slice(0, 10)
    const formattedEndDate = endDate.toISOString().slice(0, 10)
    $.ajax({
      url: "data?" +
        "&start_date=" + formattedStartDate +
        "&end_date=" + formattedEndDate +
        "&status=" + $("#id_status").val() +
        "&priority=" + $("#id_priority").val() +
        "&country=" + $("#id_country").val(),
      contentType: "application/json",
      dataType: 'json',
      success: function (result) {
        const featureCollection = result.feature_collection
        const reportsChartData = result.reports_chart_data
        const sightingsChartData = result.sightings_chart_data
        const isDarkMode = result.dark_mode
        removeFeatureSource()
        addFeatureSource(featureCollection,isDarkMode)
        if (timeChart) {
          timeChart.data.datasets.pop();
          timeChart.data.datasets = [{
            label: "Sighting",
            backgroundColor: 'rgba(5, 170, 255, 1)',
            data: sightingsChartData
          }, {
            label: "Report",
            backgroundColor: 'rgba(45, 62, 80, 1)',
            data: reportsChartData
          }];
          timeChart.update()
        }

        // update counts for sightings and reports
        $('#reports_count').text(result.reports_count);
        $('#sightings_count').text(result.sightings_count);

        // update pie charts for statuses and priorities
        if (statusesPieChart) {
            statusesPieChart.data = {
              labels: result.statuses_data.map(function (el) { return el.status__name; }),
              datasets: [{
                label: 'Dataset',
                data: result.statuses_data.map(function (el) { return el.count; }),
                backgroundColor: result.statuses_data.map(function (el) { return el.status__colour; }),
                hoverOffset: 4
              }]
            }
            statusesPieChart.update()
        }

        if (prioritiesPieChart) {
            prioritiesPieChart.data = {
              labels: result.priorities_data.map(function (el) { return el.priority__name; }),
              datasets: [{
                label: 'Dataset',
                data: result.priorities_data.map(function (el) { return el.count; }),
                backgroundColor: result.priorities_data.map(function (el) { return el.priority__colour; }),
                hoverOffset: 4
              }]
            }
            prioritiesPieChart.update()
        }


        if (domainsBarChart) {
            domainsBarChart.data = {
              labels: result.domains_reports_data.map(function (el) { return el.domain__name; }),
              datasets: [{
                label: 'Reports',
                data: result.domains_reports_data.map(function (el) { return el.count; }),
                backgroundColor: result.domains_reports_data.map(function (el) { return el.priority__colour; }),
                borderColor: "rgba(45, 62, 80, 1)",
                backgroundColor: "rgba(45, 62, 80, 1)",
              },
              {
                label: 'Sightings',
                data: result.domains_sightings_data.map(function (el) { return el.count; }),
                backgroundColor: result.domains_sightings_data.map(function (el) { return el.priority__colour; }),
                borderColor: "rgba(5, 170, 255, 1)",
                backgroundColor: "rgba(5, 170, 255, 1)",
              }
              ]
            }
            domainsBarChart.update()
        }

        $('#top_tags').text(result.tags_data);

        var masterTags = result.master_tags;
        var matrix = result.tags_array;

        createChordDiagram("#chord-diagram")
        createChordDiagram("#chord-diagram-mobile")

        function createChordDiagram(divName) {
        // create the svg area
        d3.select(divName).selectAll("*").remove()
        var Names = masterTags,
            colors = ["#301E1E"]
        	opacityDefault = 0.8;
        var margin = {left:90, top:90, right:90, bottom:90}
        if (divName === "#chord-diagram" ){
            width = Math.min(window.innerWidth, 560) - margin.left - margin.right,
            height = Math.min(window.innerWidth, 560) - margin.top - margin.bottom,
            innerRadius = Math.min(width, height) * .39,
            outerRadius = innerRadius * 1.1;
        }else{
            width = Math.min(window.innerWidth, 360) - margin.left - margin.right,
            height = Math.min(window.innerWidth, 360) - margin.top - margin.bottom,
            innerRadius = Math.min(width, height) * .39,
            outerRadius = innerRadius * 1.1;
        }

        ////////////////////////////////////////////////////////////
        /////////// Create scale and layout functions //////////////
        ////////////////////////////////////////////////////////////

        var colors = d3.scale.ordinal()
            .domain(d3.range(Names.length))
            .range(colors);

        var chord = d3.layout.chord()
            .padding(.15)
            .sortChords(d3.descending)
            .matrix(matrix);

        var arc = d3.svg.arc()
            .innerRadius(innerRadius*1.01)
            .outerRadius(outerRadius);

        var path = d3.svg.chord()
            .radius(innerRadius);

        ////////////////////////////////////////////////////////////
        ////////////////////// Create SVG //////////////////////////
        ////////////////////////////////////////////////////////////

        var svg = d3.select(divName).append("svg")
            .attr("width", width + margin.left + margin.right)
            .attr("height", height + margin.top + margin.bottom)
            .append("g")
            .attr("transform", "translate(" + (width/2 + margin.left) + "," + (height/2 + margin.top) + ")");

        ////////////////////////////////////////////////////////////
        ////////////////// Draw outer Arcs /////////////////////////
        ////////////////////////////////////////////////////////////

        var outerArcs = svg.selectAll("g.group")
            .data(chord.groups)
            .enter().append("g")
            .attr("class", "group")
            .on("mouseover", fade(.1))
            .on("mouseout", fade(opacityDefault));

        outerArcs.append("path")
            .style("fill", function(d) { return colors(d.index); })
            .attr("d", arc);

        ////////////////////////////////////////////////////////////
        ////////////////////// Append Names ////////////////////////
        ////////////////////////////////////////////////////////////

        //Append the label names on the outside
        outerArcs.append("text")
          .each(function(d) { d.angle = (d.startAngle + d.endAngle) / 2; })
          .attr("dy", ".35em")
          .attr("class", "titles")
          .attr("text-anchor", function(d) { return d.angle > Math.PI ? "end" : null; })
          .attr("transform", function(d) {
                return "rotate(" + (d.angle * 180 / Math.PI - 90) + ")"
                + "translate(" + (outerRadius + 10) + ")"
                + (d.angle > Math.PI ? "rotate(180)" : "");
          })
          .text(function(d,i) { return Names[i]; });

        ////////////////////////////////////////////////////////////
        ////////////////// Draw inner chords ///////////////////////
        ////////////////////////////////////////////////////////////

        svg.selectAll("path.chord")
            .data(chord.chords)
            .enter().append("path")
            .attr("class", "chord")
            .style("fill", function(d) { return colors(d.source.index); })
            .style("opacity", opacityDefault)
            .attr("d", path);
         //Returns an event handler for fading a given chord group.
        function fade(opacity) {
          return function(d,i) {
            svg.selectAll("path.chord")
                .filter(function(d) { return d.source.index != i && d.target.index != i; })
                .transition()
                .style("opacity", opacity);
          };
        }//fade
        }
      }
    })
  }


  $(document).ready(function () {
    var ctx = document.getElementById('line-chart');
    var mainHtmlDiv = document.getElementById('main_html_div');
    var isDarkMode = mainHtmlDiv.classList.contains("dark")
    var mapStyle = "mapbox://styles/mapbox/light-v9"
    if (isDarkMode){
        mapStyle =  "mapbox://styles/mapbox/dark-v10"
    }
    timeChart = new Chart(ctx, {
      type: 'line',
      data: {
        datasets: [{
          backgroundColor: 'rgba(0, 155, 237, 0.37)',
          borderColor: 'rgba(0, 155, 237, 0.9)',
          borderWidth: 1,
          data: [],
          pointHitRadius: 2,
          pointRadius: 1,
        }, {
          backgroundColor: 'rgba(0, 100, 237, 0.37)',
          borderColor: 'rgba(0, 155, 237, 0.9)',
          borderWidth: 1,
          data: [],
          pointHitRadius: 2,
          pointRadius: 1,
        }]
      },
      options: {
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: false,
          }
        },
        scales: {
          x: {
            ticks: {
              autoSkip: true
            },
            time: {
              displayFormats: {
                'month': 'MMM'
              },
              unit: 'month'
            },
            type: 'time'
          },
        }
      }
    });

    // instantiate pie charts
    var statusesCanvas = $('#statuses_pie');
    statusesPieChart = new Chart(statusesCanvas, {
      type: 'pie',
      options: {
         layout: {
            padding: 20
         },
         plugins: {
            legend: false,
        }
      }
    });

    var prioritiesCanvas = $('#priorities_pie');
    prioritiesPieChart = new Chart(prioritiesCanvas, {
      type: 'pie',
       options: {
         layout: {
            padding: 20
         },
         plugins: {
            legend: false,
        }
      }
    });

    var domainsCanvas = $('#domains_bar');
    domainsBarChart = new Chart(domainsCanvas, {
      type: 'bar',
       options: {
         indexAxis: 'y'
      }
    });

    var globalStartDate;
    var globalEndDate;

    mapboxgl.accessToken = mapboxApiKey;
    map = new mapboxgl.Map({
      container: "map",
      style: mapStyle,
    });
    map.on('load', function () {
      const startDate = new Date()
      startDate.setFullYear(startDate.getFullYear() - 4);
      const endDate = new Date()
      $("#date-range-slider").dateRangeSlider({
        formatter: function (val) {
          return val.toLocaleString('en-uk', { month: 'long', year: 'numeric', day: 'numeric' })
        }
      });
      $("#date-range-slider").dateRangeSlider("bounds", new Date(2012, 0, 1), endDate);
      $("#date-range-slider").dateRangeSlider("values", startDate, endDate);
      $("#date-range-slider").bind("valuesChanged", function (e, data) {
        globalStartDate = data.values.min;
        globalEndDate = data.values.max;
        fetchStatisticsData(data.values.min, data.values.max)
      });
    });

    $('#id_status').on('change', function() {
        fetchStatisticsData(globalStartDate, globalEndDate)
    });
    $('#id_priority').on('change', function() {
        fetchStatisticsData(globalStartDate, globalEndDate)
    });
    $('#id_country').on('change', function() {
        fetchStatisticsData(globalStartDate, globalEndDate)
    });

  })
