"""
Table of Contents generator for HTML files from Jupyter notebooks.
Adds a floating TOC sidebar to static HTML exports.
"""

import re
import logging

# TOC styles and script to inject into HTML
TOC_STYLE = """
<style>
#toc-container {
    position: fixed;
    left: 0;
    top: 0;
    width: 250px;
    height: 100vh;
    overflow-y: auto;
    background: #f8f9fa;
    border-right: 1px solid #dee2e6;
    padding: 20px 15px 40px 15px;
    z-index: 1000;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    box-sizing: border-box;
}

/* Ensure smooth scrolling in TOC */
#toc-container {
    scrollbar-width: thin;
    scrollbar-color: #adb5bd #f8f9fa;
}

#toc-container::-webkit-scrollbar {
    width: 6px;
}

#toc-container::-webkit-scrollbar-track {
    background: #f8f9fa;
}

#toc-container::-webkit-scrollbar-thumb {
    background: #adb5bd;
    border-radius: 3px;
}

#toc-container::-webkit-scrollbar-thumb:hover {
    background: #6c757d;
}

#toc-container h2 {
    font-size: 16px;
    font-weight: 600;
    margin: 0 0 15px 0;
    color: #212529;
}

#toc-container ul {
    list-style: none;
    padding: 0;
    margin: 0;
}

#toc-container li {
    margin: 0;
    padding: 0;
}

#toc-container a {
    display: block;
    padding: 6px 10px;
    color: #495057;
    text-decoration: none;
    font-size: 13px;
    line-height: 1.4;
    border-radius: 4px;
    transition: all 0.2s;
}

#toc-container a:hover {
    background: #e9ecef;
    color: #212529;
}

#toc-container .toc-h1-wrapper,
#toc-container .toc-h2-wrapper,
#toc-container .toc-h3-wrapper {
    display: flex;
    align-items: center;
    margin-top: 6px;
}

#toc-container .toc-h1 {
    font-weight: 600;
    flex: 1;
    order: 1;
}

#toc-container .toc-h2 {
    font-weight: 500;
    flex: 1;
    order: 1;
}

#toc-container .toc-h3 {
    font-size: 13px;
    flex: 1;
    order: 1;
}

#toc-container .toc-h4 {
    font-size: 12px;
}

#toc-container .toc-toggle {
    cursor: pointer;
    padding: 4px 6px;
    margin-left: 4px;
    user-select: none;
    color: #6c757d;
    font-size: 9px;
    transition: transform 0.2s, color 0.2s;
    border-radius: 3px;
    flex-shrink: 0;
    order: 2;
}

#toc-container .toc-toggle:hover {
    background: #e9ecef;
    color: #495057;
}

#toc-container .toc-toggle::before {
    content: '▼';
}

#toc-container .toc-toggle.collapsed::before {
    content: '►';
}

#toc-container .toc-section {
    overflow: hidden;
    transition: max-height 0.3s ease-out, opacity 0.3s ease-out;
    margin-left: 18px;
    max-height: none;
    opacity: 1;
}

#toc-container .toc-section.collapsed {
    max-height: 0 !important;
    opacity: 0;
}

#toc-container .toc-h1-wrapper {
    margin-top: 10px;
}

/* Adjust main content to make room for TOC */
body > main {
    margin-left: 270px;
    max-width: calc(100% - 290px);
}

/* Mobile: hide TOC on small screens */
@media (max-width: 768px) {
    #toc-container {
        display: none;
    }
    body > main {
        margin-left: 0;
        max-width: 100%;
    }
}

/* Dark mode support */
@media (prefers-color-scheme: dark) {
    #toc-container {
        background: #212529;
        border-right-color: #495057;
    }
    #toc-container h2 {
        color: #f8f9fa;
    }
    #toc-container a {
        color: #adb5bd;
    }
    #toc-container a:hover {
        background: #343a40;
        color: #f8f9fa;
    }
}
</style>
"""

TOC_SCRIPT = """
<script>
document.addEventListener('DOMContentLoaded', function() {
    console.log('TOC: DOMContentLoaded fired');

    // Find all headings in the main content
    const headings = document.querySelectorAll('main h1[id], main h2[id], main h3[id], main h4[id]');
    console.log('TOC: Found', headings.length, 'headings');

    if (headings.length === 0) {
        console.log('TOC: No headings found, exiting');
        return; // No headings found
    }

    // Create TOC container
    const tocContainer = document.createElement('div');
    tocContainer.id = 'toc-container';

    const tocTitle = document.createElement('h2');
    tocTitle.textContent = 'Table of Contents';
    tocContainer.appendChild(tocTitle);

    const tocList = document.createElement('ul');
    let currentH1Section = null;
    let currentH2Section = null;
    let currentH3Section = null;

    // Helper function to create collapsible heading entry
    function createCollapsibleHeading(level, id, text) {
        const wrapper = document.createElement('div');
        wrapper.className = 'toc-' + level + '-wrapper';

        const toggle = document.createElement('span');
        toggle.className = 'toc-toggle';
        toggle.dataset.id = id;

        const a = document.createElement('a');
        a.href = '#' + id;
        a.textContent = text;
        a.className = 'toc-' + level;

        const section = document.createElement('div');
        section.className = 'toc-section';

        // Add link first, then toggle (arrow on right)
        wrapper.appendChild(a);
        wrapper.appendChild(toggle);

        return { wrapper, section };
    }

    // Build hierarchical TOC from headings
    headings.forEach(heading => {
        const level = heading.tagName.toLowerCase();
        const id = heading.id;

        if (!id) return; // Skip headings without IDs

        // Clone heading and remove anchor links
        const clone = heading.cloneNode(true);
        const anchors = clone.querySelectorAll('a');
        anchors.forEach(a => a.remove());

        // Get text and clean up
        let text = clone.textContent.trim();
        text = text.replace(/¶/g, '').replace(/\\s+/g, ' ').trim();

        if (!text) {
            text = id.replace(/-/g, ' ');
        }

        if (level === 'h1') {
            const { wrapper, section } = createCollapsibleHeading('h1', id, text);
            const li = document.createElement('li');
            li.appendChild(wrapper);
            li.appendChild(section);
            tocList.appendChild(li);
            currentH1Section = section;
            currentH2Section = null;
            currentH3Section = null;

        } else if (level === 'h2') {
            const { wrapper, section } = createCollapsibleHeading('h2', id, text);

            if (currentH1Section) {
                currentH1Section.appendChild(wrapper);
                currentH1Section.appendChild(section);
            } else {
                const li = document.createElement('li');
                li.appendChild(wrapper);
                li.appendChild(section);
                tocList.appendChild(li);
            }
            currentH2Section = section;
            currentH3Section = null;

        } else if (level === 'h3') {
            const { wrapper, section } = createCollapsibleHeading('h3', id, text);

            const targetSection = currentH2Section || currentH1Section;
            if (targetSection) {
                targetSection.appendChild(wrapper);
                targetSection.appendChild(section);
            } else {
                const li = document.createElement('li');
                li.appendChild(wrapper);
                li.appendChild(section);
                tocList.appendChild(li);
            }
            currentH3Section = section;

        } else if (level === 'h4') {
            const a = document.createElement('a');
            a.href = '#' + id;
            a.textContent = text;
            a.className = 'toc-h4';

            const targetSection = currentH3Section || currentH2Section || currentH1Section;
            if (targetSection) {
                targetSection.appendChild(a);
            } else {
                const li = document.createElement('li');
                li.appendChild(a);
                tocList.appendChild(li);
            }
        }
    });

    tocContainer.appendChild(tocList);

    // Remove toggle buttons from headings without children
    tocContainer.querySelectorAll('.toc-section').forEach(section => {
        if (section.children.length === 0) {
            // This section is empty, remove the toggle button
            const wrapper = section.previousElementSibling;
            if (wrapper) {
                const toggle = wrapper.querySelector('.toc-toggle');
                if (toggle) {
                    toggle.remove();
                }
            }
            // Also remove the empty section
            section.remove();
        }
        // Don't set max-height here - CSS handles it with max-height: none
    });

    // Set initial state: H1 expanded, H2 and H3 collapsed
    tocContainer.querySelectorAll('.toc-h2-wrapper, .toc-h3-wrapper').forEach(wrapper => {
        const toggle = wrapper.querySelector('.toc-toggle');
        const section = wrapper.nextElementSibling;

        if (toggle && section && section.classList.contains('toc-section')) {
            // Collapse H2 and H3 sections by default
            toggle.classList.add('collapsed');
            section.classList.add('collapsed');
            section.style.maxHeight = '0';
        }
    });

    // Insert TOC at the beginning of body
    console.log('TOC: Inserting container with', tocList.children.length, 'items');
    document.body.insertBefore(tocContainer, document.body.firstChild);
    console.log('TOC: Successfully inserted');

    // Add collapse/expand functionality for toggle buttons
    tocContainer.querySelectorAll('.toc-toggle').forEach(toggle => {
        toggle.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();

            // Find the section (next sibling of parent wrapper)
            const wrapper = this.parentElement;
            const section = wrapper.nextElementSibling;

            if (section && section.classList.contains('toc-section')) {
                const isCollapsed = this.classList.contains('collapsed');

                if (isCollapsed) {
                    // Expand
                    this.classList.remove('collapsed');
                    section.classList.remove('collapsed');
                    section.style.maxHeight = 'none';
                } else {
                    // Collapse
                    this.classList.add('collapsed');
                    section.classList.add('collapsed');
                    section.style.maxHeight = '0';
                }
            }
        });
    });

    // Smooth scroll for all links (including H1)
    tocContainer.querySelectorAll('a').forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const targetId = this.getAttribute('href').substring(1);
            const target = document.getElementById(targetId);
            if (target) {
                target.scrollIntoView({ behavior: 'smooth', block: 'start' });
                history.pushState(null, null, '#' + targetId);
            }
        });
    });
});
</script>
"""


def add_toc_to_html(html_content):
    """
    Add floating Table of Contents to HTML content.

    Args:
        html_content (str): HTML content from notebook export

    Returns:
        str: Modified HTML with TOC injected
    """
    # Check if TOC already exists
    if 'id="toc-container"' in html_content:
        return html_content

    # Add TOC style before </head>
    html_content = html_content.replace('</head>', f'{TOC_STYLE}\n</head>')

    # Add TOC script before </body>
    html_content = html_content.replace('</body>', f'{TOC_SCRIPT}\n</body>')

    return html_content
