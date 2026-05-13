.PHONY: results paper all clean

## Regenerate prototype results (results tables + manifest)
results:
	python3 prototype/checker.py \
		--rules prototype/rules.json \
		--traces prototype/traces/*.json \
		--out-dir prototype/results

## Compile the article PDF
paper:
	latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex

## Run results then compile the paper
all: results paper

## Remove LaTeX auxiliary files (keeps source, results, and PDF)
clean:
	latexmk -c main.tex
	rm -f main.out main.fls
