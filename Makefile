.PHONY: results verify test paper all clean

## Regenerate prototype results (results tables + manifest)
results:
	python3 prototype/checker.py \
		--rules prototype/rules.json \
		--traces prototype/traces/*.json \
		--out-dir prototype/results

## Verify checksums for source, traces, and generated results
verify:
	python3 prototype/verify_manifest.py prototype/results/MANIFEST.json

## Run executable conformance and transaction tests
test:
	python3 -m unittest discover -s prototype -p 'test*.py'

## Compile the article PDF
paper:
	latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex

## Run results then compile the paper
all: results verify test paper

## Remove LaTeX auxiliary files (keeps source, results, and PDF)
clean:
	latexmk -c main.tex
	rm -f main.out main.fls
