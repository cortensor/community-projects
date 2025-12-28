"use strict";
/*
 * ATTENTION: An "eval-source-map" devtool has been used.
 * This devtool is neither made for production nor for readable output files.
 * It uses "eval()" calls to create a separate source file with attached SourceMaps in the browser devtools.
 * If you are trying to read the output file, select a different devtool (https://webpack.js.org/configuration/devtool/)
 * or disable the default devtool with "devtool: false".
 * If you are looking for production-ready output files, see mode: "production" (https://webpack.js.org/configuration/mode/).
 */
(() => {
var exports = {};
exports.id = "pages/api/auth/[...nextauth]";
exports.ids = ["pages/api/auth/[...nextauth]"];
exports.modules = {

/***/ "next-auth":
/*!****************************!*\
  !*** external "next-auth" ***!
  \****************************/
/***/ ((module) => {

module.exports = require("next-auth");

/***/ }),

/***/ "next-auth/providers/google":
/*!*********************************************!*\
  !*** external "next-auth/providers/google" ***!
  \*********************************************/
/***/ ((module) => {

module.exports = require("next-auth/providers/google");

/***/ }),

/***/ "(api)/./pages/api/auth/[...nextauth].ts":
/*!*****************************************!*\
  !*** ./pages/api/auth/[...nextauth].ts ***!
  \*****************************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

eval("__webpack_require__.r(__webpack_exports__);\n/* harmony export */ __webpack_require__.d(__webpack_exports__, {\n/* harmony export */   \"default\": () => (__WEBPACK_DEFAULT_EXPORT__)\n/* harmony export */ });\n/* harmony import */ var next_auth__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! next-auth */ \"next-auth\");\n/* harmony import */ var next_auth__WEBPACK_IMPORTED_MODULE_0___default = /*#__PURE__*/__webpack_require__.n(next_auth__WEBPACK_IMPORTED_MODULE_0__);\n/* harmony import */ var next_auth_providers_google__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! next-auth/providers/google */ \"next-auth/providers/google\");\n/* harmony import */ var next_auth_providers_google__WEBPACK_IMPORTED_MODULE_1___default = /*#__PURE__*/__webpack_require__.n(next_auth_providers_google__WEBPACK_IMPORTED_MODULE_1__);\n\n\n// Helpful runtime checks that surface missing env vars with clear errors\nconst clientId = process.env.GOOGLE_CLIENT_ID;\nconst clientSecret = process.env.GOOGLE_CLIENT_SECRET;\nconst nextAuthSecret = process.env.NEXTAUTH_SECRET;\nconst nextAuthUrl = process.env.NEXTAUTH_URL;\nif (!clientId || !clientSecret) {\n    // Throwing here gives a clear, early server-side error instead of the low-level openid-client error\n    throw new Error(\"Missing Google OAuth credentials: please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in frontend/.env.local (see .env.local.example)\");\n}\nif (!nextAuthUrl) {\n    console.warn(\"[next-auth] NEXTAUTH_URL is not set. Set NEXTAUTH_URL in frontend/.env.local (e.g. http://localhost:3000)\");\n}\nif (!nextAuthSecret) {\n    console.warn(\"[next-auth] NEXTAUTH_SECRET is not set. Generate one with: openssl rand -base64 32\");\n}\n/* harmony default export */ const __WEBPACK_DEFAULT_EXPORT__ = (next_auth__WEBPACK_IMPORTED_MODULE_0___default()({\n    providers: [\n        next_auth_providers_google__WEBPACK_IMPORTED_MODULE_1___default()({\n            clientId,\n            clientSecret\n        })\n    ],\n    session: {\n        strategy: \"jwt\"\n    },\n    secret: nextAuthSecret\n}));\n//# sourceURL=[module]\n//# sourceMappingURL=data:application/json;charset=utf-8;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiKGFwaSkvLi9wYWdlcy9hcGkvYXV0aC9bLi4ubmV4dGF1dGhdLnRzIiwibWFwcGluZ3MiOiI7Ozs7Ozs7O0FBQWdDO0FBQ3VCO0FBRXZELHlFQUF5RTtBQUN6RSxNQUFNRSxXQUFXQyxRQUFRQyxHQUFHLENBQUNDLGdCQUFnQjtBQUM3QyxNQUFNQyxlQUFlSCxRQUFRQyxHQUFHLENBQUNHLG9CQUFvQjtBQUNyRCxNQUFNQyxpQkFBaUJMLFFBQVFDLEdBQUcsQ0FBQ0ssZUFBZTtBQUNsRCxNQUFNQyxjQUFjUCxRQUFRQyxHQUFHLENBQUNPLFlBQVk7QUFFNUMsSUFBSSxDQUFDVCxZQUFZLENBQUNJLGNBQWM7SUFDOUIsb0dBQW9HO0lBQ3BHLE1BQU0sSUFBSU0sTUFDUjtBQUVKO0FBRUEsSUFBSSxDQUFDRixhQUFhO0lBQ2hCRyxRQUFRQyxJQUFJLENBQUM7QUFDZjtBQUVBLElBQUksQ0FBQ04sZ0JBQWdCO0lBQ25CSyxRQUFRQyxJQUFJLENBQUM7QUFDZjtBQUVBLGlFQUFlZCxnREFBUUEsQ0FBQztJQUN0QmUsV0FBVztRQUNUZCxpRUFBY0EsQ0FBQztZQUNiQztZQUNBSTtRQUNGO0tBQ0Q7SUFDRFUsU0FBUztRQUFFQyxVQUFVO0lBQU07SUFDM0JDLFFBQVFWO0FBQ1YsRUFBRSIsInNvdXJjZXMiOlsid2VicGFjazovL2luY2VwdGlvbi1mcm9udGVuZC8uL3BhZ2VzL2FwaS9hdXRoL1suLi5uZXh0YXV0aF0udHM/MmU4YiJdLCJzb3VyY2VzQ29udGVudCI6WyJpbXBvcnQgTmV4dEF1dGggZnJvbSBcIm5leHQtYXV0aFwiXG5pbXBvcnQgR29vZ2xlUHJvdmlkZXIgZnJvbSBcIm5leHQtYXV0aC9wcm92aWRlcnMvZ29vZ2xlXCJcblxuLy8gSGVscGZ1bCBydW50aW1lIGNoZWNrcyB0aGF0IHN1cmZhY2UgbWlzc2luZyBlbnYgdmFycyB3aXRoIGNsZWFyIGVycm9yc1xuY29uc3QgY2xpZW50SWQgPSBwcm9jZXNzLmVudi5HT09HTEVfQ0xJRU5UX0lEXG5jb25zdCBjbGllbnRTZWNyZXQgPSBwcm9jZXNzLmVudi5HT09HTEVfQ0xJRU5UX1NFQ1JFVFxuY29uc3QgbmV4dEF1dGhTZWNyZXQgPSBwcm9jZXNzLmVudi5ORVhUQVVUSF9TRUNSRVRcbmNvbnN0IG5leHRBdXRoVXJsID0gcHJvY2Vzcy5lbnYuTkVYVEFVVEhfVVJMXG5cbmlmICghY2xpZW50SWQgfHwgIWNsaWVudFNlY3JldCkge1xuICAvLyBUaHJvd2luZyBoZXJlIGdpdmVzIGEgY2xlYXIsIGVhcmx5IHNlcnZlci1zaWRlIGVycm9yIGluc3RlYWQgb2YgdGhlIGxvdy1sZXZlbCBvcGVuaWQtY2xpZW50IGVycm9yXG4gIHRocm93IG5ldyBFcnJvcihcbiAgICAnTWlzc2luZyBHb29nbGUgT0F1dGggY3JlZGVudGlhbHM6IHBsZWFzZSBzZXQgR09PR0xFX0NMSUVOVF9JRCBhbmQgR09PR0xFX0NMSUVOVF9TRUNSRVQgaW4gZnJvbnRlbmQvLmVudi5sb2NhbCAoc2VlIC5lbnYubG9jYWwuZXhhbXBsZSknXG4gIClcbn1cblxuaWYgKCFuZXh0QXV0aFVybCkge1xuICBjb25zb2xlLndhcm4oJ1tuZXh0LWF1dGhdIE5FWFRBVVRIX1VSTCBpcyBub3Qgc2V0LiBTZXQgTkVYVEFVVEhfVVJMIGluIGZyb250ZW5kLy5lbnYubG9jYWwgKGUuZy4gaHR0cDovL2xvY2FsaG9zdDozMDAwKScpXG59XG5cbmlmICghbmV4dEF1dGhTZWNyZXQpIHtcbiAgY29uc29sZS53YXJuKCdbbmV4dC1hdXRoXSBORVhUQVVUSF9TRUNSRVQgaXMgbm90IHNldC4gR2VuZXJhdGUgb25lIHdpdGg6IG9wZW5zc2wgcmFuZCAtYmFzZTY0IDMyJylcbn1cblxuZXhwb3J0IGRlZmF1bHQgTmV4dEF1dGgoe1xuICBwcm92aWRlcnM6IFtcbiAgICBHb29nbGVQcm92aWRlcih7XG4gICAgICBjbGllbnRJZCxcbiAgICAgIGNsaWVudFNlY3JldCxcbiAgICB9KSxcbiAgXSxcbiAgc2Vzc2lvbjogeyBzdHJhdGVneTogJ2p3dCcgfSxcbiAgc2VjcmV0OiBuZXh0QXV0aFNlY3JldCxcbn0pXG4iXSwibmFtZXMiOlsiTmV4dEF1dGgiLCJHb29nbGVQcm92aWRlciIsImNsaWVudElkIiwicHJvY2VzcyIsImVudiIsIkdPT0dMRV9DTElFTlRfSUQiLCJjbGllbnRTZWNyZXQiLCJHT09HTEVfQ0xJRU5UX1NFQ1JFVCIsIm5leHRBdXRoU2VjcmV0IiwiTkVYVEFVVEhfU0VDUkVUIiwibmV4dEF1dGhVcmwiLCJORVhUQVVUSF9VUkwiLCJFcnJvciIsImNvbnNvbGUiLCJ3YXJuIiwicHJvdmlkZXJzIiwic2Vzc2lvbiIsInN0cmF0ZWd5Iiwic2VjcmV0Il0sInNvdXJjZVJvb3QiOiIifQ==\n//# sourceURL=webpack-internal:///(api)/./pages/api/auth/[...nextauth].ts\n");

/***/ })

};
;

// load runtime
var __webpack_require__ = require("../../../webpack-api-runtime.js");
__webpack_require__.C(exports);
var __webpack_exec__ = (moduleId) => (__webpack_require__(__webpack_require__.s = moduleId))
var __webpack_exports__ = (__webpack_exec__("(api)/./pages/api/auth/[...nextauth].ts"));
module.exports = __webpack_exports__;

})();