import Cookies from "./js.cookie.js";

export class BooleanOption {
  constructor(checkbox, callable, defaultValue) {
    this.checkbox = checkbox;
    this.callable = callable;
    this.defaultValue = defaultValue || false;
  }

  get() {
      return this.checkbox.is(':checked')
  }

  set(value) {
      this.checkbox.prop('checked', value);
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
        option.selector().change(function () {
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
      options[name].get()
  }
  set(name, value) {
      options[name].set(value)
  }

  call(name, value) {
      options[name].call(value)
  }
}
//
// export class Options;
// export class  BooleanOption;
