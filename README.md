# When to Trade & When to Take

A practical chess course for beginner to intermediate players who know how the pieces move.

[Read the 21-page PDF](when-to-trade-and-take.pdf)

The course includes eight lessons, ten exercises with explained answers, a decision checklist, and a seven-day practice plan. It covers safe captures, exchange counting, pinned defenders, intermediate moves, piece activity, pawn tension, recaptures, queen trades, and endgame pitfalls.

## Files

- `when-to-trade-and-take.pdf`: illustrated course.
- `positions-and-answers.pgn`: playable lesson and solution lines. Contains spoilers.
- `course.md`: readable text and FEN positions.
- `build_course.py`: reproducible PDF and PGN builder.
- `validation.json`: legal-move and end-state validation results.

## Rebuild

Use Python 3.11 or later:

```sh
python -m pip install -r requirements.txt
python build_course.py
```

The builder checks every recorded line for legal moves and verifies the explicit checkmate, stalemate, and insufficient-material endpoints. It checks PDF page count and text extraction. The delivered PDF was additionally rendered and visually reviewed. Illustrative lines are not exhaustive engine analysis.

## Sources and artwork

Rule references and further practice links are listed on page 21. Course prose and exercise questions were written for this project. Standard opening positions and illustrative sparse positions are used for teaching.

Chess-piece artwork is by Cburnett, via python-chess, under [CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/). See the [Wikimedia Commons chess-piece collection](https://commons.wikimedia.org/wiki/Category:SVG_chess_pieces). This attribution and license apply to that artwork; no separate license for the entire course is implied.
