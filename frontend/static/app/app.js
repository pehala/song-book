import {html, render, useCallback, useEffect, useMemo, useState} from "./vendor/preact-htm.module.js";
import {SiteHeader, Icon, Link, closeDropdowns, useSiteHeader} from "./header.js";
import {SongList, filterRows, routeRows} from "./songs.js";
import {detectLanguage, translator} from "./i18n.js";
import {hit, inlinedJson, loadSongs} from "./store.js";

const boot = inlinedJson("boot");
if (!boot) {
    document.getElementById("app").textContent = translator(detectLanguage())("bootFailed");
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
    const [query, setQuery] = useState("");
    const [openId, setOpenId] = useState(null);
    const [scrolled, setScrolled] = useState(false);
    const site = useSiteHeader({boot});
    const {t, toast} = site;
    const route = useMemo(() => parseRoute(path), [path]);

    const navigate = useCallback(to => {
        closeDropdowns();
        history.pushState(null, "", to);
        setPath(new URL(to, location.href).pathname);
        scrollTo(0, 0);
    }, []);

    const load = useCallback(() => {
        setFailed(false);
        loadSongs(urls.songs, setSongs).catch(() => setFailed(true));
    }, []);

    useEffect(load, []);

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
        if (route.kind !== "missing") {
            hit(urls.hit, route.key);
        }
        const name = route.kind === "category" ? route.category.name : route.kind === "all" ? t("allSongs") : t("notFound");
        document.title = `${name} | ${boot.name}`;
    }, [route.key]);

    useEffect(() => {
        if (!("serviceWorker" in navigator)) {
            return;
        }
        let reloadRequested = false;
        const offer = worker =>
            toast(t("updateAvailable"), {
                label: t("reload"),
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

    let content;
    if (route.kind === "missing") {
        content = html`<p class="empty">${t("categoryMissing")} <${Link} to=${boot.index} onNavigate=${navigate}>${t("home")}<//></p>`;
    } else if (songs === null) {
        content = failed
            ? html`<p class="empty">${t("loadFailed")} <button class="sb-btn" onClick=${load}>${t("retry")}</button></p>`
            : html`<div class="spinner" role="status" aria-label=${t("loading")}></div>`;
    } else {
        content = html`
            <div class="search">
                <label for="search">${t("search")}</label>
                <input id="search" type="search" placeholder=${t("searchHint")} value=${query} onInput=${event => setQuery(event.target.value)} />
            </div>
            <${SongList} rows=${visible} openId=${openId} setOpen=${setOpenId} me=${site.me} urls=${urls} t=${t} />`;
    }

    return html`
        <${SiteHeader} site=${site} navigate=${navigate} />
        <main>${content}</main>
        ${scrolled && html`<button class="sb-btn sb-primary fab" style="top:20px" title=${t("top")} aria-label=${t("top")} onClick=${() => scrollTo({top: 0, behavior: scrollBehavior()})}><${Icon} name="up" /></button>`}
        ${openId !== null && html`<button class="sb-btn sb-primary fab" style="bottom:20px" title=${t("down")} aria-label=${t("down")} onClick=${scrollDown}><${Icon} name="down" /></button>`}`;
}

const root = document.getElementById("app");
root.replaceChildren();
render(html`<${App} />`, root);
