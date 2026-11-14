---
name: seo-optimizer
description: Implements technical SEO for web pages: meta tags, structured data, sitemap, robots.txt, and Core Web Vitals. Use when improving search ranking or auditing a site's SEO.
license: Apache-2.0
compatibility: Claude Code, Codex, Gemini CLI
metadata:
  author: ai-skills
  version: "1.0"
  category: web-development
  tags: seo, meta-tags, structured-data, sitemap, core-web-vitals, nextjs-metadata
---

## Overview

Implements comprehensive technical SEO: essential meta tags (title, description, canonical), Open Graph + Twitter Cards, JSON-LD structured data for rich results (Article, Product, BreadcrumbList, FAQ, etc.), sitemap.xml generation, robots.txt rules, and a prioritized Core Web Vitals (LCP, CLS, INP) optimization checklist with concrete code changes.

## When to Use This Skill

- Launching a new site or page that needs to rank in search.
- Auditing or improving an existing site's SEO.
- The user mentions "SEO", "meta tags", "sitemap", "structured data", "rich results", or "Core Web Vitals".

## Prerequisites

- Access to the `<head>` or Next.js `metadata` API / `generateMetadata`.
- Ability to generate or edit `sitemap.xml` and `robots.txt`.
- Google Search Console or similar for verification (recommended).
- Performance measurement tools (Lighthouse, web-vitals).

## Steps

1. **Base meta tags** (every page):
   - `<title>`, `<meta name="description">`, canonical, viewport, charset.
   - Robots meta (index, follow).

2. **Social cards**:
   - Open Graph (`og:title`, `og:description`, `og:image`, `og:type`, `og:url`).
   - Twitter Card (`twitter:card`, `twitter:title`, etc.).
   - Image size recommendations (1200x630).

3. **Structured data (JSON-LD)**:
   - Choose the right schema type for the page content.
   - Provide complete, valid examples for Article, Product, Breadcrumb, FAQPage, HowTo, etc.
   - Use `<script type="application/ld+json">`.

4. **Next.js Metadata API** (App Router):
   - Static and dynamic `metadata` export.
   - `generateMetadata` function for dynamic pages.
   - OpenGraph and Twitter objects.

5. **Sitemap & robots**:
   - Generate `app/sitemap.ts` that returns XML.
   - `app/robots.ts`.
   - Include all important URLs, lastmod, priority, changefreq.

6. **Core Web Vitals optimization**:
   - LCP: image optimization (`next/image`), preload critical resources, font display swap.
   - CLS: reserve space for images/ads, avoid inserting content above the fold.
   - INP (Interaction to Next Paint): defer non-critical JS, use `loading="lazy"`, efficient event handlers.
   - Provide a checklist with exact code diffs.

7. **Output**:
   - Complete `<head>` example or Next.js metadata object.
   - JSON-LD snippets for common page types.
   - `sitemap.ts` and `robots.ts` examples.
   - CWV fix list tailored to the page.

## Examples

Full Next.js `generateMetadata` example for a blog post with Article + Breadcrumb structured data, sitemap code, and a CWV improvement patch are included.

## Edge Cases & Error Handling

- **Dynamic pages**: Always use `generateMetadata` and fetch data server-side.
- **Duplicate content**: Strong canonical strategy.
- **Images for social**: Provide multiple sizes or use a service like Vercel OG.
- **JavaScript-heavy sites**: Ensure critical content is in HTML (SSR or SSG).

## Verification

1. View source — all meta tags present and correct.
2. Run [Google Rich Results Test](https://search.google.com/test/rich-results) on structured data.
3. Submit sitemap in Google Search Console.
4. Run Lighthouse (SEO + Performance categories) — target 90+.
5. Use `web-vitals` library or CrUX dashboard to measure real-user LCP/CLS/INP.
6. Success: Pages are indexable, rich results appear in search, Core Web Vitals pass.

## References

- [Google SEO Starter Guide](https://developers.google.com/search/docs/fundamentals/seo-starter-guide)
- [Schema.org](https://schema.org/)
- [Next.js Metadata API](https://nextjs.org/docs/app/api-reference/functions/generate-metadata)
- [Core Web Vitals](https://web.dev/vitals/)
- [robots.txt and sitemap best practices](https://developers.google.com/search/docs/crawling-indexing/robots/intro)
