import argparse
from .core.reconnaissance.passive_engine import run_passive_enumeration

def main():
    parser = argparse.ArgumentParser(description="CyberHunter 3D - Minimal Refactoring Demo")
    parser.add_argument("domain", help="The root domain to target.")
    args = parser.parse_args()

    print(f"Running passive enumeration for {args.domain}...")
    subdomains = run_passive_enumeration(args.domain)
    print(f"Found {len(subdomains)} subdomains:")
    for sub in sorted(list(subdomains)):
        print(sub)

if __name__ == "__main__":
    main()
