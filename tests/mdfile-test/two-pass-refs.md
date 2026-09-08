---
to: beamer
title: Two-pass beamer test
subtitle: Exercises latex-passes
author: mdfile test
latex-passes: 2
slide-numbers: true
---

# Purpose

This deck exists to verify the multipass build path in mdfile.  With
`latex-passes: 2` in the front matter, mdfile should invoke pandoc to
produce a .tex file and then run pdflatex twice against it.

TikZ overlays (\\piccover-style, remember-picture) are the real reason
for two passes.  This fixture avoids TikZ so it stays self-contained,
but the same code path handles them.

# Cross-reference

Deck ends on page \pageref{last}.

# The end

\label{last}
Fin.
