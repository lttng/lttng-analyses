var margin = {top: 20, right: 20, bottom: 30, left: 60},
width = 1280 - margin.left - margin.right,
height = 720 - margin.top - margin.bottom;

var x = d3.time.scale()
    .range([0, width]);

var y = d3.scale.log()
    .range([height, 0]);

var color = d3.scale.category10();

var xAxis = d3.svg.axis()
    .scale(x)
    .orient("bottom")
    .tickFormat(d3.time.format("%H:%M:%S"));

var yAxis = d3.svg.axis()
    .scale(y)
    .orient("left");

var svg = d3.select("body").append("svg")
    .attr("width", width + margin.left + margin.right)
    .attr("height", height + margin.top + margin.bottom)
    .append("g")
    .attr("transform", "translate(" + margin.left + "," + margin.top + ")");


svg.append("text")
    .attr("class", "loading")
    .text("Loading...")
    .attr("x", width / 2)
    .attr("y", height / 2);

d3.json("latencies.json", function (error, json) {
    if (error)
        return console.warn(error);

    data = json;

    data.forEach(function (d) {
        d[0] = new Date(d[0] / 1000000); // ns to ms, to Date
        d[1] = d[1] / 1000000; // ns to ms
    });

    x.domain(d3.extent(data, function (d) {
        return d[0];
    }));

    y.domain(d3.extent(data, function (d) {
        if(d[1])
            return d[1];
    }));

    svg.append("g")
        .attr("class", "x axis")
        .attr("transform", "translate(0," + height + ")")
        .call(xAxis)
        .append("text")
        .attr("class", "label")
        .attr("x", width)
        .attr("y", -6)
        .style("text-anchor", "end")
        .text("Time");

    svg.append("g")
        .attr("class", "y axis")
        .call(yAxis)
        .append("text")
        .attr("class", "label")
        .attr("transform", "rotate(-90)")
        .attr("y", 6)
        .attr("dy", ".71em")
        .style("text-anchor", "end")
        .text("Latency (ms)");

    svg.selectAll(".loading").remove();

    svg.selectAll(".dot")
        .data(data)
        .enter().append("circle")
        .attr("class", "dot")
        .attr("r", 1.5)
        .attr("cx", function (d) { return x(d[0]); })
        .attr("cy", function (d) { return y(d[1]); })
});
