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

// Calls onSongs with the stored list straight away, then with the fresh one if it differs.
// The response says `no-cache`, so the browser revalidates it by ETag itself: an unchanged list
// costs a 304, and the ETag shows that the stored copy is still current.
// Resolves when the network answered or failed with a stored copy to fall back on, rejects otherwise.
export async function loadSongs(url, onSongs) {
    const cache = await open();
    let stored = null;
    try {
        stored = (await cache?.match(url, {ignoreVary: true})) ?? null;
        if (stored) {
            onSongs(await stored.clone().json());
        }
    } catch {
        stored = null;
    }
    let response;
    try {
        response = await fetch(url);
    } catch (error) {
        if (stored) {
            return;
        }
        throw error;
    }
    if (!response.ok) {
        throw new Error(`${response.status}`);
    }
    if (stored && stored.headers.get("ETag") === response.headers.get("ETag")) {
        return;
    }
    const copy = response.clone();
    onSongs(await response.json());
    try {
        await cache?.put(url, copy);
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

// Tells the server which list was opened; `url` ends in 0, standing for the key
export function hit(url, key) {
    try {
        navigator.sendBeacon(url.replace(/0$/, key));
    } catch {
        // statistics are not worth an error
    }
}

export function csrfToken() {
    return document.cookie.match(/(?:^|; )csrftoken=([^;]*)/)?.[1] ?? "";
}
