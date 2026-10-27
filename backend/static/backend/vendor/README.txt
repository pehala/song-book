prism-code-editor.js is prism-code-editor@5.4.0 (MIT, https://github.com/FIameCaster/prism-code-editor), which bundles the
core of Prism (MIT, https://github.com/PrismJS/prism). It exports createEditor and languages only. It is built with
esbuild@0.28.2 from this entry file, next to which prism-code-editor is installed with npm:

    export {createEditor} from "prism-code-editor";
    export {languages} from "prism-code-editor/prism";

    npx esbuild entry.js --bundle --minify --format=esm --outfile=prism-code-editor.js

prism-code-editor.css is dist/layout.css of the same package, unchanged.
