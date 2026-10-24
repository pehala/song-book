// Czech is the default language of the songbook; the choice is kept in localStorage.lang.
// The strings are English gettext msgids; the translations come from the server's `djangojs` catalogue.
export const LANGUAGES = [
    ["cs", "Čeština"],
    ["en", "English"],
];

// The language the server chose for this browser: the pages it renders follow the same cookie
function cookieLanguage() {
    return document.cookie.match(/(?:^|; )django_language=([^;]*)/)?.[1];
}

function speaks(code) {
    return LANGUAGES.some(([language]) => language === code);
}

// The server's choice, else the stored one, else the first browser language the songbook speaks, else Czech
export function detectLanguage() {
    let stored = null;
    try {
        stored = localStorage.getItem("lang");
    } catch {
        // storage is blocked
    }
    for (const choice of [cookieLanguage(), stored]) {
        if (speaks(choice)) {
            return choice;
        }
    }
    for (const language of navigator.languages ?? []) {
        const code = language.slice(0, 2).toLowerCase();
        if (speaks(code)) {
            return code;
        }
    }
    return "cs";
}

// A message without a translation, in a language without a catalogue included, is shown as written
export function translator(language, catalogues) {
    const catalogue = catalogues?.[language] ?? {};
    return msgid => catalogue[msgid] ?? msgid;
}
