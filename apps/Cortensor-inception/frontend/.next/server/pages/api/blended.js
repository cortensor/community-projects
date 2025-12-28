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
exports.id = "pages/api/blended";
exports.ids = ["pages/api/blended"];
exports.modules = {

/***/ "fs":
/*!*********************!*\
  !*** external "fs" ***!
  \*********************/
/***/ ((module) => {

module.exports = require("fs");

/***/ }),

/***/ "path":
/*!***********************!*\
  !*** external "path" ***!
  \***********************/
/***/ ((module) => {

module.exports = require("path");

/***/ }),

/***/ "(api)/./pages/api/blended.ts":
/*!******************************!*\
  !*** ./pages/api/blended.ts ***!
  \******************************/
/***/ ((__unused_webpack_module, __webpack_exports__, __webpack_require__) => {

eval("__webpack_require__.r(__webpack_exports__);\n/* harmony export */ __webpack_require__.d(__webpack_exports__, {\n/* harmony export */   \"default\": () => (/* binding */ handler)\n/* harmony export */ });\n/* harmony import */ var fs__WEBPACK_IMPORTED_MODULE_0__ = __webpack_require__(/*! fs */ \"fs\");\n/* harmony import */ var fs__WEBPACK_IMPORTED_MODULE_0___default = /*#__PURE__*/__webpack_require__.n(fs__WEBPACK_IMPORTED_MODULE_0__);\n/* harmony import */ var path__WEBPACK_IMPORTED_MODULE_1__ = __webpack_require__(/*! path */ \"path\");\n/* harmony import */ var path__WEBPACK_IMPORTED_MODULE_1___default = /*#__PURE__*/__webpack_require__.n(path__WEBPACK_IMPORTED_MODULE_1__);\n\n\nfunction latestBundleIn(dir) {\n    if (!fs__WEBPACK_IMPORTED_MODULE_0___default().existsSync(dir)) return null;\n    const files = fs__WEBPACK_IMPORTED_MODULE_0___default().readdirSync(dir).filter((f)=>f.startsWith(\"blended-\") && f.endsWith(\".json\"));\n    if (files.length === 0) return null;\n    const withStats = files.map((f)=>({\n            f,\n            m: fs__WEBPACK_IMPORTED_MODULE_0___default().statSync(path__WEBPACK_IMPORTED_MODULE_1___default().join(dir, f)).mtimeMs\n        }));\n    withStats.sort((a, b)=>b.m - a.m);\n    return path__WEBPACK_IMPORTED_MODULE_1___default().join(dir, withStats[0].f);\n}\nfunction handler(req, res) {\n    try {\n        const base = path__WEBPACK_IMPORTED_MODULE_1___default().join(process.cwd(), \"../backend\", \"out-merged\");\n        const latest = latestBundleIn(base);\n        if (!latest) return res.status(404).json({\n            error: \"no blended bundles found\"\n        });\n        const raw = fs__WEBPACK_IMPORTED_MODULE_0___default().readFileSync(latest, \"utf8\");\n        const json = JSON.parse(raw);\n        return res.json({\n            path: latest,\n            bundle: json\n        });\n    } catch (err) {\n        console.error(err);\n        return res.status(500).json({\n            error: err.message || String(err)\n        });\n    }\n}\n//# sourceURL=[module]\n//# sourceMappingURL=data:application/json;charset=utf-8;base64,eyJ2ZXJzaW9uIjozLCJmaWxlIjoiKGFwaSkvLi9wYWdlcy9hcGkvYmxlbmRlZC50cyIsIm1hcHBpbmdzIjoiOzs7Ozs7OztBQUFvQjtBQUNJO0FBR3hCLFNBQVNFLGVBQWVDLEdBQVc7SUFDakMsSUFBSSxDQUFDSCxvREFBYSxDQUFDRyxNQUFNLE9BQU87SUFDaEMsTUFBTUUsUUFBUUwscURBQWMsQ0FBQ0csS0FBS0ksTUFBTSxDQUFDLENBQUNDLElBQU1BLEVBQUVDLFVBQVUsQ0FBQyxlQUFlRCxFQUFFRSxRQUFRLENBQUM7SUFDdkYsSUFBSUwsTUFBTU0sTUFBTSxLQUFLLEdBQUcsT0FBTztJQUMvQixNQUFNQyxZQUFZUCxNQUFNUSxHQUFHLENBQUMsQ0FBQ0wsSUFBTztZQUFFQTtZQUFHTSxHQUFHZCxrREFBVyxDQUFDQyxnREFBUyxDQUFDRSxLQUFLSyxJQUFJUyxPQUFPO1FBQUM7SUFDbkZMLFVBQVVNLElBQUksQ0FBQyxDQUFDQyxHQUFHQyxJQUFNQSxFQUFFTixDQUFDLEdBQUdLLEVBQUVMLENBQUM7SUFDbEMsT0FBT2IsZ0RBQVMsQ0FBQ0UsS0FBS1MsU0FBUyxDQUFDLEVBQUUsQ0FBQ0osQ0FBQztBQUN0QztBQUVlLFNBQVNhLFFBQVFDLEdBQW1CLEVBQUVDLEdBQW9CO0lBQ3ZFLElBQUk7UUFDRixNQUFNQyxPQUFPdkIsZ0RBQVMsQ0FBQ3dCLFFBQVFDLEdBQUcsSUFBSSxjQUFjO1FBQ3BELE1BQU1DLFNBQVN6QixlQUFlc0I7UUFDOUIsSUFBSSxDQUFDRyxRQUFRLE9BQU9KLElBQUlLLE1BQU0sQ0FBQyxLQUFLQyxJQUFJLENBQUM7WUFBRUMsT0FBTztRQUEyQjtRQUM3RSxNQUFNQyxNQUFNL0Isc0RBQWUsQ0FBQzJCLFFBQVE7UUFDcEMsTUFBTUUsT0FBT0ksS0FBS0MsS0FBSyxDQUFDSDtRQUN4QixPQUFPUixJQUFJTSxJQUFJLENBQUM7WUFBRTVCLE1BQU0wQjtZQUFRUSxRQUFRTjtRQUFLO0lBQy9DLEVBQUUsT0FBT08sS0FBVTtRQUNqQkMsUUFBUVAsS0FBSyxDQUFDTTtRQUNkLE9BQU9iLElBQUlLLE1BQU0sQ0FBQyxLQUFLQyxJQUFJLENBQUM7WUFBRUMsT0FBT00sSUFBSUUsT0FBTyxJQUFJQyxPQUFPSDtRQUFLO0lBQ2xFO0FBQ0YiLCJzb3VyY2VzIjpbIndlYnBhY2s6Ly9pbmNlcHRpb24tZnJvbnRlbmQvLi9wYWdlcy9hcGkvYmxlbmRlZC50cz84ZDRjIl0sInNvdXJjZXNDb250ZW50IjpbImltcG9ydCBmcyBmcm9tIFwiZnNcIjtcbmltcG9ydCBwYXRoIGZyb20gXCJwYXRoXCI7XG5pbXBvcnQgdHlwZSB7IE5leHRBcGlSZXF1ZXN0LCBOZXh0QXBpUmVzcG9uc2UgfSBmcm9tIFwibmV4dFwiO1xuXG5mdW5jdGlvbiBsYXRlc3RCdW5kbGVJbihkaXI6IHN0cmluZykge1xuICBpZiAoIWZzLmV4aXN0c1N5bmMoZGlyKSkgcmV0dXJuIG51bGw7XG4gIGNvbnN0IGZpbGVzID0gZnMucmVhZGRpclN5bmMoZGlyKS5maWx0ZXIoKGYpID0+IGYuc3RhcnRzV2l0aChcImJsZW5kZWQtXCIpICYmIGYuZW5kc1dpdGgoXCIuanNvblwiKSk7XG4gIGlmIChmaWxlcy5sZW5ndGggPT09IDApIHJldHVybiBudWxsO1xuICBjb25zdCB3aXRoU3RhdHMgPSBmaWxlcy5tYXAoKGYpID0+ICh7IGYsIG06IGZzLnN0YXRTeW5jKHBhdGguam9pbihkaXIsIGYpKS5tdGltZU1zIH0pKTtcbiAgd2l0aFN0YXRzLnNvcnQoKGEsIGIpID0+IGIubSAtIGEubSk7XG4gIHJldHVybiBwYXRoLmpvaW4oZGlyLCB3aXRoU3RhdHNbMF0uZik7XG59XG5cbmV4cG9ydCBkZWZhdWx0IGZ1bmN0aW9uIGhhbmRsZXIocmVxOiBOZXh0QXBpUmVxdWVzdCwgcmVzOiBOZXh0QXBpUmVzcG9uc2UpIHtcbiAgdHJ5IHtcbiAgICBjb25zdCBiYXNlID0gcGF0aC5qb2luKHByb2Nlc3MuY3dkKCksIFwiLi4vYmFja2VuZFwiLCBcIm91dC1tZXJnZWRcIik7XG4gICAgY29uc3QgbGF0ZXN0ID0gbGF0ZXN0QnVuZGxlSW4oYmFzZSk7XG4gICAgaWYgKCFsYXRlc3QpIHJldHVybiByZXMuc3RhdHVzKDQwNCkuanNvbih7IGVycm9yOiBcIm5vIGJsZW5kZWQgYnVuZGxlcyBmb3VuZFwiIH0pO1xuICAgIGNvbnN0IHJhdyA9IGZzLnJlYWRGaWxlU3luYyhsYXRlc3QsIFwidXRmOFwiKTtcbiAgICBjb25zdCBqc29uID0gSlNPTi5wYXJzZShyYXcpO1xuICAgIHJldHVybiByZXMuanNvbih7IHBhdGg6IGxhdGVzdCwgYnVuZGxlOiBqc29uIH0pO1xuICB9IGNhdGNoIChlcnI6IGFueSkge1xuICAgIGNvbnNvbGUuZXJyb3IoZXJyKTtcbiAgICByZXR1cm4gcmVzLnN0YXR1cyg1MDApLmpzb24oeyBlcnJvcjogZXJyLm1lc3NhZ2UgfHwgU3RyaW5nKGVycikgfSk7XG4gIH1cbn1cbiJdLCJuYW1lcyI6WyJmcyIsInBhdGgiLCJsYXRlc3RCdW5kbGVJbiIsImRpciIsImV4aXN0c1N5bmMiLCJmaWxlcyIsInJlYWRkaXJTeW5jIiwiZmlsdGVyIiwiZiIsInN0YXJ0c1dpdGgiLCJlbmRzV2l0aCIsImxlbmd0aCIsIndpdGhTdGF0cyIsIm1hcCIsIm0iLCJzdGF0U3luYyIsImpvaW4iLCJtdGltZU1zIiwic29ydCIsImEiLCJiIiwiaGFuZGxlciIsInJlcSIsInJlcyIsImJhc2UiLCJwcm9jZXNzIiwiY3dkIiwibGF0ZXN0Iiwic3RhdHVzIiwianNvbiIsImVycm9yIiwicmF3IiwicmVhZEZpbGVTeW5jIiwiSlNPTiIsInBhcnNlIiwiYnVuZGxlIiwiZXJyIiwiY29uc29sZSIsIm1lc3NhZ2UiLCJTdHJpbmciXSwic291cmNlUm9vdCI6IiJ9\n//# sourceURL=webpack-internal:///(api)/./pages/api/blended.ts\n");

/***/ })

};
;

// load runtime
var __webpack_require__ = require("../../webpack-api-runtime.js");
__webpack_require__.C(exports);
var __webpack_exec__ = (moduleId) => (__webpack_require__(__webpack_require__.s = moduleId))
var __webpack_exports__ = (__webpack_exec__("(api)/./pages/api/blended.ts"));
module.exports = __webpack_exports__;

})();