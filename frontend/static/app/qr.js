// The QR generator is only needed when a reader asks for the code, so it is imported on first use.
// Keep the import() out of modules with nested template literals: the static files storage that
// hashes module imports cannot see past them.
export async function renderQr(url, dark) {
    const {default: QrCode} = await import("../js/qr.mjs");
    return QrCode.render("svg-uri", QrCode.generate(url), {
        color: dark ? "white" : "currentColor",
        moduleRound: 1.0,
        finderRound: 0.5,
        module_size: 1,
    });
}
