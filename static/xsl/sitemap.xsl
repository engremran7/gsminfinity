<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:s="http://www.sitemaps.org/schemas/sitemap/0.9">
  <xsl:output method="html" indent="yes" />
  <xsl:template match="/">
    <html lang="en">
      <head>
        <meta charset="UTF-8" />
        <title>Sitemap</title>
        <style>
          body { font-family: system-ui, -apple-system, "Segoe UI", sans-serif; background:#0b1220; color:#e5e7eb; margin:0; padding:0; }
          header { padding: 24px 28px; background:#0f172a; border-bottom:1px solid #1f2937; }
          h1 { margin:0; font-size:22px; }
          p { margin:4px 0 0 0; color:#94a3b8; }
          main { padding:24px 28px; }
          table { width:100%; border-collapse:collapse; background:#0f172a; border:1px solid #1f2937; border-radius:10px; overflow:hidden; }
          th, td { padding:10px 12px; text-align:left; }
          th { background:#111827; color:#cbd5e1; font-size:12px; text-transform:uppercase; letter-spacing:0.04em; }
          tr:nth-child(odd) td { background:#0d1527; }
          tr:nth-child(even) td { background:#0b1120; }
          a { color:#38bdf8; text-decoration:none; }
          a:hover { text-decoration:underline; }
          .pill { display:inline-block; padding:2px 8px; border-radius:999px; font-size:12px; background:#1f2937; color:#cbd5e1; }
          .meta { color:#94a3b8; font-size:12px; }
        </style>
      </head>
      <body>
        <header>
          <h1>XML Sitemap</h1>
          <p>Human-friendly view. Crawlers will ignore this styling.</p>
        </header>
        <main>
          <table>
            <thead>
              <tr>
                <th>URL</th>
                <th>Last Modified</th>
                <th>Changefreq</th>
                <th>Priority</th>
              </tr>
            </thead>
            <tbody>
              <xsl:for-each select="s:urlset/s:url">
                <tr>
                  <td><a href="{s:loc}"><xsl:value-of select="s:loc" /></a></td>
                  <td class="meta"><xsl:value-of select="s:lastmod" /></td>
                  <td class="meta"><xsl:value-of select="s:changefreq" /></td>
                  <td class="meta"><xsl:value-of select="s:priority" /></td>
                </tr>
              </xsl:for-each>
            </tbody>
          </table>
        </main>
      </body>
    </html>
  </xsl:template>
</xsl:stylesheet>
