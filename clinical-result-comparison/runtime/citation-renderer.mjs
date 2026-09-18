const markerPattern = /\{\{(ref_(\d+))\}\}/g;

export function parseCitationJson(citationJson) {
  const citations = typeof citationJson === "string" ? JSON.parse(citationJson) : citationJson;
  validateCitationObject(citations);
  return citations;
}

export function renderCitationReport(report, citationJson) {
  if (typeof report !== "string") throw new TypeError("report must be a string");
  const citations = parseCitationJson(citationJson);
  validateCitations(report, citations);
  return renderCitationMarkers(report, citations);
}

/** Validate the current report/citation contract; this does not sanitize HTML
 * or verify citation metadata against the retrieved source records. */
export function validateCitationPair(report, citationJson) {
  if (typeof report !== "string") throw new TypeError("report must be a string");
  const citations = parseCitationJson(citationJson);
  validateCitations(report, citations);
  return true;
}


/** Substitute markers in trusted content only. Metadata escaping and URL protocol
 * checks do not sanitize the surrounding HTML or make arbitrary insertion contexts safe. */
export function renderCitationMarkers(html, citations) {
  if (typeof html !== "string") throw new TypeError("html must be a string");
  validateCitationObject(citations);

  return html.replace(markerPattern, (marker, key, number) => {
    const citation = citations[key];
    if (!citation || !isSafeHttpUrl(citation.link)) return marker;

    const href = escapeAttribute(citation.link);
    const title = escapeAttribute(citation.title || `来源 ${number}`);
    return `<sup class="source-citation"><a href="${href}" title="${title}" target="_blank" rel="noopener noreferrer">${number}</a></sup>`;
  });
}

function validateCitations(body, citations) {
  validateCitationObject(citations);
  // Reject unresolved/malformed tokens rather than silently ignoring them. The
  // brace boundaries prevent a valid-looking substring in {{{ref_1}}} passing.
  const strictMarkers = /(?<!\{)\{\{(ref_[1-9]\d*)\}\}(?!\})/g;
  const remainder = body.replace(strictMarkers, "");
  if (/\{\{|\}\}|\{\s*ref_|ref_[^\s{}]*\s*\}/.test(remainder)) {
    throw new Error("citation_marker_invalid");
  }
  const markerKeys = new Set([...body.matchAll(strictMarkers)].map((match) => match[1]));
  const citationKeys = new Set(Object.keys(citations));

  if (!sameSet(markerKeys, citationKeys)) {
    throw new Error("citation_marker_key_mismatch");
  }
  for (let n = 1; n <= citationKeys.size; n++) {
    if (!citationKeys.has(`ref_${n}`)) throw new Error("citation_keys_not_contiguous");
  }
  for (const citation of Object.values(citations)) {
    if (!citation.title.trim()) throw new Error("citation_title_empty");
    if (citation.paper_release_time_str !== "" && !isCalendarDate(citation.paper_release_time_str)) {
      throw new Error("citation_date_invalid");
    }
    // Empty links are part of the contract and remain inert when rendered.
    if (citation.link !== "" && (!/^https?:\/\//i.test(citation.link) ||
        /[\s\u0000-\u001f\u007f]/u.test(citation.link) || !isSafeHttpUrl(citation.link))) {
      throw new Error("citation_link_invalid");
    }
  }
}

function isCalendarDate(value) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const date = new Date(`${value}T00:00:00Z`);
  return !Number.isNaN(date.getTime()) && date.toISOString().slice(0, 10) === value;
}

function validateCitationObject(citations) {
  if (!citations || typeof citations !== "object" || Array.isArray(citations)) {
    throw new Error("citation_json_invalid");
  }

  for (const [key, citation] of Object.entries(citations)) {
    if (!/^ref_[1-9]\d*$/.test(key)) throw new Error("citation_key_invalid");
    if (!citation || typeof citation !== "object" || Array.isArray(citation)) {
      throw new Error("citation_value_invalid");
    }
    if (Object.keys(citation).sort().join(",") !== "link,paper_release_time_str,title") {
      throw new Error("citation_fields_invalid");
    }
    if (typeof citation.title !== "string" || typeof citation.link !== "string" || typeof citation.paper_release_time_str !== "string") {
      throw new Error("citation_field_type_invalid");
    }
  }
}

function isSafeHttpUrl(value) {
  if (!value) return false;
  try {
    const url = new URL(value);
    return url.protocol === "http:" || url.protocol === "https:";
  } catch {
    return false;
  }
}

function escapeAttribute(value) {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll('"', "&quot;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

function sameSet(left, right) {
  return left.size === right.size && [...left].every((value) => right.has(value));
}
