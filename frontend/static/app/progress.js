// The progress of a PDF being generated, polled until the file is done or failed
import {html, useEffect, useState} from "./vendor/preact-htm.module.js";
import {mountPage} from "./page.js";

const STEPS = 7;
const POLL_INTERVAL = 1000;

function stepName(step, _) {
    return [
        _("Waiting for start"),
        _("Parsing HTML"),
        _("Parsing CSS"),
        _("Applying CSS"),
        _("Creating formatting structure"),
        _("Generating layout"),
        _("Creating PDF"),
        _("Adding PDF metadata"),
    ][step];
}

function Progress({boot, data, _}) {
    const [info, setInfo] = useState(null);
    const [lost, setLost] = useState(false);

    // A failed request is retried: the connection may come back while the file renders
    useEffect(() => {
        let timer = null;
        const poll = async () => {
            try {
                const response = await fetch(data.info);
                if (!response.ok) {
                    throw new Error(response.statusText);
                }
                const current = await response.json();
                setInfo(current);
                setLost(false);
                if (current.ready || current.failed) {
                    return;
                }
            } catch {
                setLost(true);
            }
            timer = setTimeout(poll, POLL_INTERVAL);
        };
        poll();
        return () => clearTimeout(timer);
    }, []);

    const step = info?.progress ?? 0;
    const percent = Math.ceil((step / STEPS) * 100);
    let status = info ? stepName(step, _) : "";
    let bar = "progress-bar progress-bar-striped";
    if (info?.ready) {
        status = _("Completed");
        bar = "progress-bar bg-success";
    } else if (info?.failed) {
        status = _("Failed");
        bar = "progress-bar bg-danger";
    } else if (lost) {
        status = _("The progress could not be loaded");
    }
    return html`
        <div class="table-responsive">
            <table class="table table-bordered">
                <tbody>
                    <tr>
                        <th scope="row" class="w-25">${_("File name")}</th>
                        <td>${data.filename}.pdf</td>
                    </tr>
                    <tr>
                        <th scope="row" class="w-25">${_("Progress")}</th>
                        <td>
                            <div class="progress" role="progressbar" aria-label=${_("Progress")} aria-valuenow=${percent} aria-valuemin="0" aria-valuemax="100">
                                <div class=${bar} style=${{width: `${percent}%`}}>${step}/${STEPS}</div>
                            </div>
                        </td>
                    </tr>
                    <tr>
                        <th scope="row" class="w-25">${_("Status")}</th>
                        <td role="status">${status}</td>
                    </tr>
                    <tr>
                        <th scope="row" class="w-25">${_("Link")}</th>
                        <td>${info?.link && html`<a href=${info.link} target="_blank">${info.link}</a>`}</td>
                    </tr>
                </tbody>
            </table>
            <a class="btn btn-primary" href=${boot.urls.files}>${_("Back to all files")}</a>
        </div>`;
}

mountPage(Progress);
