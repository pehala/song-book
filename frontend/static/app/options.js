import {useCallback, useEffect, useState} from "./vendor/preact-htm.module.js";
import {detectLanguage} from "./i18n.js";

export function useStored(key, initial) {
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

// The options every page offers (language, theme) and the ones that only matter next to songs.
// Pages rendered by the server are in the language of the server, which the html element tells.
export function useOptions({server = false} = {}) {
    const [lang, setLang] = useState(() => (server ? document.documentElement.lang : detectLanguage()));
    const [theme, setTheme] = useStored("theme", "auto");
    const [columns, setColumns] = useStored("columns", 1);
    const [hideChords, setHideChords] = useStored("hide_chords", false);
    const [preventSleep, setPreventSleep] = useStored("prevent_sleep", false);

    useEffect(() => {
        document.documentElement.lang = lang;
    }, [lang]);

    // The attribute is Bootstrap's, so the pages that use it follow the same choice
    useEffect(() => {
        const media = matchMedia("(prefers-color-scheme: dark)");
        const apply = () => {
            document.documentElement.dataset.bsTheme = theme === "auto" ? (media.matches ? "dark" : "light") : theme;
        };
        apply();
        if (theme === "auto") {
            media.addEventListener("change", apply);
            return () => media.removeEventListener("change", apply);
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

    return {lang, setLang, theme, setTheme, columns, setColumns, hideChords, setHideChords, preventSleep, setPreventSleep};
}
