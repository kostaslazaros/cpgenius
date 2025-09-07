docker build -t tiny-renamer .

ocker run --rm   -v "$PWD/in":/input -v "$PWD/out":/output tiny-renamer