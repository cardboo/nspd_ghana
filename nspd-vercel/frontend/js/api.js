/**
 * NSPD Ghana — shared API helpers.
 *
 * Replaces the PHP server-side rendering plumbing: a fetch wrapper that
 * redirects to the login page on 401 (like require_auth()), an HTML
 * escaper (like htmlspecialchars()), and date formatters matching the
 * PHP date() formats used across the original pages.
 */

var API = {
  fetch: function (path, options) {
    options = options || {};
    options.credentials = 'same-origin';
    return fetch(path, options).then(function (response) {
      if (response.status === 401) {
        window.location.href = 'login.html';
        throw new Error('Unauthorized');
      }
      return response;
    });
  },

  json: function (path, options) {
    return API.fetch(path, options).then(function (response) {
      if (!response.ok) {
        throw new Error('Request failed with status ' + response.status);
      }
      return response.json();
    });
  }
};

/** htmlspecialchars() equivalent. */
function esc(value) {
  if (value === null || value === undefined) return '';
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

var MONTHS_SHORT = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
var MONTHS_LONG = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];

function pad2(n) {
  return n < 10 ? '0' + n : String(n);
}

/** PHP date('M d, Y') -> "Jan 05, 2026" */
function fmtDateShort(isoString) {
  if (!isoString) return '';
  var d = new Date(isoString);
  if (isNaN(d.getTime())) return '';
  return MONTHS_SHORT[d.getMonth()] + ' ' + pad2(d.getDate()) + ', ' + d.getFullYear();
}

/** PHP date('F d, Y \a\t g:i A') -> "January 05, 2026 at 3:04 PM" */
function fmtDateLong(isoString) {
  if (!isoString) return '';
  var d = new Date(isoString);
  if (isNaN(d.getTime())) return '';
  var hours = d.getHours();
  var ampm = hours >= 12 ? 'PM' : 'AM';
  var hour12 = hours % 12;
  if (hour12 === 0) hour12 = 12;
  return MONTHS_LONG[d.getMonth()] + ' ' + pad2(d.getDate()) + ', ' + d.getFullYear() +
    ' at ' + hour12 + ':' + pad2(d.getMinutes()) + ' ' + ampm;
}

/**
 * Format sea-experience years with one decimal, matching how the PHP
 * pages echoed the DECIMAL(4,1) column (e.g. "10.0").
 */
function fmtYears(value) {
  return Number(value || 0).toFixed(1);
}

/** number_format() equivalent for integer stats. */
function fmtNumber(value) {
  return Number(value || 0).toLocaleString('en-US');
}
