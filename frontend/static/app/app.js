import {html, render, useCallback, useEffect, useMemo, useRef, useState} from "./vendor/preact-htm.module.js";
import {SiteHeader, Icon, Link, closeDropdowns, useSiteHeader} from "./header.js";
import {SongList, filterRows, routeRows} from "./songs.js";
import {detectLanguage, translator} from "./i18n.js";
import {inlinedJson, loadSongs, reloadSongs, remainingSeconds} from "./store.js";

const boot = inlinedJson("boot");
if (!boot) {
    document.getElementById("app").textContent = translator(detectLanguage(), {})("The page could not be loaded");
    throw new Error("The inlined bootstrap is missing or malformed");
}
const urls = boot.urls;

// The shell is served for / too; show the tenant's landing page without asking the server again
if (location.pathname === "/") {
    history.replaceState(null, "", boot.index);
}

function parseRoute(path) {
    if (path === urls.all) {
        return {kind: "all", key: "all"};
    }
    const slug = decodeURIComponent(path.match(/^\/categories\/([^/]+)$/)?.[1] ?? "");
    const category = boot.categories.find(candidate => candidate.slug === slug);
    return category ? {kind: "category", key: slug, category} : {kind: "missing", key: path};
}

function scrollBehavior() {
    return matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth";
}

// Scrolls the open song by about a screen: to the next paragraph below the first one fully in view
function scrollDown() {
    const paragraphs = [...document.querySelectorAll(".song-text p")];
    const inView = element => {
        const rect = element.getBoundingClientRect();
        return rect.top >= 0 && rect.bottom <= innerHeight;
    };
    const index = paragraphs.findIndex(inView);
    if (index >= 0 && index < paragraphs.length - 1 && !inView(paragraphs[paragraphs.length - 1])) {
        scrollBy({top: 0.8 * paragraphs[index + 1].getBoundingClientRect().top, behavior: scrollBehavior()});
    }
}

function App() {
    const [path, setPath] = useState(location.pathname);
    const [songs, setSongs] = useState(null);
    const [failed, setFailed] = useState(false);
    const [progress, setProgress] = useState(null);
    const [query, setQuery] = useState("");
    const [openId, setOpenId] = useState(null);
    const [scrolled, setScrolled] = useState(false);
    const [scrollToOpen, setScrollToOpen] = useState(false);
    const site = useSiteHeader({boot});
    const {_, toast} = site;
    const route = useMemo(() => parseRoute(path), [path]);

    const navigate = useCallback(to => {
        closeDropdowns();
        history.pushState(null, "", to);
        setPath(new URL(to, location.href).pathname);
        scrollTo(0, 0);
    }, []);

    const load = useCallback(() => {
        setFailed(false);
        loadSongs(urls.songs, setSongs, setProgress)
            .catch(() => setFailed(true))
            .finally(() => setProgress(null));
    }, []);

    useEffect(load, []);

    const reloading = useRef(false);
    const reload = useCallback(() => {
        if (reloading.current) {
            return;
        }
        reloading.current = true;
        reloadSongs(urls.songs, setSongs, setProgress)
            .then(() => toast(_("The songs were reloaded")))
            .catch(() => toast(_("The songs could not be loaded"), null, "error"))
            .finally(() => {
                reloading.current = false;
                setProgress(null);
            });
    }, [_, toast]);

    useEffect(() => {
        const onPop = () => setPath(location.pathname);
        const onScroll = () => setScrolled(scrollY > 50);
        addEventListener("popstate", onPop);
        addEventListener("scroll", onScroll, {passive: true});
        return () => {
            removeEventListener("popstate", onPop);
            removeEventListener("scroll", onScroll);
        };
    }, []);

    useEffect(() => {
        setQuery("");
        setOpenId(null);
        const name = route.kind === "category" ? route.category.name : route.kind === "all" ? _("All songs") : _("Not found");
        document.title = `${name} | ${boot.name}`;
    }, [route.key]);

    useEffect(() => {
        if (!("serviceWorker" in navigator)) {
            return;
        }
        let reloadRequested = false;
        const offer = worker =>
            toast(_("A new version is available"), {
                label: _("Reload"),
                run: () => {
                    reloadRequested = true;
                    worker.postMessage("skipWaiting");
                },
            });
        navigator.serviceWorker.addEventListener("controllerchange", () => reloadRequested && location.reload());
        navigator.serviceWorker
            .register(urls.service_worker)
            .then(registration => {
                const watch = worker =>
                    worker.addEventListener("statechange", () => {
                        if (worker.state === "installed" && navigator.serviceWorker.controller) {
                            offer(worker);
                        }
                    });
                if (registration.waiting && navigator.serviceWorker.controller) {
                    offer(registration.waiting);
                }
                if (registration.installing) {
                    watch(registration.installing);
                }
                registration.addEventListener("updatefound", () => watch(registration.installing));
            })
            .catch(() => {});
        navigator.storage?.persist?.().catch(() => {});
    }, []);

    const rows = useMemo(() => (songs && route.kind !== "missing" ? routeRows(songs, route) : []), [songs, route]);
    const visible = useMemo(() => filterRows(rows, query), [rows, query]);

    // A random song of the list as it is shown, other than the one already open
    const openRandom = useCallback(() => {
        const others = visible.filter(({song}) => song.id !== openId);
        if (others.length) {
            setOpenId(others[Math.floor(Math.random() * others.length)].song.id);
            setScrollToOpen(true);
        }
    }, [visible, openId]);

    useEffect(() => {
        if (scrollToOpen) {
            setScrollToOpen(false);
            document.querySelector("details.song[open]")?.scrollIntoView({behavior: scrollBehavior(), block: "start"});
        }
    }, [scrollToOpen]);

    let content;
    if (route.kind === "missing") {
        content = html`<p class="empty">${_("This category does not exist.")} <${Link} to=${boot.index} onNavigate=${navigate}>${_("Back to homepage")}<//></p>`;
    } else if (songs === null) {
        content = failed
            ? html`<p class="empty">${_("The songs could not be loaded")} <button class="sb-btn" onClick=${load}>${_("Try again")}</button></p>`
            : html`<${Progress} progress=${progress} label=${_("Loading songs…")} retryLabel=${_("Fetching the whole list…")} centered _=${_} />`;
    } else {
        content = html`
            <div class="search">
                <div class="input-group">
                    <label class="addon" for="search"><${Icon} name="search" /><span class="sr-only">${_("Search")}</span></label>
                    <input id="search" type="search" placeholder=${_("Number, text or author")} value=${query} onInput=${event => setQuery(event.target.value)} />
                    ${query.trim() && html`<output class="addon count" for="search">${visible.length} / ${rows.length}</output>`}
                    <button class="sb-btn" title=${_("Random song")} aria-label=${_("Random song")} disabled=${visible.length === 0} onClick=${openRandom}><${Icon} name="shuffle" /></button>
                </div>
            </div>
            <${SongList} rows=${visible} openId=${openId} setOpen=${setOpenId} me=${site.me} urls=${urls} _=${_} />`;
    }

    return html`
        <${SiteHeader} site=${site} navigate=${navigate} onReload=${reload} />
        ${songs !== null && progress && html`<${Progress} progress=${progress} label=${_("Updating songs…")} retryLabel=${_("Fetching the whole list…")} />`}
        <main>${content}</main>
        <div class="fabs">
            ${scrolled && html`<button class="sb-btn sb-primary" title=${_("Back to top")} aria-label=${_("Back to top")} onClick=${() => scrollTo({top: 0, behavior: scrollBehavior()})}><${Icon} name="up" /></button>`}
            ${openId !== null && html`<button class="sb-btn sb-primary" title=${_("Scroll down")} aria-label=${_("Scroll down")} onClick=${scrollDown}><${Icon} name="down" /></button>`}
        </div>`;
}

function formatSize(bytes) {
    return bytes < 1e6 ? `${Math.round(bytes / 1e3)} kB` : `${(bytes / 1e6).toFixed(1)} MB`;
}

// How long the last stretch of a download is looked at to tell its speed
const SPEED_WINDOW = 3000;

function formatRemaining(seconds, _) {
    return seconds < 60
        ? _("%s s left").replace("%s", Math.round(seconds))
        : _("%s min left").replace("%s", Math.round(seconds / 60));
}

// A download's progress: a bar with a caption in the page's middle while there is nothing to show, otherwise a line
// along the top. Without a known total the bar runs indeterminately.
function Progress({progress, label, retryLabel, centered, _}) {
    const {loaded, total, retry} = progress ?? {loaded: 0, total: 0};
    const samples = useRef([]);
    const text = retry ? retryLabel : label;
    const ratio = total ? Math.min(1, loaded / total) : 0;
    let detail = loaded ? formatSize(loaded) : "";
    if (centered && total) {
        const recent = samples.current;
        if (recent.length && loaded < recent[recent.length - 1].loaded) {
            recent.length = 0;
        }
        if (loaded > (recent[recent.length - 1]?.loaded ?? 0)) {
            recent.push({time: performance.now(), loaded});
        }
        while (recent.length > 2 && performance.now() - recent[0].time > SPEED_WINDOW) {
            recent.shift();
        }
        detail = `${formatSize(loaded)} / ${formatSize(total)} (${Math.round(ratio * 100)} %)`;
        const seconds = recent.length > 1 && remainingSeconds(recent, total);
        if (seconds) {
            detail += ` · ${formatRemaining(seconds, _)}`;
        }
    }
    return html`
        <div class=${`progress${centered ? " centered" : ""}${total ? "" : " indeterminate"}`} role="progressbar"
             aria-label=${text} aria-valuemin="0" aria-valuemax=${total || undefined}
             aria-valuenow=${total ? loaded : undefined}>
            <div style=${total ? {transform: `scaleX(${ratio})`} : undefined}></div>
        </div>
        ${centered && html`<p class="progress-caption" aria-hidden="true">${text} ${detail}</p>`}`;
}

const root = document.getElementById("app");
root.replaceChildren();
render(html`<${App} />`, root);
