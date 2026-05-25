export function injectBuildInfo(html, buildInfo) {
  const meta = [
    `<meta name="meridian-build-revision" content="${buildInfo.short_revision}">`,
    `<meta name="meridian-build-built-at" content="${buildInfo.built_at}">`,
    `<script>window.MERIDIAN_BUILD=${JSON.stringify(buildInfo)};</script>`,
  ].join("\n");

  return html.includes("<!-- MERIDIAN_BUILD_INFO -->")
    ? html.replace("<!-- MERIDIAN_BUILD_INFO -->", meta)
    : html.replace("</head>", `${meta}\n</head>`);
}
