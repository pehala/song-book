// The songs live in the Cache API, so the reader draws at once and works offline

const CACHE = "songs";

async function open() {
    try {
        return await caches.open(CACHE);
    } catch {
        // no Cache API (insecure context, private mode)
        return null;
    }
}

// The delta is asked for from this long before the stored copy's Date: an edit's updated_at is set
// before the edit is committed, so a copy fetched in between has a later Date and lacks the edit
const SYNC_MARGIN = 60;

// The stored list brought up to date with a delta from the server, or null when the delta does not fit it
export function mergeDelta(songs, delta) {
    const byId = new Map(songs.map(song => [song.id, song]));
    const listed = new Set(delta.ids);
    if (delta.changed.some(song => !listed.has(song.id))) {
        return null;
    }
    for (const song of delta.changed) {
        byId.set(song.id, song);
    }
    const merged = delta.ids.map((id, index) => byId.has(id) && {...byId.get(id), number: index + 1});
    return merged.every(Boolean) ? merged : null;
}

// The body as text, reporting {loaded, total} to onProgress as it arrives. `total` is the uncompressed size the
// server announces, or 0 when it does not; `loaded` counts decoded bytes, so the two are comparable.
async function readText(response, onProgress) {
    const total = Number(response.headers.get("X-Songs-Size")) || 0;
    if (!response.body) {
        return response.text();
    }
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let text = "";
    let loaded = 0;
    for (;;) {
        const {done, value} = await reader.read();
        if (done) {
            return text + decoder.decode();
        }
        loaded += value.length;
        text += decoder.decode(value, {stream: true});
        onProgress?.({loaded, total});
    }
}

// Seconds a download has left, from the {time, loaded} samples of its last few seconds, or null while the speed
// is not known yet, the download has stalled or it is about to finish
export function remainingSeconds(samples, total) {
    const first = samples[0];
    const last = samples[samples.length - 1];
    const elapsed = (last.time - first.time) / 1000;
    const speed = (last.loaded - first.loaded) / elapsed;
    if (!total || elapsed < 1 || !(speed > 0)) {
        return null;
    }
    const seconds = (total - last.loaded) / speed;
    return seconds < 2 ? null : seconds;
}

// What is kept of a response: its body and the headers the next sync relies on
function keptCopy(text, response) {
    const headers = new Headers({"Content-Type": "application/json"});
    for (const name of ["ETag", "Date"]) {
        if (response.headers.has(name)) {
            headers.set(name, response.headers.get(name));
        }
    }
    return new Response(text, {headers});
}

// Asks for what changed since the stored copy when its ETag and Date are known, for the whole list otherwise.
// Sending If-None-Match makes the browser pass a 304 on instead of answering it from its own cache.
function fetchSongs(url, stored) {
    const etag = stored?.headers.get("ETag");
    const date = Date.parse(stored?.headers.get("Date"));
    if (!etag || Number.isNaN(date)) {
        return fetch(url);
    }
    const since = Math.max(0, Math.floor(date / 1000) - SYNC_MARGIN);
    return fetch(`${url}?since=${since}`, {headers: {"If-None-Match": etag}});
}

// Calls onSongs with the stored list straight away, then with the fresh one if it differs.
// An unchanged list costs a 304, a changed one only the songs that changed; a delta that does not
// fit the stored list falls back to the whole list.
// onProgress receives {loaded, total} while a body downloads, with retry set while the whole list is fetched
// again because a delta did not fit.
// Resolves when the network answered or failed with a stored copy to fall back on, rejects otherwise.
export async function loadSongs(url, onSongs, onProgress) {
    const cache = await open();
    let stored = null;
    let list = null;
    try {
        stored = (await cache?.match(url, {ignoreVary: true})) ?? null;
        if (stored) {
            list = await stored.clone().json();
            onSongs(list);
        }
    } catch {
        stored = null;
        list = null;
    }
    let response;
    try {
        response = await fetchSongs(url, stored);
    } catch (error) {
        if (stored) {
            return;
        }
        throw error;
    }
    if (response.status === 304) {
        return;
    }
    if (!response.ok) {
        throw new Error(`${response.status}`);
    }
    const text = await readText(response, onProgress);
    const body = JSON.parse(text);
    if (Array.isArray(body)) {
        onSongs(body);
        await store(cache, url, keptCopy(text, response));
        return;
    }
    const merged = list && mergeDelta(list, body);
    if (merged) {
        onSongs(merged);
        await store(cache, url, new Response(JSON.stringify(merged), {
            headers: {
                "Content-Type": "application/json",
                "ETag": body.etag,
                "Date": new Date(body.now * 1000).toUTCString(),
            },
        }));
        return;
    }
    const retry = step => onProgress?.({...step, retry: true});
    retry({loaded: 0, total: 0});
    const whole = await fetch(url);
    if (!whole.ok) {
        throw new Error(`${whole.status}`);
    }
    const wholeText = await readText(whole, retry);
    onSongs(JSON.parse(wholeText));
    await store(cache, url, keptCopy(wholeText, whole));
}

// Downloads the whole list again, past every cache, and replaces the stored copy
export async function reloadSongs(url, onSongs, onProgress) {
    const response = await fetch(url, {cache: "reload"});
    if (!response.ok) {
        throw new Error(`${response.status}`);
    }
    const text = await readText(response, onProgress);
    onSongs(JSON.parse(text));
    await store(await open(), url, keptCopy(text, response));
}

async function store(cache, url, response) {
    try {
        await cache?.put(url, response);
    } catch {
        // storage is full or blocked; the list is shown anyway
    }
}

// The stored list may hold archived songs, which must not outlive the session on a shared device
export async function deleteSongs(url) {
    try {
        await (await open())?.delete(url, {ignoreVary: true});
    } catch {
        // nothing stored
    }
}

export async function fetchMe(url) {
    try {
        const response = await fetch(url, {cache: "no-store"});
        return await response.json();
    } catch {
        return {auth: false, username: null, localadmin: false, superuser: false, messages: []};
    }
}

export function csrfToken() {
    return document.cookie.match(/(?:^|; )csrftoken=([^;]*)/)?.[1] ?? "";
}

// The JSON a page carries in `<script id=id type="application/json">`, or null when it is missing or malformed
export function inlinedJson(id) {
    try {
        return JSON.parse(document.getElementById(id).textContent);
    } catch {
        return null;
    }
}
