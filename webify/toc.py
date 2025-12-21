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
    padding: 20px 15px;
    z-index: 1000;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
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

#toc-container .toc-h1 {
    font-weight: 600;
    margin-top: 10px;
}

#toc-container .toc-h2 {
    padding-left: 20px;
}

#toc-container .toc-h3 {
    padding-left: 40px;
    font-size: 12px;
}

#toc-container .toc-h4 {
    padding-left: 60px;
    font-size: 12px;
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

    // Build TOC from headings
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
        // Remove pilcrow and collapse all whitespace
        text = text.replace(/¶/g, '').replace(/\\s+/g, ' ').trim();

        // If still no text after cleaning, use the ID as fallback
        if (!text) {
            text = id.replace(/-/g, ' ');
        }

        const li = document.createElement('li');
        const a = document.createElement('a');
        a.href = '#' + id;
        a.textContent = text;
        a.className = 'toc-' + level;

        li.appendChild(a);
        tocList.appendChild(li);
    });

    tocContainer.appendChild(tocList);

    // Insert TOC at the beginning of body
    console.log('TOC: Inserting container with', tocList.children.length, 'items');
    document.body.insertBefore(tocContainer, document.body.firstChild);
    console.log('TOC: Successfully inserted');

    // Smooth scroll to sections
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
