const regex = /[CDEFGAHB]([b#])?/g;

function transposeChord(chord, amount) {
    // const scale = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];
    // const normalizeMap = {"Cb":"B", "Db":"C#", "Eb":"D#", "Fb":"E", "Gb":"F#", "Ab":"G#", "Bb":"A#",  "E#":"F", "B#":"C"};
    const scale = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "H"];
    const normalizeMap = {"Cb":"H", "Db":"C#", "Eb":"D#", "Fb":"E", "Gb":"F#", "Ab":"G#", "Hb":"A#", "B":"A#", "E#":"F", "H#":"C"};
    return chord.replace(regex, function(match) {
        let i = (scale.indexOf((normalizeMap[match] ? normalizeMap[match] : match)) + amount) % scale.length;
        return scale[ i < 0 ? i + scale.length : i ];
    })
}

function transpose(object) {
    const target = object.getAttribute("data-target")
    const old_value = object.getAttribute("data-previous-value", 0);
    const new_value = object.value;
    const diff = new_value - old_value;
    document.querySelectorAll("#" + target + " .chord").forEach(function(element) {
        element.innerText = transposeChord(element.innerText, diff)
    });
    object.setAttribute("data-previous-value", new_value);
}

function isElementInViewPort(element) {
    let rect = element.getBoundingClientRect();
    // get the height of the window
    let viewPortBottom = window.innerHeight || document.documentElement.clientHeight;
    // get the width of the window
    let viewPortRight = window.innerWidth || document.documentElement.clientWidth;

    let isTopInViewPort = rect.top >= 0,
     isLeftInViewPort = rect.left >= 0,
     isBottomInViewPort = rect.bottom <= viewPortBottom,
     isRightInViewPort = rect.right <= viewPortRight;

    // check if element is completely visible inside the viewport
     return (isTopInViewPort && isLeftInViewPort && isBottomInViewPort && isRightInViewPort);

}

function betterScrollDown() {
    let children = $(".song:visible p ")
    if (children.length === 0)
        return

    let scrollTo = null;
    for (let i = 0; i < children.length - 1; i++) {
        if (isElementInViewPort(children[i])) {
            scrollTo = children[i+1]
            console.log(i+1)
            break
        }
    }

    let last_visible = isElementInViewPort(children[children.length - 1])

    if (scrollTo !== null && !last_visible) {
        console.log(scrollTo.getBoundingClientRect().top)
        $('body,html').animate({
            scrollTop: `+=${0.8 * scrollTo.getBoundingClientRect().top}`,
        }, 800);
    }

}

function _change(source, diff) {
    const target = document.getElementById(source.getAttribute("data-target"))
    const min = parseInt(target.getAttribute("min"))
    const max = parseInt(target.getAttribute("max"))
    const previous_value = parseInt(target.value)
    target.value = Math.min(Math.max(previous_value + diff, min), max)
    target.dispatchEvent(new Event('change'));
}

function add(event, source) {
    if(!event.detail || event.detail === 1){//activate on first click only to avoid hiding again on multiple clicks
        _change(source, 1)
    }
}

function subtract(event, source) {
    if(!event.detail || event.detail === 1){//activate on first click only to avoid hiding again on multiple clicks
        _change(source, -1)
    }
}