import {Icon} from "./header.js";
import {html, useEffect, useMemo, useState} from "./vendor/preact-htm.module.js";

// Czech names: H is the natural B, B is B flat
const SCALE = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "H"];
const NORMALIZE = {Cb: "H", Db: "C#", Eb: "D#", Fb: "E", Gb: "F#", Ab: "G#", Hb: "A#", B: "A#", "E#": "F", "H#": "C"};
const NOTE = /[CDEFGAHB][b#]?/g;
const CHORD = /(<(?:span|rt) class="chord">)([^<]*)(<\/(?:span|rt)>)/g;

export function transposeChord(chord, amount) {
    return chord.replace(NOTE, note => {
        const index = SCALE.indexOf(NORMALIZE[note] ?? note);
        return index < 0 ? note : SCALE[(((index + amount) % 12) + 12) % 12];
    });
}

export function transposeHtml(text, amount) {
    return amount === 0 ? text : text.replace(CHORD, (_, open, chord, close) => open + transposeChord(chord, amount) + close);
}

const decoder = document.createElement("textarea");

function plainText(text) {
    const stripped = text.replace(/<\/p>|<br\s*\/?>/g, " ").replace(/<[^>]*>/g, "");
    decoder.innerHTML = stripped;
    return decoder.value;
}

export function fold(text) {
    return text.normalize("NFD").replace(/\p{M}/gu, "").toLowerCase();
}

// What a search is matched against: the name, the author and the text without markup, computed on first use
function haystack(song) {
    song.hay ??= fold(`${song.name} ${song.author ?? ""} ${plainText(song.text)}`);
    return song.hay;
}

// The songs of a route in list order, numbered from 1; archived songs are already last in the payload
export function routeRows(songs, route) {
    const chosen = route.kind === "category" ? songs.filter(song => song.cats.includes(route.key)) : songs;
    return chosen.map((song, index) => ({song, number: index + 1}));
}

// Terms are separated by `;` and every one has to occur in the number, name, author or text
export function filterRows(rows, query) {
    const terms = query.split(";").map(term => fold(term.trim())).filter(Boolean);
    if (terms.length === 0) {
        return rows;
    }
    return rows.filter(({song, number}) => {
        const text = `${number} ${haystack(song)}`;
        return terms.every(term => text.includes(term));
    });
}

function SongBody({song, me, urls, _}) {
    const [shift, setShift] = useState(0);
    const text = useMemo(() => transposeHtml(song.text, shift), [song.text, shift]);
    const next = "?next=" + encodeURIComponent(location.pathname);
    return html`
        <div class="tools">
            ${song.link && html`<a class="sb-btn sb-primary" href=${song.link} title="YouTube"><${Icon} name="play" /></a>`}
            <div class="stepper" role="group" aria-label=${_("Transpose")}>
                <button class="sb-btn" aria-label=${_("Transpose") + " −1"} onClick=${() => setShift(Math.max(-11, shift - 1))}><${Icon} name="minus" /></button>
                <output aria-label=${_("Transpose")}>${shift > 0 ? "+" + shift : shift}</output>
                <button class="sb-btn" aria-label=${_("Transpose") + " +1"} onClick=${() => setShift(Math.min(11, shift + 1))}><${Icon} name="plus" /></button>
            </div>
            ${song.capo > 0 && html`<span class="capo">${_("Capo")} ${song.capo}</span>`}
            ${me?.localadmin && html`
                <span class="gap"></span>
                <a class="sb-btn sb-ghost" href=${urls.edit.replace(/0$/, song.id) + next}><${Icon} name="edit" /> ${_("Edit")}</a>
                <a class="sb-btn sb-ghost" href=${urls.delete.replace(/0$/, song.id) + next}><${Icon} name="trash" /> ${_("Delete")}</a>`}
        </div>
        <div class="song-text" dangerouslySetInnerHTML=${{__html: text}}></div>`;
}

// The body stays drawn while the details element animates shut
function SongRow({song, number, open, setOpen, me, urls, _}) {
    const [lingering, setLingering] = useState(false);
    useEffect(() => {
        if (open) {
            setLingering(true);
            return;
        }
        const timer = setTimeout(() => setLingering(false), 300);
        return () => clearTimeout(timer);
    }, [open]);
    const toggle = event => {
        event.preventDefault();
        setOpen(current => (current === song.id ? null : song.id));
    };
    return html`
        <details class=${"song" + (song.archived ? " archived" : "")} open=${open}>
            <summary onClick=${toggle}>
                <span class="num">${number}.</span>
                <h2>${song.name}</h2>
                ${song.author && html`<small>${song.author}</small>`}
            </summary>
            ${(open || lingering) && html`<${SongBody} song=${song} me=${me} urls=${urls} _=${_} />`}
        </details>`;
}

export function SongList({rows, openId, setOpen, me, urls, _}) {
    if (rows.length === 0) {
        return html`<p class="empty">${_("No songs found")}</p>`;
    }
    return rows.map(
        ({song, number}) => html`<${SongRow} key=${song.id} song=${song} number=${number} open=${openId === song.id} setOpen=${setOpen} me=${me} urls=${urls} _=${_} />`
    );
}
