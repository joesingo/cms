import sys
import argparse
import yaml

from mdss.config import SiteConfig
from mdss.site_gen import SiteGenerator


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "content_dir",
        help="The directory containing Markdown content"
    )
    parser.add_argument(
        "export_dir",
        help="The directory to export HTML files to"
    )
    args = parser.parse_args(sys.argv[1:])

    with open("mdss_config.yml") as f:
        config_dict = yaml.load(f)
    config = SiteConfig(config_dict)
    SiteGenerator(args.content_dir, config).gen_site(args.export_dir)


if __name__ == "__main__":
    main()
