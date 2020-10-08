const regex = /[CDEFGAH]([b#])?/g;

function transposeChord(chord, amount) {
    // const scale = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];
    // const normalizeMap = {"Cb":"B", "Db":"C#", "Eb":"D#", "Fb":"E", "Gb":"F#", "Ab":"G#", "Bb":"A#",  "E#":"F", "B#":"C"};
    const scale = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "H"];
    const normalizeMap = {"Cb":"H", "Db":"C#", "Eb":"D#", "Fb":"E", "Gb":"F#", "Ab":"G#", "Hb":"A#",  "E#":"F", "H#":"C"};
    return chord.replace(regex, function(match) {
        let i = (scale.indexOf((normalizeMap[match] ? normalizeMap[match] : match)) + amount) % scale.length;
        return scale[ i < 0 ? i + scale.length : i ];
    })
}

function transpose(event, object, id) {
    const input = $(object);
    const old_value = input.attr("previous_value");
    const new_value = input.val();
    const diff = new_value - old_value;
    $("#" + id).find(".chord").each(function(element) {
        $( this ).html(transposeChord($( this ).html(), diff))
    });
    input.attr("previous_value", new_value);
}

function collapsible(element, id) {
    const collapsible = $('#' + id);

    if (collapsible.hasClass('unrolled') === true) {
        collapsible.slideUp();
    } else {
        collapsible.slideDown();
    }
    collapsible.toggleClass("unrolled");
    element.classList.toggle("unrolled");
}