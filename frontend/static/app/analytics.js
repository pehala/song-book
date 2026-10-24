// Hits per day of the tenant's pages; the page loads Chart.js from the CDN before this module
import {html, useEffect, useRef, useState} from "./vendor/preact-htm.module.js";
import {mountPage} from "./page.js";

// A day between two days with the same count adds nothing to the line, so it is left out
function thinOut(values) {
    return values.map((value, index) => (values[index - 1] === value && values[index + 1] === value ? null : value));
}

// Keys are category slugs or `all`; a category that no longer exists is shown by its slug
function keyName(key, boot, _) {
    if (key === "all") {
        return _("All songs");
    }
    return boot.categories.find(category => category.slug === key)?.name ?? key;
}

function HitsChart({series, _}) {
    const canvas = useRef(null);
    const chart = useRef(null);

    useEffect(() => {
        const data = thinOut(series.hits);
        const suggestedMax = Math.max(0, ...series.hits) + 5;
        if (chart.current) {
            chart.current.data.labels = series.dates;
            chart.current.data.datasets[0].data = data;
            chart.current.options.scales.y.suggestedMax = suggestedMax;
            chart.current.update();
            return;
        }
        chart.current = new globalThis.Chart(canvas.current, {
            type: "line",
            data: {
                labels: series.dates,
                datasets: [{label: _("Hits"), data, spanGaps: true, fill: false, borderColor: "rgb(75, 192, 192)", tension: 0.01}],
            },
            options: {
                locale: document.documentElement.lang,
                scales: {
                    x: {grid: {color: "grey"}},
                    y: {suggestedMax, beginAtZero: true, ticks: {stepSize: 1}, grid: {color: "grey"}},
                },
            },
        });
    }, [series]);

    useEffect(() => () => chart.current?.destroy(), []);

    return html`<canvas ref=${canvas} width="400" height="300" role="img" aria-label=${_("Hits per day")}></canvas>`;
}

function Analytics({boot, data, _}) {
    const [key, setKey] = useState("");
    const [days, setDays] = useState(7);
    const [series, setSeries] = useState(null);
    const [failed, setFailed] = useState(false);

    useEffect(() => {
        const controller = new AbortController();
        setFailed(false);
        fetch(`${data.data}?${new URLSearchParams({key, days})}`, {signal: controller.signal})
            .then(response => {
                if (!response.ok) {
                    throw new Error(response.statusText);
                }
                return response.json();
            })
            .then(setSeries)
            .catch(error => error.name !== "AbortError" && setFailed(true));
        return () => controller.abort();
    }, [key, days]);

    const ranges = [
        [7, _("Week")],
        [30, _("Month")],
        [365, _("Year")],
    ];
    let content = null;
    if (failed) {
        content = html`<p role="alert">${_("The statistics could not be loaded")}</p>`;
    } else if (!globalThis.Chart) {
        content = html`<p role="alert">${_("The chart could not be loaded")}</p>`;
    } else if (series) {
        content = html`<${HitsChart} series=${series} _=${_} />`;
    }
    return html`
        <div class="row g-2 mb-2">
            <div class="input-group col-sm">
                <label class="input-group-text" for="keys">${_("Keys")}</label>
                <select id="keys" class="form-select" value=${key} onChange=${event => setKey(event.target.value)}>
                    <option value="">${_("All")}</option>
                    ${(series?.keys ?? []).map(name => html`<option key=${name} value=${name}>${keyName(name, boot, _)}</option>`)}
                </select>
            </div>
            <div class="input-group col-sm">
                <label class="input-group-text" for="range">${_("Date range")}</label>
                <select id="range" class="form-select" value=${days} onChange=${event => setDays(Number(event.target.value))}>
                    ${ranges.map(([count, label]) => html`<option key=${count} value=${count}>${label}</option>`)}
                </select>
            </div>
        </div>
        ${content}`;
}

mountPage(Analytics);
