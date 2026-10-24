// The header, the notices and the QR dialog, shared by the reader and by the pages the server renders
import {html, useCallback, useEffect, useMemo, useRef, useState} from "./vendor/preact-htm.module.js";
import {LANGUAGES, translator} from "./i18n.js";
import {useOptions} from "./options.js";
import QrCode from "./vendor/qr.mjs";
import {csrfToken, deleteSongs, fetchMe} from "./store.js";

export function Icon({name}) {
    return html`<svg class="sb-i" aria-hidden="true"><use href=${"#i-" + name} /></svg>`;
}

export function closeDropdowns(except = null) {
    document.querySelectorAll("details.sb-dd[open]").forEach(dropdown => {
        if (dropdown !== except) {
            dropdown.open = false;
        }
    });
}

export function Link({to, onNavigate, children, ...props}) {
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
    return html`<details class="sb-dd"><summary>${label}</summary><div class="sb-panel">${children}</div></details>`;
}

// `server` pages are rendered by Django: their language is changed by the server, and leaving is a page load
export function useSiteHeader({boot, initialMe = null, server = false}) {
    const urls = boot.urls;
    const options = useOptions({server});
    const t = useMemo(() => translator(options.lang), [options.lang]);
    const [me, setMe] = useState(initialMe);
    const [toasts, setToasts] = useState([]);
    const [qr, setQr] = useState(null);

    const dismiss = useCallback(id => setToasts(current => current.filter(item => item.id !== id)), []);
    const toast = useCallback((text, action = null, level = "info") => {
        const id = Math.random();
        setToasts(current => [...current, {id, text, action, level}]);
        return id;
    }, []);

    useEffect(() => {
        if (initialMe) {
            return;
        }
        fetchMe(urls.me).then(current => {
            setMe(current);
            current.messages.forEach(message => {
                const id = toast(message.text, null, message.level);
                setTimeout(() => dismiss(id), 6000);
            });
        });
    }, []);

    useEffect(() => {
        const onClick = event => closeDropdowns(event.target.closest?.("details.sb-dd"));
        const onKey = event => event.key === "Escape" && closeDropdowns();
        document.addEventListener("click", onClick);
        document.addEventListener("keydown", onKey);
        return () => {
            document.removeEventListener("click", onClick);
            document.removeEventListener("keydown", onKey);
        };
    }, []);

    const setLang = useCallback(
        async code => {
            options.setLang(code);
            try {
                localStorage.setItem("lang", code);
            } catch {
                // the choice lasts until the page is closed
            }
            const body = new URLSearchParams({language: code, next: location.pathname});
            try {
                await fetch(urls.setlang, {method: "POST", body, headers: {"X-CSRFToken": csrfToken()}, redirect: "manual"});
            } catch {
                // offline: the reader still speaks the language
            }
            if (server) {
                location.reload();
            }
        },
        [options.setLang, server]
    );

    const logout = useCallback(async () => {
        try {
            await fetch(urls.logout, {method: "POST", headers: {"X-CSRFToken": csrfToken()}, redirect: "manual"});
        } catch {
            toast(t("logoutFailed"), null, "error");
            return;
        }
        await deleteSongs(urls.songs);
        if (server) {
            location.assign(boot.index);
        } else {
            location.reload();
        }
    }, [server, t, toast]);

    const showQr = useCallback(() => {
        const dark = document.documentElement.dataset.bsTheme === "dark";
        const src = QrCode.render("svg-uri", QrCode.generate(location.href), {
            color: dark ? "white" : "currentColor",
            moduleRound: 1.0,
            finderRound: 0.5,
            module_size: 1,
        });
        setQr({src, url: location.href});
    }, []);

    return {boot, server, t, me, options: {...options, setLang}, toasts, toast, dismiss, logout, showQr, qr, setQr};
}

function Header({site, navigate}) {
    const {boot, t, me, options, server, showQr, logout} = site;
    const urls = boot.urls;
    const [menuOpen, setMenuOpen] = useState(false);
    const go = to => {
        setMenuOpen(false);
        navigate(to);
    };
    const current = path => (path === location.pathname ? "page" : null);
    return html`
        <header class="sb-bar">
            <${Link} class="sb-brand" to=${boot.index} onNavigate=${go}>
                ${boot.icon && html`<img src=${boot.icon} alt="" />`}${boot.name}
            <//>
            <button class="sb-btn sb-burger" aria-label=${t("menu")} aria-expanded=${menuOpen} onClick=${() => setMenuOpen(!menuOpen)}><${Icon} name="menu" /></button>
            <nav class=${"sb-menu" + (menuOpen ? " open" : "")}>
                <${Dropdown} label=${t("categories")}>
                    ${boot.categories.map(
                        category => html`<${Link} key=${category.slug} to=${urls.categories + category.slug} onNavigate=${go} aria-current=${current(urls.categories + category.slug)}>${category.name}<//>`
                    )}
                    ${boot.all_songs && html`<${Link} to=${urls.all} onNavigate=${go} aria-current=${current(urls.all)}>${t("allSongs")}<//>`}
                <//>
                ${boot.pdfs.length > 0 && html`<${Dropdown} label=${t("pdf")}>${boot.pdfs.map(file => html`<a key=${file.url} href=${file.url}>${file.name}</a>`)}<//>`}
                ${boot.links.length > 0 && html`<${Dropdown} label=${t("seeAlso")}>${boot.links.map(link => html`<a key=${link.url} href=${link.url} target="_blank" rel="noopener">${link.name}</a>`)}<//>`}
                <span class="sb-gap"></span>
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
                <${Dropdown} label=${t("options")}>
                    <label>
                        ${t("language")}
                        <select value=${options.lang} onChange=${event => options.setLang(event.target.value)}>
                            ${LANGUAGES.map(([code, name]) => html`<option key=${code} value=${code}>${name}</option>`)}
                        </select>
                    </label>
                    <div class="sb-row" role="group" aria-label=${t("theme")}>
                        ${[["light", "sun"], ["dark", "moon"], ["auto", "auto"]].map(
                            ([name, icon]) => html`<button key=${name} class="sb-btn" title=${t(name)} aria-label=${t(name)} aria-pressed=${options.theme === name} onClick=${() => options.setTheme(name)}><${Icon} name=${icon} /></button>`
                        )}
                    </div>
                    ${!server && html`
                        <label>
                            ${t("columns")}
                            <input type="number" min="1" max="9" value=${options.columns} onInput=${event => options.setColumns(Math.max(1, parseInt(event.target.value, 10) || 1))} />
                        </label>
                        <label>${t("hideChords")}<input type="checkbox" checked=${options.hideChords} onChange=${event => options.setHideChords(event.target.checked)} /></label>
                        <label>
                            ${t("preventSleep")}
                            <input type="checkbox" checked=${options.preventSleep} disabled=${!("wakeLock" in navigator)} onChange=${event => options.setPreventSleep(event.target.checked)} />
                        </label>`}
                    <div class="sb-sep"></div>
                    <div class="sb-meta"><span>${t("version")}</span><span>${boot.version}</span></div>
                    <div class="sb-meta"><span>${t("git")}</span><span>${boot.rev}</span></div>
                <//>
                ${me?.auth
                    ? html`
                        <${Dropdown} label=${t("account")}>
                            <span>${t("loggedAs")} <b>${me.username}</b></span>
                            <a href=${urls.password}>${t("changePassword")}</a>
                            <button class="sb-link" onClick=${logout}>${t("logout")}</button>
                        <//>`
                    : me && html`<a class="sb-btn" href=${urls.login + "?next=" + encodeURIComponent(location.pathname)}>${t("login")}</a>`}
                <button class="sb-btn" onClick=${showQr}>${t("qr")}</button>
            </nav>
        </header>`;
}

function Toasts({site}) {
    const {t, toasts, dismiss} = site;
    return html`
        <div class="sb-toasts" role="status">
            ${toasts.map(
                toast => html`
                    <div class=${"sb-toast sb-toast-" + toast.level} key=${toast.id}>
                        <span>${toast.text}</span>
                        ${toast.action && html`<button class="sb-btn" onClick=${toast.action.run}>${toast.action.label}</button>`}
                        <button class="sb-btn" aria-label=${t("close")} onClick=${() => dismiss(toast.id)}>×</button>
                    </div>`
            )}
        </div>`;
}

function QrDialog({site}) {
    const {t, qr, setQr} = site;
    const dialog = useRef(null);
    useEffect(() => {
        if (qr && !dialog.current.open) {
            dialog.current.showModal();
        }
    }, [qr]);
    return html`
        <dialog class="sb-dialog" ref=${dialog} onClose=${() => setQr(null)}>
            <h2>${t("qrCode")}</h2>
            ${qr && html`<img src=${qr.src} alt=${t("qrCode")} /><p><a href=${qr.url}>${qr.url}</a></p>`}
            <form method="dialog"><button class="sb-btn">${t("close")}</button></form>
        </dialog>`;
}

export function SiteHeader({site, navigate}) {
    return html`<${Header} site=${site} navigate=${navigate} /><${Toasts} site=${site} /><${QrDialog} site=${site} />`;
}
