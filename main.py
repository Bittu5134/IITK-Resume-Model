import argparse
import json
import sys
from resume_engine.pipeline import ResumeEngine

def main():
    ap = argparse.ArgumentParser(description="IITK Context-Aware Resume Diagnostic Engine")
    ap.add_argument("pdf", nargs="?", help="Path to SPO PDF resume file")
    ap.add_argument("--role", choices=["sde", "quant", "consulting", "core"], help="Target industry track")
    ap.add_argument("-o", "--output", help="Save analysis JSON output to file")
    ap.add_argument("--serve", action="store_true", help="Launch the Web Advisory Dashboard server")
    ap.add_argument("--reload", action="store_true", default=True, help="Enable auto hot reload for development")
    ap.add_argument("--host", default="0.0.0.0", help="Host address for server (default: 0.0.0.0)")
    ap.add_argument("--port", type=int, default=8000, help="Port for web server (default: 8000)")

    args = ap.parse_args()

    if args.serve:
        import uvicorn
        print(f"🚀 Starting IITK Resume Diagnostic Web Engine on http://localhost:{args.port} (hot reload: {args.reload})")
        uvicorn.run("resume_engine.api.app:app", host=args.host, port=args.port, reload=args.reload)
        return

    if not args.pdf:
        ap.print_help()
        print("\nTip: Run 'python main.py --serve' to launch the interactive web dashboard!")
        sys.exit(1)

    if not args.role:
        print("Error: --role argument is required when analyzing a PDF via CLI.")
        sys.exit(1)

    result = ResumeEngine().analyze(args.pdf, args.role)
    text = json.dumps(result.model_dump(), indent=2, ensure_ascii=False)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"Analysis saved to {args.output}")
    else:
        print(text)

if __name__ == "__main__":
    main()

