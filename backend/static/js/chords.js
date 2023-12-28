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

function transpose(event, object, id) {
    const input = $(object);
    const old_value = input.attr("previous_value");
    const new_value = input.val();
    const diff = new_value - old_value;
    $("#id" + id).find(".chord").each(function(element) {
        $( this ).html(transposeChord($( this ).html(), diff))
    });
    input.attr("previous_value", new_value);
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