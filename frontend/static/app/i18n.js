// Czech is the default language of the songbook; the choice is kept in localStorage.lang
const dictionaries = {
    cs: {
        allSongs: "Všechno",
        categories: "Kategorie",
        pdf: "PDF",
        seeAlso: "Jiné stránky",
        options: "Možnosti",
        language: "Jazyk",
        theme: "Motiv",
        light: "Světlý",
        dark: "Tmavý",
        auto: "Automaticky",
        columns: "Sloupce",
        hideChords: "Skrýt akordy",
        preventSleep: "Zabránit uspání",
        search: "Vyhledávání",
        searchHint: "Číslo, text nebo autor",
        noResults: "Nic nenalezeno",
        transpose: "Transponovat",
        capo: "Capo",
        edit: "Upravit",
        delete: "Smazat",
        version: "Verze",
        git: "Git",
        loggedAs: "Přihlášen jako",
        login: "Přihlásit se",
        logout: "Odhlásit se",
        account: "Účet",
        changePassword: "Změnit heslo",
        qr: "QR",
        qrCode: "QR kód",
        close: "Zavřít",
        menu: "Menu",
        admin: "Administrace",
        songs: "Písničky",
        addSong: "Přidat písničku",
        manageCategories: "Kategorie",
        analytics: "Statistiky",
        editSongbook: "Upravit zpěvník",
        djangoAdmin: "Django admin",
        files: "Soubory",
        generatedFiles: "Vygenerované soubory",
        templates: "Šablony",
        loading: "Načítání…",
        loadFailed: "Písničky se nepodařilo načíst",
        logoutFailed: "Odhlášení se nezdařilo",
        bootFailed: "Stránku se nepodařilo načíst",
        retry: "Zkusit znovu",
        notFound: "Nenalezeno",
        categoryMissing: "Tato kategorie neexistuje.",
        home: "Zpátky domů",
        updateAvailable: "Je dostupná nová verze",
        reload: "Načíst znovu",
        top: "Nahoru",
        down: "Posunout dolů",
    },
    en: {
        allSongs: "All songs",
        categories: "Categories",
        pdf: "PDF",
        seeAlso: "See also",
        options: "Options",
        language: "Language",
        theme: "Theme",
        light: "Light",
        dark: "Dark",
        auto: "Auto",
        columns: "Columns",
        hideChords: "Hide chords",
        preventSleep: "Prevent sleep",
        search: "Search",
        searchHint: "Number, text or author",
        noResults: "No songs found",
        transpose: "Transpose",
        capo: "Capo",
        edit: "Edit",
        delete: "Delete",
        version: "Version",
        git: "Git",
        loggedAs: "Logged as",
        login: "Log in",
        logout: "Log out",
        account: "Account",
        changePassword: "Change password",
        qr: "QR",
        qrCode: "QR code",
        close: "Close",
        menu: "Menu",
        admin: "Admin",
        songs: "Songs",
        addSong: "Add song",
        manageCategories: "Categories",
        analytics: "Analytics",
        editSongbook: "Edit songbook",
        djangoAdmin: "Django admin",
        files: "Files",
        generatedFiles: "Generated files",
        templates: "Templates",
        loading: "Loading…",
        loadFailed: "The songs could not be loaded",
        logoutFailed: "Signing out failed",
        bootFailed: "The page could not be loaded",
        retry: "Try again",
        notFound: "Not found",
        categoryMissing: "This category does not exist.",
        home: "Back to homepage",
        updateAvailable: "A new version is available",
        reload: "Reload",
        top: "Back to top",
        down: "Scroll down",
    },
};

export const LANGUAGES = [
    ["cs", "Čeština"],
    ["en", "English"],
];

// The language the server chose for this browser: the pages it renders follow the same cookie
function cookieLanguage() {
    return document.cookie.match(/(?:^|; )django_language=([^;]*)/)?.[1];
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
        if (choice in dictionaries) {
            return choice;
        }
    }
    for (const language of navigator.languages ?? []) {
        const code = language.slice(0, 2).toLowerCase();
        if (code in dictionaries) {
            return code;
        }
    }
    return "cs";
}

export function translator(language) {
    const dictionary = dictionaries[language] ?? dictionaries.cs;
    return key => dictionary[key] ?? key;
}
