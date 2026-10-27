// Enhances the song editor: the syntax colours of the lyrics, the sections as tabs on a phone, the chord bar above the
// keyboard, brace completion, the unsaved changes with their draft, and Ctrl+S. Without it the form still works with
// every section shown. The preview is the server's: this only types text and asks the server to render a line.

import {highlight} from "./highlight.js";

const SPLIT_KEY = "sb-editor-split";
const DETAILS_KEY = "sb-editor-details";
const SAVED_COOKIE = "sb-saved";
const MIN_SPLIT = 0.2;
const MAX_SPLIT = 0.8;
const SPLIT_STEP = 0.02;
const SAVE_DELAY = 400;
const LINE_DELAY = 300;

const form = document.querySelector("[data-editor]");
const lyrics = form?.querySelector("textarea.markdownx-editor");
// The editor that colours the syntax takes the place of the lyrics' textarea before anything else is set up on it:
// `text` is what is typed into and `scroller` what scrolls
const {textarea: text, scroller} = lyrics ? highlight(lyrics) : {};

if (form && text) {
    const showTab = setupTabs();
    const unfoldDetails = setupDetailsFold();
    setupViewport();
    setupKeys();
    setupBraces();
    setupSyncedScroll();
    setupSplit();
    setupChanges();

    // A control the browser refuses to submit has to be on screen for it to be pointed at: the browser takes the reader
    // to the first one, so its section is shown and the details are unfolded when it is among them
    form.addEventListener("invalid", event => {
        const panel = event.target.closest("[data-panel]");
        if (panel && event.target === form.querySelector(":invalid")) {
            showTab(panel.dataset.panel);
            if (panel.dataset.panel === "details") {
                unfoldDetails();
            }
        }
    }, true);
}

function setupTabs() {
    const tabs = form.querySelector(".sb-ed-tabs");
    const buttons = [...tabs.querySelectorAll("[role=tab]")];
    const panels = [...form.querySelectorAll("[data-panel]")];

    // The panels the tabs do not show are d-none, which their d-xl-* classes undo where there are no tabs
    function show(name) {
        for (const button of buttons) {
            const selected = button.dataset.tab === name;
            button.classList.toggle("active", selected);
            button.setAttribute("aria-selected", selected);
            button.tabIndex = selected ? 0 : -1;
        }
        for (const panel of panels) {
            panel.classList.toggle("d-none", panel.dataset.panel !== name);
        }
    }

    tabs.hidden = false;
    for (const button of buttons) {
        button.addEventListener("click", () => show(button.dataset.tab));
        button.addEventListener("keydown", event => {
            const step = {ArrowRight: 1, ArrowLeft: -1}[event.key];
            if (step) {
                const next = buttons[(buttons.indexOf(button) + step + buttons.length) % buttons.length];
                show(next.dataset.tab);
                next.focus();
            }
        });
    }
    show(form.dataset.initialTab || "lyrics");
    return show;
}

// From 1200px the details fold away behind an arrow on their own panel, to give the text boxes the room, and the
// choice is kept. They stay unfolded for whoever needs them: the server marks the form with data-show-details for a
// song being created and for a refused form, and a field the browser wants to point at unfolds them too
function setupDetailsFold() {
    const panel = form.querySelector("[data-panel=details]");
    const button = panel.querySelector("[data-fold-row] button");
    let stored = null;

    try {
        stored = localStorage.getItem(DETAILS_KEY);
    } catch {
        // Without storage the choice lasts until the page is left
    }

    function fold(folded) {
        const title = folded ? button.dataset.titleShow : button.dataset.titleHide;
        panel.classList.toggle("sb-ed-folded", folded);
        button.setAttribute("aria-expanded", !folded);
        button.setAttribute("aria-label", title);
        button.title = title;
    }

    button.addEventListener("click", () => {
        const folded = !panel.classList.contains("sb-ed-folded");
        fold(folded);
        try {
            localStorage.setItem(DETAILS_KEY, folded ? "hidden" : "shown");
        } catch {
            // Nothing to do about a full or blocked storage
        }
    });
    fold(!form.hasAttribute("data-show-details") && stored === "hidden");
    return () => fold(false);
}

// Sizes the editor to what the keyboard leaves, which phones report through the visual viewport only
function setupViewport() {
    const viewport = window.visualViewport;
    const fit = () => {
        const root = document.documentElement.style;
        root.setProperty("--sb-top", `${form.getBoundingClientRect().top + window.scrollY}px`);
        if (viewport && viewport.scale <= 1.01) {
            root.setProperty("--sb-vh", `${viewport.height}px`);
        }
    };
    viewport?.addEventListener("resize", fit);
    window.addEventListener("resize", fit);
    // What sits above the form, like a message that is dismissed, changes where it starts without any window resizing
    new ResizeObserver(fit).observe(document.body);
    fit();
}

// What the textarea holds around its caret, as the unit the server renders for the line preview
function currentLine() {
    const {value, selectionStart} = text;
    const start = value.lastIndexOf("\n", selectionStart - 1) + 1;
    const end = value.indexOf("\n", selectionStart);
    return value.slice(start, end === -1 ? value.length : end);
}

// Types into the textarea the way the user would, so that undo still has it
function insertAt(snippet, caret = snippet.length) {
    text.focus();
    const start = text.selectionStart;
    if (!document.execCommand("insertText", false, snippet)) {
        text.setRangeText(snippet, start, text.selectionEnd, "end");
        text.dispatchEvent(new Event("input", {bubbles: true}));
    }
    text.setSelectionRange(start + caret, start + caret);
}

function setupKeys() {
    const keys = form.querySelector("[data-keys]");
    const line = keys.querySelector("[data-line]");
    const preview = form.querySelector("[data-panel=preview]");
    const csrf = form.querySelector("[name=csrfmiddlewaretoken]").value;
    let lineTimer;
    let lineRequest;
    let lineContent = null;

    function drawLine() {
        const content = currentLine();
        if (content === lineContent) {
            return;
        }
        lineRequest?.abort();
        if (!content.trim()) {
            lineContent = null;
            line.hidden = true;
            return;
        }
        lineContent = content;
        lineRequest = new AbortController();
        const body = new FormData();
        body.set("content", content);
        fetch(text.dataset.markdownxUrlsPath, {
            method: "POST",
            body,
            headers: {"X-CSRFToken": csrf, "X-Requested-With": "XMLHttpRequest"},
            signal: lineRequest.signal,
        })
            .then(response => (response.ok ? response.text() : Promise.reject(response)))
            .then(html => {
                line.innerHTML = html;
                line.hidden = false;
            })
            .catch(error => {
                if (error.name !== "AbortError") {
                    lineContent = null;
                }
            });
    }

    // The line stands in for the preview where that is not on screen, and an element that is not displayed has no
    // offset parent
    function drawLineSoon() {
        if (!preview.offsetParent) {
            clearTimeout(lineTimer);
            lineTimer = setTimeout(drawLine, LINE_DELAY);
        }
    }

    // A chord goes in front of the word that is selected, not over it
    keys.addEventListener("click", event => {
        const button = event.target.closest("button");
        if (!button) {
            return;
        }
        text.focus();
        text.setSelectionRange(text.selectionStart, text.selectionStart);
        if (button.dataset.chord) {
            insertAt(`{${button.dataset.chord}}`);
        } else if (button.dataset.insert) {
            insertAt(button.dataset.insert, button.dataset.insert === "{}" ? 1 : undefined);
        } else if (button.dataset.command) {
            document.execCommand(button.dataset.command);
        }
    });
    // Pressing a key must not take the focus from the textarea, or the keyboard goes away
    for (const type of ["pointerdown", "mousedown"]) {
        keys.addEventListener(type, event => {
            if (event.target.closest("button")) {
                event.preventDefault();
            }
        });
    }
    text.addEventListener("focus", () => form.classList.add("sb-ed-typing"));
    text.addEventListener("blur", () => form.classList.remove("sb-ed-typing"));
    text.addEventListener("input", drawLineSoon);
    document.addEventListener("selectionchange", () => {
        if (document.activeElement === text) {
            drawLineSoon();
        }
    });
    keys.hidden = false;
}

// Typing { gives {} with the caret inside, } steps over the one that is there, and Backspace removes an empty pair
function setupBraces() {
    text.addEventListener("beforeinput", event => {
        if (event.isComposing || text.selectionStart !== text.selectionEnd) {
            return;
        }
        const at = text.selectionStart;
        const {value} = text;
        if (event.inputType === "insertText" && event.data === "{") {
            event.preventDefault();
            insertAt("{}", 1);
        } else if (event.inputType === "insertText" && event.data === "}" && value[at] === "}") {
            event.preventDefault();
            text.setSelectionRange(at + 1, at + 1);
        } else if (event.inputType === "deleteContentBackward" && value[at - 1] === "{" && value[at] === "}") {
            event.preventDefault();
            text.setSelectionRange(at - 1, at + 1);
            if (!document.execCommand("delete") || text.value === value) {
                text.setRangeText("", at - 1, at + 1, "end");
                text.dispatchEvent(new Event("input", {bubbles: true}));
            }
        }
    });
}

// The share of the width the lyrics have beside the preview, from 1200px: the splitter is dragged, moved with the arrow
// keys and put back by a double click, and the share is kept.
function setupSplit() {
    const work = form.querySelector(".sb-ed-work");
    const split = work.querySelector("[data-split]");
    let share = null;

    try {
        share = Number(localStorage.getItem(SPLIT_KEY)) || null;
    } catch {
        // Storage can be blocked; the share then lasts until the page is left
    }

    function set(wanted) {
        share = wanted === null ? null : Math.min(MAX_SPLIT, Math.max(MIN_SPLIT, Math.round(wanted * 1000) / 1000));
        work.style.setProperty("--sb-split", share ?? 0.5);
        split.setAttribute("aria-valuenow", Math.round((share ?? 0.5) * 100));
        try {
            if (share) {
                localStorage.setItem(SPLIT_KEY, share);
            } else {
                localStorage.removeItem(SPLIT_KEY);
            }
        } catch {
            // Nothing to do about a full or blocked storage
        }
    }

    // A finger or a mouse takes hold of the splitter, and the browser lets go of it when the button or finger is up
    split.addEventListener("pointerdown", event => {
        event.preventDefault();
        split.setPointerCapture(event.pointerId);
    });
    split.addEventListener("pointermove", event => {
        if (split.hasPointerCapture(event.pointerId)) {
            const box = work.getBoundingClientRect();
            set((event.clientX - box.left) / box.width);
        }
    });
    split.addEventListener("dblclick", () => set(null));
    split.addEventListener("keydown", event => {
        const step = {ArrowLeft: -SPLIT_STEP, ArrowRight: SPLIT_STEP}[event.key];
        if (step) {
            event.preventDefault();
            set((share ?? 0.5) + step);
        }
    });
    set(share);
}

// The preview follows the lyrics as they are scrolled
function setupSyncedScroll() {
    const preview = form.querySelector("[data-panel=preview]");
    scroller.addEventListener("scroll", () => {
        const room = scroller.scrollHeight - scroller.clientHeight;
        if (room > 0 && preview.offsetParent) {
            preview.scrollTop = (scroller.scrollTop / room) * (preview.scrollHeight - preview.clientHeight);
        }
    });
}

// Unsaved changes: the status in the bar, a guard against leaving, a draft kept in the browser and Ctrl+S
function setupChanges() {
    const status = form.querySelector("[data-status]");
    const banner = form.querySelector("[data-draft]");
    const draftKey = `sb-draft:${location.pathname}`;
    const initial = snapshot();
    let saveTimer;
    let submitting = false;

    // What the form would send, without the token and the button that was pressed
    function snapshot() {
        return JSON.stringify([...new FormData(form)].filter(([name]) => name !== "csrfmiddlewaretoken"));
    }

    function stored() {
        try {
            return JSON.parse(localStorage.getItem(draftKey));
        } catch {
            return null;
        }
    }

    function store(draft) {
        try {
            if (draft) {
                localStorage.setItem(draftKey, JSON.stringify(draft));
            } else {
                localStorage.removeItem(draftKey);
            }
        } catch {
            // Storage can be full or blocked; the draft is a convenience
        }
    }

    function update(sent = false) {
        const now = snapshot();
        const dirty = now !== initial;
        status.hidden = !dirty;
        store(dirty ? {base: initial, now, sent} : null);
    }

    // The server tells that it saved this page by a cookie, which a new submit clears first
    function saved() {
        return document.cookie.split("; ").includes(`${SAVED_COOKIE}=${encodeURIComponent(location.pathname)}`);
    }

    function forgetSaved() {
        document.cookie = `${SAVED_COOKIE}=; max-age=0; path=/`;
    }

    function changed() {
        clearTimeout(saveTimer);
        saveTimer = setTimeout(update, SAVE_DELAY);
        status.hidden = snapshot() === initial;
    }

    function restore(entries) {
        const values = new Map();
        for (const [name, value] of entries) {
            values.set(name, [...(values.get(name) ?? []), value]);
        }
        for (const control of form.elements) {
            if (!control.name || control.name === "csrfmiddlewaretoken" || ["submit", "button"].includes(control.type)) {
                continue;
            }
            const wanted = values.get(control.name) ?? [];
            if (control.type === "checkbox" || control.type === "radio") {
                control.checked = wanted.includes(control.value);
                control.dispatchEvent(new Event("change", {bubbles: true}));
            } else {
                control.value = wanted[0] ?? "";
            }
        }
        text.dispatchEvent(new Event("input", {bubbles: true}));
        update();
    }

    form.addEventListener("input", changed);
    form.addEventListener("change", changed);
    // The draft stays until the server has saved the song: a connection that fails leaves the edits nowhere else
    form.addEventListener("submit", () => {
        submitting = true;
        clearTimeout(saveTimer);
        forgetSaved();
        update(true);
    });
    // A page restored by going back from a failed save is not being submitted any more
    window.addEventListener("pageshow", event => {
        if (event.persisted) {
            submitting = false;
        }
    });
    window.addEventListener("beforeunload", event => {
        if (!submitting && snapshot() !== initial) {
            event.preventDefault();
        }
    });
    document.addEventListener("keydown", event => {
        if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "s") {
            event.preventDefault();
            form.requestSubmit(form.querySelector("[name=continue]"));
        }
    });

    const draft = stored();
    if (draft?.sent && saved()) {
        store(null);
        forgetSaved();
    } else if (draft && draft.now !== initial) {
        banner.hidden = false;
        banner.querySelector("[data-draft-stale]").hidden = draft.base === initial;
        banner.querySelector("[data-draft-restore]").addEventListener("click", () => {
            restore(JSON.parse(draft.now));
            banner.hidden = true;
        });
        banner.querySelector("[data-draft-discard]").addEventListener("click", () => {
            store(null);
            banner.hidden = true;
        });
    } else if (draft) {
        store(null);
    }
}
