export default class KumoGraph extends HTMLElement {
    constructor() {
        super();
        this.chartDiv = document.createElement('div');
        this.appendChild(this.chartDiv);
    }

    drawChart(opts) {
        $(this.chartDiv).highcharts(opts);
    }
}
