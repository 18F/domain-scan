echo "running linters..."
flake8 .

echo "running tests..."
python -m unittest discover tests
