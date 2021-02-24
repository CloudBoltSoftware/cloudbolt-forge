import { html, render } from './node_modules/lit-html/lit-html.js';
import KumoGraph from './rh_graphs.js';
import { fetch_via_post } from "./util.js";

export default class CostOverviewElement extends HTMLElement {

    constructor() {
        super();
        this.total_costs = "…";
        this.monthly_budget = "?";
        this.mtd = "…";
        this.mtd_delta = "…";
        this.month_forecast = "…";
        this.month_forecast_delta = "…",
            this.ytd = "…";
        this.year_forecast = "…";
        this.cost_by_day = {};
    }

    connectedCallback() {
        render(this.render_html(), this);
        this.update_overview()
    }

    async update_overview() {
        await this.fetch_overview_data();
        render(this.render_html(), this);

        // I'm not thrilled with this apporach, but it works for now.
        const e = document.getElementsByTagName('cb-daily-cost-chart')[0];
        e.drawChart(this.chartData());
    }

    chartData() {
        return {
            chart: {
                type: 'column',
                width: 600,
                height: 200,
                shadow: true
            },
            legend: {
                enabled: false
            },
            title: {
                text: 'Cost by Day'
            },
            xAxis: {
                categories: this.cost_by_day.categories,
                labels: {
                    enabled: false
                }
            },
            yAxis: {
                title: {
                    text: '$ (USD)'
                }

            },
            series: [
                {
                    name: "Cost",
                    data: this.cost_by_day.values,
                    animation: false,
                },
            ],
            credits: {
                enabled: false
            },
            caption: {
                text: "Last 30 days"
            }
        };
    }


    render_html() {
        return html`
        <ul>
        <li>
            Total Costs<br>
            ${this.total_costs}
        </li>
        <li>
            Monthly Budget<br>
            ${this.monthly_budget}
        </li>
        <li>
            Cost by Day over Last 30 Days<br>
            <cb-daily-cost-chart></cb-daily-cost-chart>
        </li>
        <li>
            Month-to-Date<br>
            ${this.mtd} (∆ ${this.mtd_delta} vs last month)
        </li>
        <li>
            Month Forecast<br>
            ${this.month_forecast} (∆ ${this.month_forecast_delta} vs last month)
        </li>
        <li>
            Year-to-Date<br>
            ${this.ytd}
        </li>
        <li>
            Year Forecast<br>
            ${this.year_forecast}
        </li>
        </ul>
        `
    }

    async fetch_overview_data() {
        const url = "/xui/kumo/api/cost_overview_for_rh/";
        const json = await fetch_via_post(url, 1, this.getAttribute("csrf-token"));

        ({
            total_costs: this.total_costs,
            ytd: this.ytd,
            year_forecast: this.year_forecast,
            mtd: this.mtd,
            mtd_delta: this.mtd_delta,
            monthly_budget: this.monthly_budget,
            month_forecast: this.month_forecast,
            month_forecast_delta: this.month_forecast_delta,
            cost_by_day: this.cost_by_day,
        } = json);


    }

}
