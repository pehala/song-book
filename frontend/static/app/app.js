import {html, render, useCallback, useEffect, useMemo, useRef, useState} from "./vendor/preact-htm.module.js";
import {LANGUAGES, detectLanguage, translator} from "./i18n.js";
import {Icon, SongList, filterRows, routeRows} from "./songs.js";
import {renderQr} from "./qr.js";
import {csrfToken, deleteSongs, fetchMe, hit, loadSongs} from "./store.js";

const boot = JSON.parse(document.getElementById("boot").textContent);
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

function useStored(key, initial) {
    const [value, setValue] = useState(() => {
        try {
            const stored = localStorage.getItem(key);
            if (stored !== null) {
                return typeof initial === "string" ? stored : JSON.parse(stored);
            }
        } catch {
            // blocked or damaged storage falls back to the default
        }
        return initial;
    });
    const set = useCallback(
        next => {
            setValue(next);
            try {
                localStorage.setItem(key, typeof next === "string" ? next : JSON.stringify(next));
            } catch {
                // the choice lasts until the page is closed
            }
        },
        [key]
    );
    return [value, set];
}

function closeDropdowns(except = null) {
    document.querySelectorAll("details.dd[open]").forEach(dropdown => {
        if (dropdown !== except) {
            dropdown.open = false;
        }
    });
}

function Link({to, onNavigate, children, ...props}) {
    const click = event => {
        if (event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
            return;
        }
        event.preventDefault();
        onNavigate(to);
    };
    return html`<a href=${to} onClick=${click} ...${props}>${children}</a>`;
}

function Dropdown({label, children}) {
    return html`<details class="dd"><summary>${label}</summary><div class="panel">${children}</div></details>`;
}

function Nav({me, t, options, navigate, showQr, logout}) {
    const [menuOpen, setMenuOpen] = useState(false);
    const go = to => {
        setMenuOpen(false);
        navigate(to);
    };
    const current = path => (path === location.pathname ? "page" : null);
    return html`
        <header class="bar">
            <${Link} class="brand" to=${boot.index} onNavigate=${go}>
                ${boot.icon && html`<img src=${boot.icon} alt="" />`}${boot.name}
            <//>
            <button class="btn burger" aria-label=${t("menu")} aria-expanded=${menuOpen} onClick=${() => setMenuOpen(!menuOpen)}><${Icon} name="menu" /></button>
            <nav class=${"menu" + (menuOpen ? " open" : "")}>
                <${Dropdown} label=${t("categories")}>
                    ${boot.categories.map(
                        category => html`<${Link} key=${category.slug} to=${urls.categories + category.slug} onNavigate=${go} aria-current=${current(urls.categories + category.slug)}>${category.name}<//>`
                    )}
                    ${boot.all_songs && html`<${Link} to=${urls.all} onNavigate=${go} aria-current=${current(urls.all)}>${t("allSongs")}<//>`}
                <//>
                ${boot.pdfs.length > 0 && html`<${Dropdown} label=${t("pdf")}>${boot.pdfs.map(file => html`<a key=${file.url} href=${file.url}>${file.name}</a>`)}<//>`}
                ${boot.links.length > 0 && html`<${Dropdown} label=${t("seeAlso")}>${boot.links.map(link => html`<a key=${link.url} href=${link.url} target="_blank" rel="noopener">${link.name}</a>`)}<//>`}
                <span class="gap"></span>
                ${me?.localadmin && html`
                    <${Dropdown} label=${t("songs")}>
                        <a href=${urls.add}>${t("addSong")}</a>
                        <a href=${urls.categories}>${t("manageCategories")}</a>
                    <//>
                    <${Dropdown} label=${t("files")}>
                        <a href=${urls.files}>${t("generatedFiles")}</a>
                        <a href=${urls.templates}>${t("templates")}</a>
                    <//>
                    <${Dropdown} label=${t("admin")}>
                        <a href=${urls.analytics}>${t("analytics")}</a>
                        <a href=${urls.tenant}>${t("editSongbook")}</a>
                        ${me.superuser && html`<a href=${urls.admin}>${t("djangoAdmin")}</a>`}
                    <//>`}
                <button class="btn" onClick=${showQr}>${t("qr")}</button>
                <${Dropdown} label=${t("options")}>
                    <label>
                        ${t("language")}
                        <select value=${options.lang} onChange=${event => options.setLang(event.target.value)}>
                            ${LANGUAGES.map(([code, name]) => html`<option key=${code} value=${code}>${name}</option>`)}
                        </select>
                    </label>
                    <div class="row" role="group" aria-label=${t("theme")}>
                        ${[["light", "sun"], ["dark", "moon"], ["auto", "auto"]].map(
                            ([name, icon]) => html`<button key=${name} class="btn" title=${t(name)} aria-label=${t(name)} aria-pressed=${options.theme === name} onClick=${() => options.setTheme(name)}><${Icon} name=${icon} /></button>`
                        )}
                    </div>
                    <label>
                        ${t("columns")}
                        <input type="number" min="1" max="9" value=${options.columns} onInput=${event => options.setColumns(Math.max(1, parseInt(event.target.value, 10) || 1))} />
                    </label>
                    <label>${t("hideChords")}<input type="checkbox" checked=${options.hideChords} onChange=${event => options.setHideChords(event.target.checked)} /></label>
                    <label>
                        ${t("preventSleep")}
                        <input type="checkbox" checked=${options.preventSleep} disabled=${!("wakeLock" in navigator)} onChange=${event => options.setPreventSleep(event.target.checked)} />
                    </label>
                    <div class="sep"></div>
                    <div class="meta"><span>${t("version")}</span><span>${boot.version}</span></div>
                    <div class="meta"><span>${t("git")}</span><span>${boot.rev}</span></div>
                <//>
                ${me?.auth
                    ? html`
                        <${Dropdown} label=${t("account")}>
                            <span>${t("loggedAs")} <b>${me.username}</b></span>
                            <a href=${urls.password}>${t("changePassword")}</a>
                            <button class="link" onClick=${logout}>${t("logout")}</button>
                        <//>`
                    : me && html`<a class="btn" href=${urls.login + "?next=" + encodeURIComponent(location.pathname)}>${t("login")}</a>`}
            </nav>
        </header>`;
}

function Toasts({toasts, dismiss}) {
    return html`
        <div class="toasts" role="status">
            ${toasts.map(
                toast => html`
                    <div class="toast" key=${toast.id}>
                        <span>${toast.text}</span>
                        ${toast.action && html`<button class="btn" onClick=${toast.action.run}>${toast.action.label}</button>`}
                        <button class="btn" aria-label=${toast.close} onClick=${() => dismiss(toast.id)}>×</button>
                    </div>`
            )}
        </div>`;
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
        scrollBy({top: 0.8 * paragraphs[index + 1].getBoundingClientRect().top, behavior: "smooth"});
    }
}

function App() {
    const [path, setPath] = useState(location.pathname);
    const [songs, setSongs] = useState(null);
    const [failed, setFailed] = useState(false);
    const [me, setMe] = useState(null);
    const [query, setQuery] = useState("");
    const [openId, setOpenId] = useState(null);
    const [toasts, setToasts] = useState([]);
    const [scrolled, setScrolled] = useState(false);
    const [qr, setQr] = useState(null);
    const [lang, setLang] = useState(detectLanguage);
    const [theme, setTheme] = useStored("theme", "auto");
    const [columns, setColumns] = useStored("columns", 1);
    const [hideChords, setHideChords] = useStored("hide_chords", false);
    const [preventSleep, setPreventSleep] = useStored("prevent_sleep", false);
    const dialog = useRef(null);
    const t = useMemo(() => translator(lang), [lang]);
    const route = useMemo(() => parseRoute(path), [path]);

    const toast = useCallback((text, action = null) => {
        const id = Math.random();
        setToasts(current => [...current, {id, text, action, close: ""}]);
        return id;
    }, []);
    const dismiss = useCallback(id => setToasts(current => current.filter(item => item.id !== id)), []);

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

    useEffect(() => {
        load();
        fetchMe(urls.me).then(current => {
            setMe(current);
            current.messages.forEach(message => {
                const id = toast(message.text);
                setTimeout(() => dismiss(id), 6000);
            });
        });
    }, []);

    useEffect(() => {
        const onPop = () => setPath(location.pathname);
        const onClick = event => closeDropdowns(event.target.closest?.("details.dd"));
        const onKey = event => event.key === "Escape" && closeDropdowns();
        const onScroll = () => setScrolled(scrollY > 50);
        addEventListener("popstate", onPop);
        addEventListener("scroll", onScroll, {passive: true});
        document.addEventListener("click", onClick);
        document.addEventListener("keydown", onKey);
        return () => {
            removeEventListener("popstate", onPop);
            removeEventListener("scroll", onScroll);
            document.removeEventListener("click", onClick);
            document.removeEventListener("keydown", onKey);
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
        document.documentElement.lang = lang;
    }, [lang]);
    useEffect(() => {
        if (theme === "light" || theme === "dark") {
            document.documentElement.dataset.theme = theme;
        } else {
            delete document.documentElement.dataset.theme;
        }
    }, [theme]);
    useEffect(() => {
        document.documentElement.classList.toggle("hide-chords", hideChords);
    }, [hideChords]);
    useEffect(() => {
        document.documentElement.style.setProperty("--chords-grid-columns", columns);
    }, [columns]);

    useEffect(() => {
        if (!preventSleep || !("wakeLock" in navigator)) {
            return;
        }
        let lock = null;
        let stopped = false;
        const request = async () => {
            try {
                lock = await navigator.wakeLock.request("screen");
                if (stopped) {
                    lock.release();
                }
            } catch {
                // refused, for example on low battery
            }
        };
        const onVisible = () => document.visibilityState === "visible" && request();
        request();
        document.addEventListener("visibilitychange", onVisible);
        return () => {
            stopped = true;
            document.removeEventListener("visibilitychange", onVisible);
            lock?.release().catch(() => {});
        };
    }, [preventSleep]);

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
            .register(urls.sw)
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

    const chooseLanguage = useCallback(
        code => {
            setLang(code);
            try {
                localStorage.setItem("lang", code);
            } catch {
                // the choice lasts until the page is closed
            }
            if (me?.auth) {
                const body = new URLSearchParams({language: code, next: location.pathname});
                fetch(urls.setlang, {method: "POST", body, headers: {"X-CSRFToken": csrfToken()}, redirect: "manual"}).catch(() => {});
            }
        },
        [me]
    );

    const logout = useCallback(async () => {
        try {
            await fetch(urls.logout, {method: "POST", headers: {"X-CSRFToken": csrfToken()}, redirect: "manual"});
        } finally {
            await deleteSongs(urls.songs);
            location.reload();
        }
    }, []);

    const showQr = useCallback(async () => {
        const dark = theme === "dark" || (theme === "auto" && matchMedia("(prefers-color-scheme: dark)").matches);
        setQr({src: await renderQr(location.href, dark), url: location.href});
    }, [theme]);
    useEffect(() => {
        if (qr && !dialog.current.open) {
            dialog.current.showModal();
        }
    }, [qr]);

    const rows = useMemo(() => (songs && route.kind !== "missing" ? routeRows(songs, route) : []), [songs, route]);
    const visible = useMemo(() => filterRows(rows, query), [rows, query]);
    const options = {lang, setLang: chooseLanguage, theme, setTheme, columns, setColumns, hideChords, setHideChords, preventSleep, setPreventSleep};

    let content;
    if (route.kind === "missing") {
        content = html`<p class="empty">${t("categoryMissing")} <${Link} to=${boot.index} onNavigate=${navigate}>${t("home")}<//></p>`;
    } else if (songs === null) {
        content = failed
            ? html`<p class="empty">${t("loadFailed")} <button class="btn" onClick=${load}>${t("retry")}</button></p>`
            : html`<div class="spinner" role="status" aria-label=${t("loading")}></div>`;
    } else {
        content = html`
            <div class="search">
                <label for="search">${t("search")}</label>
                <input id="search" type="search" placeholder=${t("searchHint")} value=${query} onInput=${event => setQuery(event.target.value)} />
            </div>
            <${SongList} rows=${visible} openId=${openId} setOpen=${setOpenId} me=${me} urls=${urls} t=${t} />`;
    }

    return html`
        <${Nav} me=${me} t=${t} options=${options} navigate=${navigate} showQr=${showQr} logout=${logout} />
        <main>${content}</main>
        ${scrolled && html`<button class="btn primary fab" style="top:20px" title=${t("top")} aria-label=${t("top")} onClick=${() => scrollTo({top: 0, behavior: "smooth"})}><${Icon} name="up" /></button>`}
        ${openId !== null && html`<button class="btn primary fab" style="bottom:20px" title=${t("down")} aria-label=${t("down")} onClick=${scrollDown}><${Icon} name="down" /></button>`}
        <${Toasts} toasts=${toasts.map(item => ({...item, close: t("close")}))} dismiss=${dismiss} />
        <dialog ref=${dialog} onClose=${() => setQr(null)}>
            <h2>${t("qrCode")}</h2>
            ${qr && html`<img src=${qr.src} alt=${t("qrCode")} /><p><a href=${qr.url}>${qr.url}</a></p>`}
            <form method="dialog"><button class="btn">${t("close")}</button></form>
        </dialog>`;
}

const root = document.getElementById("app");
root.replaceChildren();
render(html`<${App} />`, root);
