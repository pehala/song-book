// Draws the content of a page the server renders; site.js draws its header
import {html, render} from "./vendor/preact-htm.module.js";
import {translator} from "./i18n.js";
import {inlinedJson} from "./store.js";

// The page's own data is inlined as `page-data`; it speaks the language of the server, like its header
export function mountPage(Page) {
    const boot = inlinedJson("boot");
    const data = inlinedJson("page-data");
    const _ = translator(document.documentElement.lang, boot?.i18n);
    render(html`<${Page} boot=${boot} data=${data} _=${_} />`, document.getElementById("page"));
}
