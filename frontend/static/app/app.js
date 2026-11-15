import {html, render, useCallback, useEffect, useMemo, useRef, useState} from "./vendor/preact-htm.module.js";
import {SiteHeader, Icon, Link, closeDropdowns, useSiteHeader} from "./header.js";
import {SongList, filterRows, indexSongs, routeRows} from "./songs.js";
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

const SCROLL_GAP = 8;
// Scrolling takes this many ms per pixel, but never less than the first or more than the second
const SCROLL_MS_PER_PIXEL = 1.2;
const SCROLL_MIN_DURATION = 400;
const SCROLL_MAX_DURATION = 800;

let scrollAnimation = null;

function stopScrollAnimation() {
    cancelAnimationFrame(scrollAnimation);
}

// Scrolls by a distance, easing in and out, for a time that grows with the distance; the browser's own smooth scrolling
// cannot be slowed
function animateScrollBy(distance) {
    stopScrollAnimation();
    if (matchMedia("(prefers-reduced-motion: reduce)").matches) {
        scrollBy({top: distance, behavior: "auto"});
        return;
    }
    const duration = Math.min(Math.max(Math.abs(distance) * SCROLL_MS_PER_PIXEL, SCROLL_MIN_DURATION), SCROLL_MAX_DURATION);
    const start = scrollY;
    const began = performance.now();
    const step = now => {
        const progress = Math.min((now - began) / duration, 1);
        scrollTo(0, start + distance * (progress < 0.5 ? 2 * progress ** 2 : 1 - (-2 * progress + 2) ** 2 / 2));
        if (progress < 1) {
            scrollAnimation = requestAnimationFrame(step);
        }
    };
    scrollAnimation = requestAnimationFrame(step);
}

// How far below the screen a verse is still looked for; no song is longer
const BELOW = 100000;

function openVerses() {
    return [...document.querySelectorAll("details.song[open] .song-text p")].map(element => element.getBoundingClientRect());
}

// How far the open song can still be scrolled: until its last verse ends just above the bottom edge
function songRemaining(verses) {
    return verses.length ? Math.max(...verses.map(rect => rect.bottom)) - innerHeight + SCROLL_GAP : 0;
}

// Scrolls the open song by up to 80% of the screen, so that what is being read stays in view: the last verse start
// within that distance moves up under the title, but never past the end of the song
function scrollDown() {
    const title = document.querySelector("details.song[open] > summary");
    const verses = openVerses();
    const remaining = songRemaining(verses);
    if (!title || remaining <= 1) {
        return;
    }
    // where the title's bottom edge sticks: the search bar sticks to the top of the screen, the title right under it
    const top = document.querySelector(".search").offsetHeight + title.offsetHeight;
    const reach = 0.8 * (innerHeight - top);
    const distances = verses.map(rect => rect.top - top - SCROLL_GAP).filter(distance => distance > 1 && distance <= reach);
    // with no verse start in reach (one taller than the screen), move by the whole reach
    const distance = distances.length ? Math.max(...distances) : reach;
    animateScrollBy(Math.min(distance, remaining));
}

// A double click on the open song, beside its text as well as on it, scrolls it down like the button; the title, the
// tools and the links keep their own double clicks
function scrollDownOnDoubleClick(event) {
    if (event.target.closest("details.song[open]") && !event.target.closest("summary, .tools, a")) {
        scrollDown();
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
    const [canScrollDown, setCanScrollDown] = useState(false);
    const [scrollToOpen, setScrollToOpen] = useState(false);
    const top = useRef(null);
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
        addEventListener("popstate", onPop);
        return () => removeEventListener("popstate", onPop);
    }, []);

    // Back to top is offered once the strip at the top of the page has left the screen
    useEffect(() => {
        const observer = new IntersectionObserver(([entry]) => setScrolled(!entry.isIntersecting));
        observer.observe(top.current);
        return () => observer.disconnect();
    }, []);

    // Scroll down is offered while a verse of the open song reaches below the line it scrolls to: the verses are
    // watched against a band starting just under that line, so nothing is measured while the page scrolls. The band
    // follows the window's height, and the verses are watched again when transposing draws them anew.
    useEffect(() => {
        const text = openId === null ? null : document.querySelector("details.song[open] .song-text");
        if (!text) {
            setCanScrollDown(false);
            return;
        }
        const below = new Set();
        let verses = null;
        const watch = () => {
            verses?.disconnect();
            below.clear();
            verses = new IntersectionObserver(
                entries => {
                    for (const entry of entries) {
                        if (entry.isIntersecting) {
                            below.add(entry.target);
                        } else {
                            below.delete(entry.target);
                        }
                    }
                    setCanScrollDown(below.size > 0);
                },
                {rootMargin: `${SCROLL_GAP - 2 - innerHeight}px 0px ${BELOW}px 0px`}
            );
            text.querySelectorAll("p").forEach(verse => verses.observe(verse));
            // the observer answers a frame later; until then the verses are measured once
            setCanScrollDown(songRemaining(openVerses()) > 1);
        };
        const redrawn = new MutationObserver(watch);
        redrawn.observe(text, {childList: true});
        addEventListener("resize", watch);
        watch();
        return () => {
            verses.disconnect();
            redrawn.disconnect();
            removeEventListener("resize", watch);
        };
    }, [openId]);

    useEffect(() => {
        addEventListener("dblclick", scrollDownOnDoubleClick);
        // the reader's own scrolling takes over from an animation under way
        const interrupts = ["wheel", "touchstart", "keydown"];
        interrupts.forEach(type => addEventListener(type, stopScrollAnimation, {passive: true}));
        return () => {
            removeEventListener("dblclick", scrollDownOnDoubleClick);
            interrupts.forEach(type => removeEventListener(type, stopScrollAnimation));
            stopScrollAnimation();
        };
    }, []);

    // Back to top sits under the open song's sticky title, whatever height the title has
    useEffect(() => {
        const title = openId === null ? null : document.querySelector("details.song[open] > summary");
        if (!title) {
            return;
        }
        const update = () => document.documentElement.style.setProperty("--title-height", `${title.offsetHeight}px`);
        const resized = new ResizeObserver(update);
        resized.observe(title);
        return () => {
            resized.disconnect();
            document.documentElement.style.removeProperty("--title-height");
        };
    }, [openId]);

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

    // The search text is built while the reader looks at the list, not on the first key they press
    useEffect(() => {
        if (!songs) {
            return;
        }
        const job = {cancelled: false};
        indexSongs(songs, job);
        return () => {
            job.cancelled = true;
        };
    }, [songs]);

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
                    ${query.trim() && html`<output class="addon count" for="search" title=${_("Songs matching the search")}>${_("{found} of {total}").replace("{found}", visible.length).replace("{total}", rows.length)}</output>`}
                    <button class="sb-btn" title=${_("Random song")} aria-label=${_("Random song")} disabled=${visible.length === 0} onClick=${openRandom}><${Icon} name="shuffle" /></button>
                </div>
            </div>
            <${SongList} rows=${visible} openId=${openId} setOpen=${setOpenId} me=${site.me} urls=${urls} _=${_} />`;
    }

    return html`
        <div class="top-strip" ref=${top} aria-hidden="true"></div>
        <${SiteHeader} site=${site} navigate=${navigate} onReload=${reload} />
        ${songs !== null && progress && html`<${Progress} progress=${progress} label=${_("Updating songs…")} retryLabel=${_("Fetching the whole list…")} />`}
        <main class=${canScrollDown ? "can-scroll-down" : ""}>${content}</main>
        ${scrolled && html`<button class="sb-btn sb-primary fab to-top" title=${_("Back to top")} aria-label=${_("Back to top")} onClick=${() => scrollTo({top: 0, behavior: scrollBehavior()})}><${Icon} name="up" /></button>`}
        ${canScrollDown && html`<button class="sb-btn sb-primary fab to-bottom" title=${_("Scroll down")} aria-label=${_("Scroll down")} onClick=${scrollDown}><${Icon} name="down" /></button>`}`;
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
        ${centered && html`<p class="progress-caption" aria-hidden="true"><span>${text}</span><span>${detail}</span></p>`}`;
}

const root = document.getElementById("app");
root.replaceChildren();
render(html`<${App} />`, root);
