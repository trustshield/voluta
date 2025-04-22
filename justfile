build:
    @echo "📦 Building Voluta with maturin..."
    maturin develop --release

test:
    @echo "🧪 Running tests..."
    python -m pytest tests/
    @echo "✅ Build and tests completed successfully!"

build-and-test:
    just build
    just test

fuzz iterations="1000" seed="":
    python tests/benchmark/fuzz.py --iterations {{iterations}} --seed {{seed}}

stress size="1" patterns="100" chunk="8" threads="4":
    python tests/benchmark/stress.py --size {{size}} --patterns {{patterns}} --chunk {{chunk}} --threads {{threads}}
