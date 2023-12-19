import Cookies from "./js.cookie.js";

export class BooleanOption {
  constructor(checkbox, callable, defaultValue) {
    this.checkbox = checkbox;
    this.callable = callable;
    this.defaultValue = defaultValue || false;
  }

  get() {
      return this.checkbox.checked
  }

  set(value) {
      this.checkbox.checked = (value === "true")
  }

  call(value) {
      this.callable(value === "true" || value === true)
  }

  elements() {
      return [this.checkbox]
  }

  default() {
      return this.defaultValue
  }

  allowedValues() {
      return null
  }
}

export class CheckboxOption {
    constructor(selector, callable, defaultValue) {
    this.selector = selector
    this.callable = callable;
    this.defaultValue = defaultValue || false;
  }

  get() {
      return Array.from(this.elements()).filter(element => element.checked)[0].value
  }

  set(value) {
      Array.from(this.elements()).filter(element => element.value === value)[0].checked = true
  }

  call(value) {
      this.callable(value)
  }

  elements() {
      return document.querySelectorAll(this.selector)
  }

  default() {
      return this.defaultValue
  }

  allowedValues() {
        return Array.from(this.elements()).map(element => element.value)
  }
}
export class Options {
  constructor(options) {
    this.options = options
    for (let [name, option] of options) {
        option.elements().forEach(function (element) {
            element.addEventListener('change', function () {
                const value = option.get();
                Cookies.set(name, value, {SameSite: "Strict"})
                option.call(value)
            })
        })
        let value = Cookies.get(name)
        if ((value === undefined || value === "undefined") || (option.allowedValues() !== null && !(value in option.allowedValues()))) {
            value = option.default()
            Cookies.set(name, value, {SameSite: "Strict"})
        }
        option.set(value)
        option.call(value)
    }
  }

  get(name) {
      return this.options.get(name).get()
  }
  set(name, value) {
      this.options.get(name).set(value)
  }

  call(name, value) {
      this.options.get(name).call(value)
  }

  elements(name) {
      return this.options.get(name).elements()
  }
}
