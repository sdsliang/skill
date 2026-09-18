import assert from "node:assert/strict";
import test from "node:test";
import { parseCitationJson, renderCitationMarkers, renderCitationReport, validateCitationPair } from "../runtime/citation-renderer.mjs";

const source = (overrides = {}) => ({ title: "Source", link: "https://example.com/source", paper_release_time_str: "2024-02-29", ...overrides });
const validate = (overrides) => validateCitationPair("Claim{{ref_1}}", { ref_1: source(overrides) });

test("current contract accepts JSON strings, repeated markers and unordered contiguous keys", () => {
  const refs = { ref_2: source({ link: "", paper_release_time_str: "" }), ref_1: source() };
  assert.equal(validateCitationPair("B{{ref_2}} A{{ref_1}}{{ref_1}}", JSON.stringify(refs)), true);
  assert.equal(validateCitationPair("No references", {}), true);
  assert.equal(validate({ title: " A & <B> ", link: "http://example.com/?a=1&b=2" }), true);
});

test("missing, unused and noncontiguous references fail", () => {
  assert.throws(() => validateCitationPair("{{ref_1}}", {}), /citation_marker_key_mismatch/);
  assert.throws(() => validateCitationPair("No citations", { ref_1: source() }), /citation_marker_key_mismatch/);
  assert.throws(() => validateCitationPair("{{ref_2}}", { ref_2: source() }), /citation_keys_not_contiguous/);
  assert.throws(() => validateCitationPair("{{ref_1}}{{ref_3}}", { ref_1: source(), ref_3: source() }), /citation_keys_not_contiguous/);
});

test("malformed and unresolved markers cannot disappear from validation", () => {
  for (const marker of ["{{ref_n}}", "{{ref_0}}", "{{ref_01}}", "{{ref_-1}}", "{{ref_1.0}}", "{{ ref_1 }}", "{{ref_1}", "{ref_1}}", "{ref_1}", "{{ref_1", "ref_1}}", "{{{ref_1}}}", "{{ref_1}}}", "{{pending}}", "{{ref_1\n}}"] ) {
    assert.throws(() => validateCitationPair(marker, {}), /citation_marker_invalid/, marker);
    assert.throws(() => validateCitationPair(`Valid{{ref_1}} ${marker}`, { ref_1: source() }), /citation_marker_invalid/, marker);
  }
});

test("titles must be nonblank; all three fields must be strings", () => {
  for (const title of ["", " ", "\n\t", "\u00a0"]) assert.throws(() => validate({ title }), /citation_title_empty/);
  for (const key of ["title", "link", "paper_release_time_str"]) {
    for (const value of [null, 123, [], {}, false]) assert.throws(() => validate({ [key]: value }), /citation_field_type_invalid/);
    const entry = source();
    delete entry[key];
    assert.throws(() => validateCitationPair("{{ref_1}}", { ref_1: entry }), /citation_fields_invalid/);
  }
  assert.throws(() => validate({ extra: "value" }), /citation_fields_invalid/);
});

test("only real calendar dates or empty dates pass", () => {
  for (const value of ["", "2025-01-01", "2000-02-29"]) assert.equal(validate({ paper_release_time_str: value }), true);
  for (const value of [" ", "2025-1-01", "2025-01-01 00:00:00", "2025-01-01T00:00:00Z", "2025-02-29", "2024-02-30", "2025-13-01", "2025-00-10", "2025-01-00"] ) {
    assert.throws(() => validate({ paper_release_time_str: value }), /citation_date_invalid/, value);
  }
});

test("validator accepts empty/HTTP(S) links and rejects unsafe or malformed links", () => {
  for (const link of ["", "https://example.com", "HTTP://example.com/path", "https://example.com/?q=%20"]) assert.equal(validate({ link }), true);
  for (const link of [" ", "/relative", "//example.com", "javascript:alert(1)", "data:text/html,test", "ftp://example.com", "https://", "https:example.com", " https://example.com", "https://exam\nple.com", "https://example.com/a b"]) {
    assert.throws(() => validate({ link }), /citation_link_invalid/, link);
  }
  assert.equal(renderCitationReport("{{ref_1}}", { ref_1: source({ link: "" }) }), "{{ref_1}}");
  assert.equal(renderCitationMarkers("{{ref_1}}", { ref_1: source({ link: "javascript:alert(1)" }) }), "{{ref_1}}");
});

test("strict JSON object schema rejects invalid roots, keys, values and fenced JSON", () => {
  for (const value of [null, [], true, 1]) assert.throws(() => parseCitationJson(value), /citation_json_invalid/);
  for (const value of [null, [], "source"]) assert.throws(() => parseCitationJson({ ref_1: value }), /citation_value_invalid/);
  for (const key of ["ref_0", "ref_01", "ref_n", "other"]) assert.throws(() => parseCitationJson({ [key]: source() }), /citation_key_invalid/);
  for (const value of ["```json\n{}\n```", "{", '{"ref_1":}']) assert.throws(() => parseCitationJson(value), SyntaxError);
  assert.throws(() => validateCitationPair(null, {}), TypeError);
});

test("renderer is a substitution helper, not an HTML sanitizer", () => {
  const trustedHtml = '<span data-label="x">Claim</span>{{ref_1}}';
  const rendered = renderCitationReport(trustedHtml, { ref_1: source() });
  assert.ok(rendered.startsWith('<span data-label="x">Claim</span>'));
  assert.match(rendered, /rel="noopener noreferrer"/);
  // Existing surrounding markup is untouched, even if unsafe. Callers must
  // sanitize/parse content and choose safe text insertion contexts separately.
  assert.equal(renderCitationMarkers('<img src=x onerror="alert(1)">', {}), '<img src=x onerror="alert(1)">');
});
