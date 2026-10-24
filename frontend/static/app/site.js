// Draws the shared header on the pages rendered by the server
import {html, render} from "./vendor/preact-htm.module.js";
import {SiteHeader, useSiteHeader} from "./header.js";
import {inlinedJson} from "./store.js";

const boot = inlinedJson("boot");
const me = inlinedJson("me");

function Site() {
    const site = useSiteHeader({boot, initialMe: me, server: true});
    return html`<${SiteHeader} site=${site} navigate=${to => location.assign(to)} />`;
}

// Without its data the header stays out and the page keeps working without it
if (boot) {
    render(html`<${Site} />`, document.getElementById("site-header"));
}
