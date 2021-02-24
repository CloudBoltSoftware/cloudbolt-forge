import { html, render } from './node_modules/lit-html/lit-html.js';
import { fetch_via_post } from "./util.js";

export default class SpendDetailsElement extends HTMLElement {
    constructor() {
        super();
        this.yesterdays_spend = 0.0;
        this.avg_daily_spend = 0.0;
        this.avg_monthly_spend = 0.0;
    }

    connectedCallback() {
        render(this.build_spend_output(), this);
        this.update_data();
    }

    async update_data() {
        await this.fetch_spend_data();
        render(this.build_spend_output(), this);
    }

    build_spend_output() {
        const output = html`
            <h3>Spend Details</h3>
            <ul>
                <li>
                    Yesterday's Spend<br>
                    ${this.yesterdays_spend}</li>
                <li>
                    Average Daily Cost<br>
                    ${this.avg_daily_spend}</li>
                <li>
                    Average Monthly Cost<br>
                    ${this.avg_monthly_spend}</li>
            </ul>
        `
        return output;
    }

    async fetch_spend_data() {
        const url = "/xui/kumo/api/spend_details_for_rh/";
        const json = await fetch_via_post(url, 1, this.getAttribute("csrf-token"));

        ({
            yesterdays_spend: this.yesterdays_spend,
            avg_daily_spend: this.avg_daily_spend,
            avg_monthly_spend: this.avg_monthly_spend,
        } = json);
    }

}
