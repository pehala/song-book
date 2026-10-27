// Shows in the song editor whether the song is expected to fit on one page of the PDF.
import { pageFill, wrappedChordShare } from "./song_pdf_estimate.js";

// How far from a full page the estimate is too unsure to promise either way, as a share of the page
const MARGIN = 0.02;
// Share of wrapping lines of chords above which the song looks cramped in three columns
const CRAMPED = 0.07;

for (const indicator of document.querySelectorAll("[data-pdf-pages]")) {
  const form = indicator.closest("form");
  const icon = indicator.querySelector(".pdf-pages-icon");
  const label = indicator.querySelector(".pdf-pages-label");
  const cramped = indicator.querySelector(".pdf-pages-cramped");

  const update = () => {
    const text = form.elements.text.value;
    indicator.hidden = !text.trim();
    const columns = Number(form.elements.pdf_columns?.value ?? 2);
    const fill = pageFill(text, columns);
    const state = fill < 1 - MARGIN ? "fits" : fill <= 1 + MARGIN ? "close" : "overflows";
    indicator.dataset.state = state;
    indicator.classList.toggle("text-success", state === "fits");
    indicator.classList.toggle("text-warning-emphasis", state !== "fits");
    icon.textContent = state === "fits" ? "✓" : "⚠";
    label.textContent = indicator.dataset[state];
    cramped.hidden = columns < 3 || wrappedChordShare(text, columns) <= CRAMPED;
  };

  // On the form, because the element of the text can be replaced by an editor after this runs
  form.addEventListener("input", event => {
    if (["text", "pdf_columns"].includes(event.target.name)) {
      update();
    }
  });
  update();
}
