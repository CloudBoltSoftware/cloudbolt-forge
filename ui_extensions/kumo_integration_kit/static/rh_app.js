import KumoGraph from './rh_graphs.js';
import ChartsComponent, { CHART_TYPES } from './charts_component.js';


// import CostOverviewElement from "./cost_overview.js";
// import SpendDetailsElement from "./spend_overview.js";
// import CostEfficiencyElement from "./cost_efficiency_overview.js";

// customElements.define('cb-daily-cost-chart', KumoGraph);
// customElements.define('cost-efficiency-chart', class extends KumoGraph { });
// customElements.define('cb-cost-overview', CostOverviewElement);
// customElements.define('cb-spend-details', SpendDetailsElement);
// customElements.define('cb-cost-efficiency', CostEfficiencyElement);


CHART_TYPES.forEach((n) => customElements.define(`${n}-chart`, class extends KumoGraph { }));
customElements.define('kumo-charts-component', ChartsComponent);
