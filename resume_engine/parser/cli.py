import argparse, json
from .pdf_parser import parse_pdf

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("pdf"); ap.add_argument("-o","--output",default="resume_ast.json")
    a=ap.parse_args(); ast=parse_pdf(a.pdf)
    with open(a.output,"w",encoding="utf-8") as f: json.dump(ast.model_dump(),f,indent=2,ensure_ascii=False)
    print(f"Parsed {len(ast.bullets())} bullets -> {a.output}")
if __name__=="__main__": main()
