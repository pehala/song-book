// Service worker of the reader: the shell and its static files are served from the cache,
// everything else, the songs included, goes to the network.
const CACHE = "{{ cache_name }}";
const SHELL = "{{ shell_url }}";
const STATIC = "{{ static_url }}";
const PRECACHE = {{ precache|safe }};
const RUNTIME = {{ runtime|safe }};
// The reader's routes: the shell itself, the list of all songs and the categories
// (except the pages of the category admin that share the prefix)
const READER = /^\/(?:all|categories\/(?!(?:add|move)$)[^/]+)?$/;

self.addEventListener("install", event => {
    event.waitUntil(caches.open(CACHE).then(cache => cache.addAll([SHELL, ...PRECACHE])));
});

self.addEventListener("activate", event => {
    event.waitUntil(
        caches.keys().then(names =>
            Promise.all(names.filter(name => name.startsWith("shell-") && name !== CACHE).map(name => caches.delete(name)))
        )
    );
});

self.addEventListener("message", event => {
    if (event.data === "skipWaiting") {
        self.skipWaiting();
    }
});

self.addEventListener("fetch", event => {
    const request = event.request;
    const url = new URL(request.url);
    if (request.method !== "GET" || url.origin !== location.origin) {
        return;
    }
    if (request.mode === "navigate" && READER.test(url.pathname)) {
        event.respondWith(shell(event));
    } else if (url.pathname.startsWith(STATIC) || RUNTIME.includes(url.pathname)) {
        event.respondWith(cacheFirst(request));
    }
});

// The shell holds nothing user-specific, so one copy serves every reader route.
// Django varies it on Accept-Language, which would make cache.match miss, hence ignoreVary.
async function shell(event) {
    const cache = await caches.open(CACHE);
    const cached = await cache.match(SHELL, {ignoreVary: true});
    if (!cached) {
        return fetch(event.request);
    }
    event.waitUntil(revalidate(cache, cached));
    return cached;
}

async function revalidate(cache, cached) {
    try {
        const response = await fetch(SHELL, {cache: "no-cache"});
        if (response.ok && response.headers.get("ETag") !== cached.headers.get("ETag")) {
            await cache.put(SHELL, response);
        }
    } catch {
        // offline: the cached shell stays
    }
}

async function cacheFirst(request) {
    const cache = await caches.open(CACHE);
    const cached = await cache.match(request, {ignoreVary: true});
    if (cached) {
        return cached;
    }
    const response = await fetch(request);
    if (response.ok) {
        await cache.put(request, response.clone());
    }
    return response;
}
