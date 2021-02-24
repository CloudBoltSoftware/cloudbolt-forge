import { html, render } from './node_modules/lit-html/lit-html.js';
import { fetch_via_post } from "./util.js";


export const CHART_TYPES = [
  'cost-efficiency', 'cost-by-year', 'cost-by-day', 'cost-by-service', 'ri-utilization'
]
export default class ChartsComponent extends HTMLElement {

  constructor() {
    super();
    this.loading = true;
    this.ri_utilization_chart_data = [];
    this.cost_efficiency_chart_data = {};
    this.cost_by_year_chart_data = {};
    this.cost_by_day_chart_data = {};
    this.cost_by_service_chart_data = {};
    this.month_to_date = 0;
    this.year_to_date = 0;
    this.year_forecast = 0;
    this.total_spend = 0;
    this.yesterday_spend = 0;
  }

  connectedCallback() {
    render(this.render_html(), this);
    this.update_overview()
  }

  async update_overview() {
    await this.fetch_overview_data();
    render(this.render_html(), this);

    CHART_TYPES.forEach(chartType => {
      // I'm not thrilled with this apporach, but it works for now.

      const e = document.getElementsByTagName(`${chartType}-chart`)[0];
      e.drawChart(this.chartData(chartType));
    })
  }

  chartConfig(chartName) {
    switch (chartName) {
      case 'cost-efficiency':
        return {
          seriesName: 'Percent', yAxisName: 'Percent', text: "Cost Efficiency",
          type: 'area', data: this.cost_efficiency_chart_data
        }
      case 'cost-by-year':
        return {
          seriesName: 'Cost', yAxisName: '$ (USD)', text: "Cost By Year",
          type: 'column', data: this.cost_by_year_chart_data
        }
      case 'cost-by-day':
        return {
          seriesName: 'Cost', yAxisName: '$ (USD)', text: "Cost By Day",
          type: 'column', data: this.cost_by_day_chart_data
        }
      case 'cost-by-service':
        return {
          legend: { enabled: true, align: 'left' }, seriesName: 'Cost',
          yAxisName: '$ (USD)', text: "Cost By Service", type: 'pie',
          data: {
            values: this.cost_by_service_chart_data.labels.map((name, i) =>
              ({ name, y: this.cost_by_service_chart_data.values[i] })
            )
          }
        }
      case 'ri-utilization':
        return {
          legend: { enabled: true, align: 'left' },
          seriesName: 'Percent', yAxisName: '', text: "RI Utilization",
          type: 'pie', data: {
            values: this.ri_utilization_chart_data.map((row) => ({ name: row.label, y: row.value }))
          }
        }
    }
  }

  chartData(chartName) {
    const {
      seriesName, data, legend, yAxisName, type, text
    } = this.chartConfig(chartName);

    return {
      chart: { type, shadow: true },
      legend: legend || { enabled: false },
      title: { text },
      xAxis: {
        categories: data.labels,
        labels: { enabled: false }
      },
      yAxis: { title: { text: yAxisName } },
      series: [{
        name: seriesName,
        data: data.values,
        animation: false,
      }],
      credits: { enabled: false },
      plotOptions: {
        pie: {
          dataLabels: { enabled: false },
          showInLegend: true,
        }
      },
    };
  }

  render_html() {
    if (this.loading) { return html`<h1>Loading data. Please wait...</h1>` }

    return html`
    <div class="row">
      <div class="chart-panel col-md-4">
        <cost-by-year-chart></cost-by-year-chart>
      </div>

      <div class="chart-panel col-md-4">
        <cost-by-day-chart></cost-by-day-chart>
      </div>

      <div class="chart-panel col-md-4">
        <cost-by-service-chart></cost-by-service-chart>
      </div>
    </div>

    <div class="row">
      <div class="chart-panel col-md-4">
        <h3>Stats</h3><br>

        <p>${`month_to_date: $${this.month_to_date}`}</p>
        <p>${`year_to_date: $${this.year_to_date}`}</p>
        <p>${`year_forecast: $${this.year_forecast}`}</p>
        <p>${`total_spend: $${this.total_spend}`}</p>
        <p>${`yesterday_spend: $${this.yesterday_spend}`}</p>
        <p>${`used_reservations: $${this.used_reservations}`}</p>
        <p>${`unused_reservations: $${this.unused_reservations}`}</p>
      </div>

      <div class="chart-panel col-md-4">
        <cost-efficiency-chart></cost-efficiency-chart>
      </div>

      <div class="chart-panel col-md-4">
        <ri-utilization-chart></ri-utilization-chart>
      </div>
    </div>
    `
  }

  async fetch_overview_data() {
    const url = "/xui/kumo/api/charts_data_rh_json/";
    const json = await fetch_via_post(url, 1, this.getAttribute("csrf-token"));
    this.loading = false;
    ({
      cost_efficiency_chart_data: this.cost_efficiency_chart_data,
      cost_by_year_chart_data: this.cost_by_year_chart_data,
      cost_by_day_chart_data: this.cost_by_day_chart_data,
      cost_by_service_chart_data: this.cost_by_service_chart_data,
      month_to_date: this.month_to_date,
      year_to_date: this.year_to_date,
      year_forecast: this.year_forecast,
      total_spend: this.total_spend,
      yesterday_spend: this.yesterday_spend,
      ri_utilization_chart_data: this.ri_utilization_chart_data,
      used_reservations: this.used_reservations,
      unused_reservations: this.unused_reservations,
    } = json);


  }

}
