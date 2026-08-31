import argparse, json
from resume_engine.pipeline import ResumeEngine

def main():
    ap=argparse.ArgumentParser(description='IITK Context-Aware Resume Diagnostic Engine')
    ap.add_argument('pdf'); ap.add_argument('--role',required=True,choices=['sde','quant','consulting','core']); ap.add_argument('-o','--output')
    a=ap.parse_args(); result=ResumeEngine().analyze(a.pdf,a.role); text=json.dumps(result.model_dump(),indent=2,ensure_ascii=False)
    if a.output: open(a.output,'w',encoding='utf-8').write(text)
    else: print(text)
if __name__=='__main__': main()
