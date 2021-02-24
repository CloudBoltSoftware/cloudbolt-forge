import { html, render } from './node_modules/lit-html/lit-html.js';
import { fetch_via_post } from "./util.js";

export default class CostEfficiencyElement extends HTMLElement {
    constructor() {
        super();
        this.monthly_benefit = 0.0;
        this.avg_efficiency = 0;
        this.unused_resources = 0;
        this.resizable_resources = 0;
        this.services_count = 0;
        this.chart_data = {};
    }

    connectedCallback() {
        render(this.render_html(), this);
        this.update_overview()
    }

    async update_overview() {
        await this.fetch_efficiency_data();
        render(this.render_html(), this);

        // I'm not thrilled with this approach, but it works for now.
        const e = document.getElementsByTagName('cost-efficiency-chart')[0];
        e.drawChart(this.chartData());
    }

    chartData() {
        return {
            chart: {
                type: 'area',
                width: 600,
                height: 200,
                shadow: true
            },
            legend: {
                enabled: false
            },
            title: {
                text: 'Cost Efficiency'
            },
            xAxis: {
                categories: this.chart_data.labels,
                labels: {
                    enabled: false
                }
            },
            yAxis: {
                title: {
                    text: 'Percent'
                }

            },
            series: [
                {
                    name: "Time",
                    data: this.chart_data.dataset,
                    animation: false,
                },
            ],
            credits: {
                enabled: false
            }
        };
    }

    render_html() {
        const output = html`
        <h3>Cost Efficiency</h3>
        <ul>
            <li>
                Potential Benefit (Monthly)<br>
                $${parseFloat(this.monthly_benefit).toFixed(2)}
            </li>
            <li>
                Average Efficiency<br>
                ${this.avg_efficiency}
            </li>
            <li>
                Unused Resources<br>
                ${this.unused_resources}
            </li>
            <li>
                Resizable Resources<br>
                ${this.resizable_resources}
            </li>
            <li>
                Number of Services<br>
                ${this.services_count}
            </li>
            <li>
                <cost-efficiency-chart></cost-efficiency-chart>
            </li>
        </ul>
        `
        return output;
    }

    async fetch_efficiency_data() {
        const url = "/xui/kumo/api/cost_efficiency_for_rh/";
        const json = await fetch_via_post(url, 1, this.getAttribute("csrf-token"));
        const labels = []
        const dataset = []

        if (json.chart_data.categories.length) {
            json.chart_data.categories[0].category.forEach(element => {
                labels.push(element.label);
                dataset.push(element.value);
            });
        }

        json.chart_data = { labels, dataset };
        ({
            monthly_benefit: this.monthly_benefit,
            avg_efficiency: this.avg_efficiency,
            unused_resources: this.unused_resources,
            resizable_resources: this.resizable_resources,
            services_count: this.services_count,
            chart_data: this.chart_data,
        } = json);
    }

}