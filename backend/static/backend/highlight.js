// Puts the lyrics in a code editor that colours the syntax of a song: the chords, the spaces and the braces that stand
// for no chord. The editor is a layer over a real textarea, which still takes the typing, the undo and the keyboard of a
// phone. The patterns of a chord and of spaces are the server's, which the textarea carries as data-chord-re and
// data-spaces-re, so what is coloured is what the server renders.

import {createEditor, languages} from "./vendor/prism-code-editor.js";

// The attributes of the textarea that the editor's own textarea must not take: its look and its size
const NOT_COPIED = ["class", "style", "rows", "cols"];

// The server's patterns are Python's, which writes a named group (?P<name>...)
function pattern(source) {
    return new RegExp(source.replaceAll("(?P<", "(?<"), "g");
}

// Replaces the textarea with the editor and returns the textarea the editor types into, the element that scrolls and a
// function that gives the element of a line of the text, counted from 0
export function highlight(textarea) {
    // Markdown reads an escaped character and a code span as text, so no chord starts in one; the token names carry a
    // prefix because song.css styles .chord
    languages.songbook = {
        "sb-escape": /\\[^]/g,
        "sb-code": /`[^`\n]*`/g,
        "sb-chord": {
            pattern: pattern(textarea.dataset.chordRe),
            inside: {
                "sb-chord-name": {pattern: /(^\{)[^]+(?=\}$)/, lookbehind: true},
                "sb-brace": /[{}]/,
            },
        },
        "sb-spaces": {
            pattern: pattern(textarea.dataset.spacesRe),
            inside: {"sb-spaces-count": /\d+/, "sb-spaces-mark": /\//},
        },
        "sb-stray": /[{}]/g,
    };
    const editor = createEditor(null, {
        language: "songbook",
        value: textarea.value,
        lineNumbers: false,
        wordWrap: true,
        tabSize: 4,
        class: "border rounded bg-body font-monospace",
    });

    // What the form, the label, markdownx and the editor's script know the textarea by
    const typed = editor.textarea;
    for (const {name, value} of textarea.attributes) {
        if (!NOT_COPIED.includes(name)) {
            typed.setAttribute(name, value);
        }
    }
    typed.classList.add("markdownx-editor");
    textarea.replaceWith(editor.container);
    return {textarea: typed, scroller: editor.container, line: index => editor.lines[index + 1]};
}
