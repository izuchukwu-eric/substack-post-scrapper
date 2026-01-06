"""Data extractor for Substack search pages."""

import json
import re
from datetime import datetime
from typing import Any

from playwright.async_api import Page
import structlog

logger = structlog.get_logger()


class DataExtractor:
    """Extracts post data from Substack search pages."""

    def __init__(self):
        """Initialize data extractor."""
        self._captured_posts: list[dict[str, Any]] = []

    async def extract_posts(self, page: Page, keyword: str) -> list[dict[str, Any]]:
        """Extract post data from the search results page.

        Args:
            page: Playwright page with search results
            keyword: Search keyword used

        Returns:
            List of post data dictionaries
        """
        posts = []

        # Strategy 1: Try to extract from React state/props
        posts = await self._extract_from_react_state(page)

        if not posts:
            # Strategy 2: Try to extract from embedded JSON (window._preloads or __NEXT_DATA__)
            posts = await self._extract_from_next_data(page)

        if not posts:
            # Strategy 3: Try window._preloads
            posts = await self._extract_from_preloads(page)

        if not posts:
            # Strategy 4: Extract from DOM as fallback
            posts = await self._extract_from_dom(page)

        # Add keyword and scrape timestamp to each post
        scraped_at = datetime.utcnow().isoformat() + "Z"
        for post in posts:
            post["keyword"] = keyword
            post["scrapedAt"] = scraped_at

        logger.info("extracted_posts", count=len(posts), keyword=keyword)
        return posts

    async def _extract_from_react_state(self, page: Page) -> list[dict[str, Any]]:
        """Extract posts from React component state."""
        try:
            posts = await page.evaluate(r'''
                () => {
                    const posts = [];

                    // Try to find posts in React fiber/state
                    const findReactPosts = (element) => {
                        if (!element) return [];

                        // Check for React fiber
                        const fiberKey = Object.keys(element).find(k => k.startsWith('__reactFiber'));
                        if (!fiberKey) return [];

                        const fiber = element[fiberKey];
                        const findPosts = (node, depth = 0) => {
                            if (!node || depth > 20) return [];
                            let found = [];

                            // Check memoizedProps for posts data
                            if (node.memoizedProps) {
                                const props = node.memoizedProps;
                                if (props.post && props.post.id) {
                                    found.push(props.post);
                                }
                                if (props.posts && Array.isArray(props.posts)) {
                                    found = found.concat(props.posts);
                                }
                            }

                            // Traverse children
                            if (node.child) {
                                found = found.concat(findPosts(node.child, depth + 1));
                            }
                            if (node.sibling) {
                                found = found.concat(findPosts(node.sibling, depth + 1));
                            }

                            return found;
                        };

                        return findPosts(fiber);
                    };

                    // Try from root
                    const root = document.getElementById('__next') || document.getElementById('root');
                    if (root) {
                        const found = findReactPosts(root);
                        if (found.length > 0) {
                            return found;
                        }
                    }

                    // Try all elements with search result data
                    const allElements = document.querySelectorAll('[class*="SearchResult"], [class*="search-result"], article');
                    for (const el of allElements) {
                        const found = findReactPosts(el);
                        posts.push(...found);
                    }

                    // Deduplicate by ID
                    const seen = new Set();
                    return posts.filter(p => {
                        if (!p.id || seen.has(p.id)) return false;
                        seen.add(p.id);
                        return true;
                    });
                }
            ''')

            if posts and len(posts) > 0:
                logger.debug("extracted_from_react_state", count=len(posts))
                return posts

        except Exception as e:
            logger.debug("react_state_extraction_failed", error=str(e))

        return []

    async def _extract_from_next_data(self, page: Page) -> list[dict[str, Any]]:
        """Extract posts from Next.js __NEXT_DATA__ script tag."""
        try:
            script_content = await page.evaluate('''
                () => {
                    const script = document.querySelector('script#__NEXT_DATA__');
                    return script ? script.textContent : null;
                }
            ''')

            if script_content:
                data = json.loads(script_content)
                # Navigate the Next.js data structure to find posts
                props = data.get("props", {})
                page_props = props.get("pageProps", {})

                # Check various possible locations for posts
                posts = page_props.get("posts", [])
                if not posts:
                    posts = page_props.get("results", [])
                if not posts:
                    search_data = page_props.get("searchData", {})
                    posts = search_data.get("posts", [])
                if not posts:
                    # Try dehydratedState for React Query
                    dehydrated = page_props.get("dehydratedState", {})
                    queries = dehydrated.get("queries", [])
                    for query in queries:
                        state = query.get("state", {})
                        query_data = state.get("data", {})
                        if isinstance(query_data, dict):
                            posts = query_data.get("posts", [])
                            if posts:
                                break

                if posts:
                    logger.debug("extracted_from_next_data", count=len(posts))
                    return posts

        except Exception as e:
            logger.debug("next_data_extraction_failed", error=str(e))

        return []

    async def _extract_from_preloads(self, page: Page) -> list[dict[str, Any]]:
        """Extract posts from window._preloads."""
        try:
            preloads = await page.evaluate('''
                () => {
                    if (window._preloads) {
                        return JSON.stringify(window._preloads);
                    }
                    return null;
                }
            ''')

            if preloads:
                data = json.loads(preloads)
                posts = data.get("posts", [])
                if posts:
                    logger.debug("extracted_from_preloads", count=len(posts))
                    return posts

        except Exception as e:
            logger.debug("preloads_extraction_failed", error=str(e))

        return []

    async def _extract_from_dom(self, page: Page) -> list[dict[str, Any]]:
        """Extract posts from DOM elements as fallback."""
        try:
            posts = await page.evaluate(r'''
                () => {
                    const posts = [];

                    // Look for search result items
                    const cards = document.querySelectorAll(
                        '[class*="SearchResult"], ' +
                        '[class*="post-preview"], ' +
                        '[data-testid="search-result"], ' +
                        'article[class*="post"]'
                    );

                    cards.forEach((card, index) => {
                        try {
                            // Find the link to the post
                            const link = card.querySelector('a[href*="/p/"]');
                            const canonical_url = link ? link.href : null;

                            // Extract post ID from URL or data attribute
                            let postId = null;
                            if (canonical_url) {
                                const match = canonical_url.match(/\/p\/([^/?]+)/);
                                if (match) {
                                    postId = match[1];
                                }
                            }

                            // Get title
                            const titleEl = card.querySelector('h2, h3, [class*="title"]');
                            const title = titleEl ? titleEl.textContent.trim() : null;

                            // Get subtitle/description
                            const subtitleEl = card.querySelector(
                                '[class*="subtitle"], ' +
                                '[class*="description"], ' +
                                'p[class*="preview"]'
                            );
                            const subtitle = subtitleEl ? subtitleEl.textContent.trim() : null;

                            // Get cover image
                            const imgEl = card.querySelector('img[src*="substackcdn"], img[src*="substack"]');
                            const cover_image = imgEl ? imgEl.src : null;

                            // Get author info
                            const authorEl = card.querySelector('[class*="author"], [class*="byline"]');
                            const authorName = authorEl ? authorEl.textContent.trim() : null;

                            // Get publication name
                            const pubEl = card.querySelector('[class*="publication"]');
                            const pubName = pubEl ? pubEl.textContent.trim() : null;

                            // Get date
                            const dateEl = card.querySelector('time, [class*="date"]');
                            const dateStr = dateEl ? (dateEl.getAttribute('datetime') || dateEl.textContent.trim()) : null;

                            if (title && canonical_url) {
                                posts.push({
                                    id: index + 1,  // Temporary ID
                                    publication_id: 0,  // Will be filled later
                                    title: title,
                                    slug: postId || '',
                                    canonical_url: canonical_url,
                                    subtitle: subtitle,
                                    description: subtitle,
                                    cover_image: cover_image,
                                    post_date: dateStr || new Date().toISOString(),
                                    type: 'newsletter',
                                    audience: 'everyone',
                                    truncated_body_text: subtitle,
                                    publishedBylines: authorName ? [{
                                        id: 0,
                                        name: authorName,
                                        publicationUsers: pubName ? [{
                                            publication: {
                                                id: 0,
                                                name: pubName,
                                                subdomain: ''
                                            }
                                        }] : []
                                    }] : []
                                });
                            }
                        } catch (e) {
                            console.error('Error extracting card:', e);
                        }
                    });

                    return posts;
                }
            ''')

            if posts:
                logger.debug("extracted_from_dom", count=len(posts))

            return posts

        except Exception as e:
            logger.error("dom_extraction_failed", error=str(e))
            return []

    async def get_post_count(self, page: Page) -> int:
        """Get the current count of loaded posts on the page.

        Args:
            page: Playwright page

        Returns:
            Number of posts currently visible
        """
        try:
            count = await page.evaluate('''
                () => {
                    // Try various selectors for search results
                    const selectors = [
                        '[class*="SearchResult"]',
                        '[class*="post-preview"]',
                        '[data-testid="search-result"]',
                        'article[class*="post"]',
                        '[class*="reader2-post"]'
                    ];

                    for (const selector of selectors) {
                        const elements = document.querySelectorAll(selector);
                        if (elements.length > 0) {
                            return elements.length;
                        }
                    }

                    return 0;
                }
            ''')
            return count
        except Exception as e:
            logger.error("get_post_count_failed", error=str(e))
            return 0
