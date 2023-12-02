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

  selector() {
      return this.checkbox
  }

  default() {
      return this.defaultValue
  }
}

export class CheckboxOption {
    constructor(checkbox, callable, defaultValue) {
    this.checkbox = checkbox;
    this.callable = callable;
    this.defaultValue = defaultValue || false;
  }

  get() {
      return this.checkbox.filter(":checked").val()
  }

  set(value) {
      this.checkbox.filter("[value=" + value + "]").prop("checked", true)
  }

  call(value) {
      this.callable(value)
  }

  selector() {
      return this.checkbox
  }

  default() {
      return this.defaultValue
  }
}
export class Options {
  constructor(options) {
    this.options = options
    for (let [name, option] of options) {
        option.selector().addEventListener('change', function () {
            const value = option.get();
            Cookies.set(name, value, {SameSite: "Strict"})
            option.call(value)
        })
        let value = Cookies.get(name)
        if (value === undefined) {
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

  selector(name) {
      return this.options.get(name).selector()
  }
}
