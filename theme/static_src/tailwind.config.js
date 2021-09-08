// This is a minimal config.
// If you need the full config, get it from here:
// https://unpkg.com/browse/tailwindcss@latest/stubs/defaultConfig.stub.js
module.exports = {
  purge: [],
  darkMode: 'class', // or 'media' or 'class'
  theme: {
    fontFamily:{
      body: ['Lato',]
    },
    extend: {
     fontFamily:{
      body: ['Lato',]
    },
     colors: {
        "wr-blue":"#05aaff",
        "wr-blue-light":"#3fa9f5",
        "wr-blue-dark":"#1d4ed8",
        "wr-grey":"#2a2f36",
        "wr-grey-light":"#e6e6e8",
        "wr-grey-dark":"#25292f",
        "wr-shadow":"#f4f4f4",
     },
     width: {
         '144': '36rem',
         '192': '48rem',
       },
     height: {
         '144': '36rem',
         '192': '48rem',
       }
    },
  },
  variants: {
    extend: {},
  },
  plugins: [require('@tailwindcss/line-clamp')],
}
